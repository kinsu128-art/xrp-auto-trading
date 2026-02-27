"""
XRP 자동매매 시스템
래리 윌리엄스 돌파 전략 기반
"""
import sys
import os
import time
import logging
import schedule
import argparse
import threading
from datetime import datetime, timedelta, timezone

# 한국 표준시 (UTC+9) - 시스템 타임존에 무관하게 KST 사용
KST = timezone(timedelta(hours=9))
from typing import Optional

# Windows 콘솔 UTF-8 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass  # Python 3.6 이하에서는 무시

from config import Config, validate_config
from bithumb_api import BithumbAPI
from data_storage import DataStorage
from data_collector import DataCollector
from strategy_engine import LarryWilliamsStrategy
from backtester import Backtester
from visualizer import Visualizer
from order_executor import OrderExecutor
from portfolio import Portfolio
from notification import TelegramNotifier, NotificationManager
from logger import setup_logger, TradeLogger, MetricsLogger, cleanup_old_logs


class TradingBot:
    """자동매매 봇 메인 클래스"""

    def __init__(self, config: Config):
        """
        트레이딩 봇 초기화

        Args:
            config: 설정 객체
        """
        self.config = config

        # 로거 설정
        self.logger = setup_logger(
            name="TradingBot",
            log_level=config.LOG_LEVEL,
            log_file=config.LOG_FILE,
            error_log_file=config.ERROR_LOG_FILE
        )

        # 트레이드 로거
        self.trade_logger = TradeLogger(self.logger)
        self.metrics_logger = MetricsLogger(self.logger)

        # API 클라이언트
        self.api = BithumbAPI(
            api_key=config.BITHUMB_API_KEY,
            api_secret=config.BITHUMB_API_SECRET,
            api_url=config.BITHUMB_API_URL
        )

        # 데이터 저장소
        self.storage = DataStorage(config.DATABASE_PATH)

        # 데이터 수집기
        self.data_collector = DataCollector(self.api, self.storage, self.logger)

        # 전략 엔진
        self.strategy = LarryWilliamsStrategy(
            breakthrough_ratio=config.BREAKTHROUGH_RATIO,
            num_candles_for_avg=config.NUM_CANDLES_FOR_AVG,
            logger=self.logger
        )

        # 주문 실행기
        self.order_executor = OrderExecutor(
            api=self.api,
            logger=self.logger,
            max_retries=config.MAX_RETRIES,
            retry_delay=config.RETRY_DELAY
        )

        # 포트폴리오 (storage 연동으로 포지션 영속화)
        self.portfolio = Portfolio(
            order_currency=config.ORDER_CURRENCY,
            payment_currency=config.TRADING_CURRENCY,
            fee_rate=config.FEE_RATE,
            logger=self.logger,
            storage=self.storage
        )

        # 알림 시스템
        self.notifier = TelegramNotifier(
            bot_token=config.TELEGRAM_BOT_TOKEN,
            chat_id=config.TELEGRAM_CHAT_ID,
            logger=self.logger
        )
        self.notification_manager = NotificationManager(self.notifier)

        # 시각화
        self.visualizer = Visualizer()

        # 상태 플래그
        self.is_running = False       # 매매 실행 여부 (/stop으로 일시중지)
        self._process_alive = True    # 프로세스 생존 여부 (실제 종료 시에만 False)
        self.last_candle_timestamp = 0
        self._candle_retry_timer = None  # 캔들 데이터 재시도 타이머
        self._candle_retry_count = 0    # 캔들 재시도 횟수 (최대 6회)
        self._candle_processing = False  # 캔들 처리 중 플래그 (중복 실행 방지)
        self._candle_lock = threading.Lock()  # 캔들 처리 스레드 안전 보장

        # 일일 거래 기록
        self.daily_trades = []

        # 지정가 주문 상태
        self._pending_order_id: Optional[str] = None       # 대기 중인 지정가 주문 UUID
        self._order_monitor_thread: Optional[threading.Thread] = None  # 체결 감시 스레드

        # 인트라데이 감시 상태
        self._intraday_target: Optional[float] = None   # 감시 중인 돌파기준선 (None이면 감시 안함)
        self._intraday_period_ts: int = 0               # 감시 대상 봉의 시작 타임스탬프 (ms)

    def initialize(self) -> bool:
        """
        시스템 초기화

        Returns:
            초기화 성공 여부
        """
        self.trade_logger.log_system_start()

        # 설정 유효성 검사
        if not validate_config(self.config):
            self.logger.error("설정 유효성 검사 실패")
            return False

        # 데이터베이스 초기화 확인
        db_count = self.storage.get_count()
        self.logger.info(f"저장된 캔들 데이터 개수: {db_count}")

        if db_count == 0:
            self.logger.info("초기 데이터 수집이 필요합니다.")
            self.logger.info("먼저 'python main.py --mode collect'를 실행하세요.")
            return False

        # 텔레그램 연결 테스트
        if not self.notifier.test_connection():
            self.logger.error("텔레그램 연결 실패")
            return False

        # 시스템 상태 알림
        self.notifier.send_system_status("started", "자동매매 시스템이 시작되었습니다.")

        self.logger.info("✅ 시스템 초기화 완료")
        return True

    def run_backtest(self, days: int = 365):
        """
        백테스트 실행

        Args:
            days: 백테스트 기간 (일)
        """
        self.logger.info(f"📊 백테스트 시작 ({days}일)")

        # 데이터 수집
        candles = self.data_collector.get_candles_for_backtest(
            order_currency=self.config.ORDER_CURRENCY,
            days=days
        )

        if not candles:
            self.logger.error("백테스트용 데이터 없음")
            return

        # 백테스터 실행
        backtester = Backtester(
            strategy=self.strategy,
            initial_capital=1000000.0,  # 100만 KRW
            fee_rate=self.config.FEE_RATE,  # config 기준 수수료 (기본 0.25%)
            logger=self.logger
        )

        result = backtester.run(candles)

        # 성과 지표
        metrics = result.calculate_metrics()

        # 시각화
        os.makedirs("reports", exist_ok=True)
        self.visualizer.plot_all_charts(
            candles,
            result.trades,
            result.equity_curve,
            output_dir="reports"
        )

        # HTML 리포트
        self.visualizer.create_backtest_report(
            candles,
            result.trades,
            metrics,
            output_path="reports/backtest_report.html"
        )

        # 텔레그램 알림
        self.notifier.send_backtest_summary(metrics, len(result.trades))

        self.logger.info(f"📊 백테스트 완료")
        self.logger.info(f"  총 수익률: {metrics['total_return_percent']:.2f}%")
        self.logger.info(f"  승률: {metrics['win_rate']:.2f}%")

    def run_live(self):
        """
        실전 모드 실행
        """
        if not self.initialize():
            self.logger.error("시스템 초기화 실패")
            return

        self.is_running = True
        self._process_alive = True
        self.trade_logger.log_system_start()

        # 텔레그램 명령어 등록 및 폴링 시작
        self._register_telegram_commands()
        self.notifier.start_polling()

        # 스케줄러 설정 (6시간 봉 마감 시)
        self.setup_scheduler()

        # 메인 루프
        try:
            self.logger.info("🚀 실전 모드 시작")
            self.notifier.send_system_status("started", "실전 모드가 시작되었습니다.\n/help 로 사용 가능한 명령어를 확인하세요.")

            while self._process_alive:
                if self.is_running:
                    schedule.run_pending()
                    self._check_intraday_breakthrough()  # 인트라데이 돌파 감시 (60초마다)
                time.sleep(60)  # 1분마다 체크

        except KeyboardInterrupt:
            self.logger.info("⏹️  사용자 중단 신호 수신")
            self.shutdown()
        except Exception as e:
            self.logger.error(f"❌ 치명적 에러: {str(e)}", exc_info=True)
            self.notifier.send_error("CriticalError", str(e))
            self.shutdown()

    def _parse_candle_interval_hours(self) -> int:
        """CANDLE_PERIOD 설정을 시간 단위 정수로 변환 (예: '6h' → 6)"""
        period = self.config.CANDLE_PERIOD
        unit = period[-1]
        value = int(period[:-1])
        if unit == "h":
            return value
        elif unit == "d":
            return value * 24
        return value

    def setup_scheduler(self):
        """
        스케줄러 설정 (CANDLE_PERIOD 기반 동적 봉 마감 + 일일 로그 정리)
        """
        interval_hours = self._parse_candle_interval_hours()
        candle_hours = list(range(0, 24, interval_hours))
        schedule_times = []

        for h in candle_hours:
            time_str = f"{h:02d}:00"
            schedule.every().day.at(time_str).do(self.on_candle_close)
            schedule_times.append(time_str)

        # 매일 03:00에 오래된 로그 정리
        schedule.every().day.at("03:00").do(self.cleanup_logs)

        self.logger.info(f"📅 스케줄러 설정 완료 ({', '.join(schedule_times)} / 로그 정리 03:00)")

    def cleanup_logs(self):
        """오래된 로그 파일 정리"""
        try:
            cleanup_old_logs(self.config.LOG_FILE, self.config.LOG_RETENTION_DAYS, self.logger)
            cleanup_old_logs(self.config.ERROR_LOG_FILE, self.config.LOG_RETENTION_DAYS, self.logger)
        except Exception as e:
            self.logger.error(f"로그 정리 중 에러: {e}")

    def on_candle_close(self, is_retry: bool = False):
        """
        캔들 마감 처리

        Args:
            is_retry: 재시도 여부 (True이면 실패 시 추가 재시도 예약 안 함)
        """
        # 중복 실행 방지: 재시도와 정규 스케줄이 동시에 호출될 경우 (스레드 안전)
        with self._candle_lock:
            if self._candle_processing:
                self.logger.warning("⚠️ 캔들 마감 처리가 이미 진행 중 - 중복 호출 무시")
                return
            self._candle_processing = True

        # 정규 스케줄 호출 시 잔존 재시도 타이머 취소 (M-2)
        if not is_retry:
            if self._candle_retry_timer and self._candle_retry_timer.is_alive():
                self._candle_retry_timer.cancel()
                self._candle_retry_timer = None
                self.logger.info("⏰ 정규 캔들 마감 시작 - 잔존 재시도 타이머 취소됨")

        try:
            self.logger.info("=" * 50)
            self.logger.info(f"🕐 캔들 마감 처리 시작: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}")

            # 1. 데이터 업데이트
            self.logger.info("1️⃣ 데이터 업데이트 중...")
            updated_count = self.data_collector.update_data(
                order_currency=self.config.ORDER_CURRENCY,
                payment_currency=self.config.TRADING_CURRENCY,
                chart_intervals=self.config.CANDLE_PERIOD
            )
            self.logger.info(f"   {updated_count}개 캔들 업데이트 완료")

            if updated_count == 0:
                # 다음 캔들 시간 계산 (CANDLE_PERIOD 기반 동적 생성)
                _now = datetime.now(KST)
                _interval_hours = self._parse_candle_interval_hours()
                _candle_hours = list(range(0, 24, _interval_hours))
                _next_hour = next((h for h in _candle_hours if h > _now.hour), None)
                if _next_hour is None:
                    _next_dt = (_now + timedelta(days=1)).replace(hour=_candle_hours[0], minute=0, second=0, microsecond=0)
                else:
                    _next_dt = _now.replace(hour=_next_hour, minute=0, second=0, microsecond=0)
                _next_time_str = _next_dt.strftime('%H:%M')

                position = self.portfolio.get_position() if self.portfolio.has_position() else None

                _retry_interval = 600   # 재시도 간격: 10분
                _max_retries = 6        # 최대 재시도 횟수: 6회 (총 1시간)

                if is_retry:
                    self._candle_retry_count += 1
                    if self._candle_retry_count >= _max_retries:
                        # 최대 재시도 초과 → 포지션 보유 시 폴백 판단, 아니면 다음 캔들 대기
                        self.logger.warning(
                            f"⚠️ 캔들 데이터 없음 - 최대 재시도 {_max_retries}회 초과"
                        )
                        if position:
                            self.logger.info("📊 포지션 보유 중 - 기존 캔들 데이터로 폴백 판단 실행")
                            self._fallback_with_existing_data(position, _next_time_str)
                        else:
                            self.logger.info("포지션 없음 - 다음 캔들까지 대기")
                            self.notifier.send_candle_fetch_failed(
                                is_retry=True,
                                next_time=_next_time_str,
                                position=None,
                                currency=self.config.ORDER_CURRENCY
                            )
                    else:
                        # 재시도 횟수 남음 → 10분 후 다시 예약 (텔레그램 알림 없음)
                        self.logger.warning(
                            f"⚠️ 재시도 실패 ({self._candle_retry_count}/{_max_retries}회) - 10분 후 재시도"
                        )
                        if self._candle_retry_timer and self._candle_retry_timer.is_alive():
                            self._candle_retry_timer.cancel()
                        self._candle_retry_timer = threading.Timer(_retry_interval, self._retry_candle_fetch)
                        self._candle_retry_timer.daemon = True
                        self._candle_retry_timer.start()
                        self.logger.info(
                            f"⏰ 10분 후 재시도 예약됨 ({self._candle_retry_count}/{_max_retries}회 완료)"
                        )
                else:
                    # 첫 실패 → 카운터 초기화 후 재시도 예약
                    self._candle_retry_count = 0
                    log_msg = "⚠️ 새로운 캔들 데이터 없음 - 10분 간격 최대 6회 재시도 예약"
                    if position:
                        log_msg += " (포지션 보유 중)"
                    self.logger.warning(log_msg)
                    self.notifier.send_candle_fetch_failed(
                        is_retry=False,
                        next_time=_next_time_str,
                        position=position,
                        currency=self.config.ORDER_CURRENCY
                    )

                    # 기존 타이머가 있으면 취소 후 새로 예약
                    if self._candle_retry_timer and self._candle_retry_timer.is_alive():
                        self._candle_retry_timer.cancel()
                    self._candle_retry_timer = threading.Timer(_retry_interval, self._retry_candle_fetch)
                    self._candle_retry_timer.daemon = True
                    self._candle_retry_timer.start()
                    self.logger.info("⏰ 10분 후 캔들 데이터 재시도 예약됨 (1/6회)")

                return

            # 데이터 수집 성공 시 잔존 타이머 및 카운터 초기화
            if self._candle_retry_timer and self._candle_retry_timer.is_alive():
                self._candle_retry_timer.cancel()
                self._candle_retry_timer = None
            self._candle_retry_count = 0

            # 2. 최신 캔들 조회
            self.logger.info("2️⃣ 최신 캔들 조회 중...")
            candles = self.storage.load_candles(limit=10)

            if len(candles) < 6:
                self.logger.warning("캔들 데이터 부족")
                return

            latest_candle = candles[-1]
            self.trade_logger.log_candle_close(latest_candle)

            # 이전 캔들에서 미체결된 지정가 주문 취소
            self._cancel_pending_order()

            # 3. 잔고 업데이트
            self.logger.info("3️⃣ 잔고 조회 중...")
            balance = self.order_executor.get_balance()
            krw_balance = float(balance.get(f"available_{self.config.TRADING_CURRENCY.lower()}", 0))
            coin_balance = float(balance.get(f"available_{self.config.ORDER_CURRENCY.lower()}", 0))

            self.portfolio.update_balance(krw_balance, coin_balance)

            # 현재 가격 조회
            ticker = self.api.get_ticker(
                order_currency=self.config.ORDER_CURRENCY,
                payment_currency=self.config.TRADING_CURRENCY
            )
            current_price = float(ticker.get("closing_price", 0))

            # 잔고 알림
            total_value = self.portfolio.get_total_value(current_price)
            self.trade_logger.log_balance(krw_balance, coin_balance, total_value)

            # 4. 포지션 유실 안전장치: 포지션 없지만 코인 잔고가 유의미하면 복구
            if not self.portfolio.has_position() and coin_balance > 0 and current_price > 0:
                coin_value_krw = coin_balance * current_price
                if coin_value_krw >= self.portfolio.min_order_krw:
                    self.logger.warning(
                        f"⚠️ 포지션 유실 감지: 포지션 없으나 {self.config.ORDER_CURRENCY} "
                        f"{coin_balance:.4f}개 보유 ({coin_value_krw:,.0f} KRW) → 포지션 자동 복구"
                    )
                    # 이전 봉을 entry_candle로 사용 (현재 봉이면 매도 판단 스킵됨)
                    recovery_candle = candles[-2] if len(candles) >= 2 else latest_candle
                    self.portfolio.open_position(
                        amount=coin_balance,
                        price=current_price,
                        candle=recovery_candle
                    )
                    self.notifier._send_message(
                        f"[포지션 자동 복구]\n"
                        f"포지션 데이터 유실 감지\n"
                        f"코인 잔고 기반 복구 완료\n\n"
                        f"수량: {coin_balance:.4f} {self.config.ORDER_CURRENCY}\n"
                        f"현재가 기준: {current_price:,.0f} KRW\n"
                        f"평가금액: {coin_value_krw:,.0f} KRW"
                    )

            # 5. 포지션 확인 및 매도 → 인트라데이 감시 설정
            if self.portfolio.has_position():
                self.logger.info("4️⃣ 포지션 매도 확인 중...")
                self._check_sell_position(candles)

                # 매도 후 잔고 재조회하여 같은 캔들에서 인트라데이 감시 설정
                if not self.portfolio.has_position():
                    self.logger.info("5️⃣ 매도 완료 → 인트라데이 감시 설정 중...")
                    time.sleep(3)
                    balance_after_sell = self.order_executor.get_balance()
                    krw_after = float(balance_after_sell.get(f"available_{self.config.TRADING_CURRENCY.lower()}", 0))
                    coin_after = float(balance_after_sell.get(f"available_{self.config.ORDER_CURRENCY.lower()}", 0))
                    self.portfolio.update_balance(krw_after, coin_after)
                    self._setup_intraday_monitoring(candles)
                else:
                    # 포지션 보유 중 → 인트라데이 감시 취소
                    self._intraday_target = None
                    self._intraday_period_ts = 0
            else:
                self.logger.info("4️⃣ 인트라데이 감시 설정 중...")
                self._setup_intraday_monitoring(candles)

            self.logger.info("=" * 50)

        except Exception as e:
            self.logger.error(f"❌ 캔들 마감 처리 에러: {str(e)}", exc_info=True)
            self.notifier.send_error("CandleCloseError", str(e))
        finally:
            with self._candle_lock:
                self._candle_processing = False

    def _check_buy_signal(self, candles: list):
        """
        매수 신호 확인 및 지정가 주문 실행

        Args:
            candles: 캔들 데이터
        """
        # 이미 대기 중인 주문이 있으면 스킵
        if self._pending_order_id:
            self.logger.info(f"📋 대기 중인 지정가 주문 있음 - 매수 신호 확인 스킵")
            return

        # 매수 조건 확인
        buy_signal = self.strategy.check_buy_signal(candles)

        if buy_signal["should_buy"]:
            self.logger.info("✅ 매수 신호 발생!")

            breakthrough_price = buy_signal["breakthrough_price"]

            # 지정가 기준 매수 수량 계산
            try:
                amount, fee = self.portfolio.calculate_buy_amount(
                    price=breakthrough_price,
                    use_ratio=1.0
                )
            except Exception as e:
                self.logger.error(f"매수 수량 계산 실패: {str(e)}")
                return

            # 지정가 매수 주문 실행
            try:
                self.logger.info(
                    f"📥 지정가 매수 주문: {breakthrough_price:,.2f} KRW x {amount:.4f} {self.config.ORDER_CURRENCY}"
                )

                result = self.order_executor.limit_buy(
                    order_currency=self.config.ORDER_CURRENCY,
                    price=breakthrough_price,
                    units=amount
                )

                order_id = result.get("uuid") if isinstance(result, dict) else None

                if order_id:
                    self._pending_order_id = order_id
                    self._start_order_monitor(order_id, breakthrough_price, amount, candles[-1], buy_signal)
                    self.logger.info(f"📡 주문 체결 감시 시작: {order_id[:8]}...")
                else:
                    self.logger.warning("주문 UUID 없음 - 체결 감시 불가")

                # 주문 접수 알림
                self.notifier.send_limit_order_placed(
                    currency=self.config.ORDER_CURRENCY,
                    amount=amount,
                    price=breakthrough_price,
                    breakthrough_price=breakthrough_price,
                    avg_close=buy_signal.get("avg_close")
                )

                self.trade_logger.log_buy(
                    currency=self.config.ORDER_CURRENCY,
                    amount=amount,
                    price=breakthrough_price
                )

            except Exception as e:
                self.logger.error(f"매수 주문 실패: {str(e)}")
                self.notifier.send_error("BuyError", str(e))
        else:
            self.logger.info(f"매수 조건 미충족: {', '.join(buy_signal.get('reasons', []))}")
            self._notify_buy_analysis(candles, buy_signal)

    def _start_order_monitor(
        self,
        order_id: str,
        breakthrough_price: float,
        amount: float,
        entry_candle: dict,
        buy_signal: dict
    ):
        """지정가 매수 주문 체결 감시 스레드 시작"""
        if self._order_monitor_thread and self._order_monitor_thread.is_alive():
            self.logger.warning("이미 주문 감시 스레드가 실행 중")
            return

        self._order_monitor_thread = threading.Thread(
            target=self._monitor_order_fill,
            args=(order_id, breakthrough_price, amount, entry_candle, buy_signal),
            name="OrderMonitor",
            daemon=True
        )
        self._order_monitor_thread.start()

    def _monitor_order_fill(
        self,
        order_id: str,
        breakthrough_price: float,
        amount: float,
        entry_candle: dict,
        buy_signal: dict
    ):
        """
        주문 체결 감시 (백그라운드 스레드)
        30초마다 체결 여부 확인, 체결 시 포지션 오픈 + 텔레그램 알림
        """
        check_interval = 60  # 60초마다 확인

        while self._process_alive:
            # 주문 ID가 변경(취소)되면 감시 중단
            if self._pending_order_id != order_id:
                self.logger.info(f"📡 주문 감시 중단: 주문 취소됨 ({order_id[:8]}...)")
                return

            try:
                detail = self.api.get_order_detail(order_id)
                state = detail.get("state", "")

                if state == "done":
                    # 체결 완료
                    trades = detail.get("trades", [])
                    if trades:
                        total_volume = sum(float(t.get("volume", 0)) for t in trades)
                        total_funds = sum(float(t.get("funds", 0)) for t in trades)
                        actual_price = total_funds / total_volume if total_volume > 0 else breakthrough_price
                        actual_amount = total_volume
                    else:
                        actual_amount = amount
                        actual_price = breakthrough_price

                    self.logger.info(
                        f"✅ 지정가 매수 체결! {actual_amount:.4f} {self.config.ORDER_CURRENCY} @ {actual_price:,.2f} KRW"
                    )

                    # 감시 종료 표시
                    self._pending_order_id = None

                    # 포지션 오픈
                    self.portfolio.open_position(
                        amount=actual_amount,
                        price=actual_price,
                        candle=entry_candle
                    )

                    # 잔고 업데이트
                    try:
                        time.sleep(2)
                        balance_after = self.order_executor.get_balance()
                        krw_after = float(balance_after.get(
                            f"available_{self.config.TRADING_CURRENCY.lower()}", 0
                        ))
                        coin_after = float(balance_after.get(
                            f"available_{self.config.ORDER_CURRENCY.lower()}", 0
                        ))
                        self.portfolio.update_balance(krw_after, coin_after)
                    except Exception:
                        pass

                    # 체결 알림
                    self.notifier.send_buy_filled(
                        currency=self.config.ORDER_CURRENCY,
                        amount=actual_amount,
                        price=actual_price,
                        breakthrough_price=breakthrough_price,
                        avg_close=buy_signal.get("avg_close")
                    )

                    self.metrics_logger.log_trade()
                    return

                elif state == "cancel":
                    # 외부에서 취소됨
                    self.logger.info(f"📡 주문 취소 확인: {order_id[:8]}...")
                    self._pending_order_id = None
                    return

                self.logger.debug(f"주문 대기 중: {order_id[:8]}... (상태: {state})")

            except Exception as e:
                self.logger.warning(f"주문 체결 확인 오류: {e}")

            time.sleep(check_interval)

    def _cancel_pending_order(self):
        """대기 중인 지정가 주문 취소 (다음 캔들 마감 시 호출)"""
        if not self._pending_order_id:
            return

        order_id = self._pending_order_id
        self._pending_order_id = None  # 먼저 초기화 → 감시 스레드 자동 중단

        try:
            self.order_executor.cancel_order(order_id)
            self.logger.info(f"🚫 미체결 지정가 주문 취소 완료: {order_id[:8]}...")
            self.notifier._send_message(
                f"[주문 취소]\n"
                f"지정가 매수 주문이 체결되지 않아 취소되었습니다.\n"
                f"주문 ID: {order_id[:8]}...\n"
                f"🕐 {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            self.logger.error(f"주문 취소 실패: {e}")

    def _check_sell_position(self, candles: list):
        """
        포지션 매도 확인 및 실행

        Args:
            candles: 캔들 데이터
        """
        position = self.portfolio.get_position()

        # 매도 조건 확인
        sell_signal = self.strategy.check_sell_signal(candles, position)

        if sell_signal["should_sell"]:
            self.logger.info("✅ 매도 신호 발생!")

            # 매도 수량
            amount = position["amount"]

            # 매도 실행
            try:
                self.logger.info(f"📤 매도 실행: {amount:.8f} @ {sell_signal['sell_price']:.2f}")

                result = self.order_executor.market_sell(
                    order_currency=self.config.ORDER_CURRENCY,
                    units=amount
                )

                # 주문 UUID로 실제 체결가 조회
                actual_amount, actual_price = self._get_filled_order_info(
                    result, fallback_amount=amount, fallback_price=sell_signal["sell_price"]
                )
                self.logger.info(f"✅ 매도 체결 확인: {actual_amount:.8f} {self.config.ORDER_CURRENCY} @ {actual_price:.2f} KRW")

                # 포지션 클로즈 (실제 체결가 기준)
                position_info = self.portfolio.close_position(actual_price)

                # 알림
                self.notifier.send_sell_signal(
                    currency=self.config.ORDER_CURRENCY,
                    amount=actual_amount,
                    price=actual_price,
                    profit=position_info["profit"],
                    profit_percent=position_info["profit_percent"],
                    duration_hours=position_info.get("duration_hours", 0),
                    reason=sell_signal.get("reason")
                )

                self.trade_logger.log_sell(
                    currency=self.config.ORDER_CURRENCY,
                    amount=actual_amount,
                    price=actual_price,
                    profit=position_info["profit"],
                    profit_percent=position_info["profit_percent"],
                    duration_hours=position_info.get("duration_hours", 0)
                )

                # 일일 거래 기록
                self.daily_trades.append(position_info)

                self.metrics_logger.log_trade()

            except Exception as e:
                self.logger.error(f"매도 실행 실패: {str(e)}")
                self.notifier.send_error("SellError", str(e))

        else:
            # 매수 조건 유지 중 - 포지션 보유 알림
            current_candle = candles[-1]
            current_price = current_candle["close"]
            entry_price = position.get("entry_price", 0)
            entry_time = position.get("entry_time")
            duration_hours = 0
            if entry_time:
                from datetime import datetime
                duration_hours = (datetime.now() - entry_time).total_seconds() / 3600

            self.notifier.send_hold_signal(
                currency=self.config.ORDER_CURRENCY,
                amount=position["amount"],
                entry_price=entry_price,
                current_price=current_price,
                duration_hours=duration_hours
            )

    def _get_filled_order_info(self, order_result: dict, fallback_amount: float, fallback_price: float, max_wait: int = 5):
        """
        주문 UUID로 체결 수량/단가를 조회한다.

        Args:
            order_result: market_buy/market_sell 반환값
            fallback_amount: 조회 실패 시 사용할 수량
            fallback_price: 조회 실패 시 사용할 가격
            max_wait: 최대 폴링 횟수 (2초 간격)

        Returns:
            (actual_amount, actual_price) 튜플
        """
        order_uuid = None
        if isinstance(order_result, dict):
            order_uuid = order_result.get("uuid")

        if not order_uuid:
            self.logger.warning("주문 UUID 없음 - 폴백 값 사용")
            return fallback_amount, fallback_price

        for attempt in range(max_wait):
            try:
                time.sleep(2)
                detail = self.api.get_order_detail(order_uuid)

                state = detail.get("state", "")
                trades = detail.get("trades", [])

                if state in ("done", "cancel") and trades:
                    total_volume = sum(float(t.get("volume", 0)) for t in trades)
                    total_funds = sum(float(t.get("funds", 0)) for t in trades)

                    if total_volume > 0 and total_funds > 0:
                        avg_price = total_funds / total_volume
                        self.logger.info(f"📋 주문 체결 조회 성공: {total_volume:.8f} @ {avg_price:.2f}")
                        return total_volume, avg_price

                if state == "done":
                    break

                self.logger.debug(f"주문 상태: {state} (시도 {attempt + 1}/{max_wait})")

            except Exception as e:
                self.logger.warning(f"주문 체결 조회 실패 (시도 {attempt + 1}): {e}")

        self.logger.warning("주문 체결 상세 조회 실패 - 폴백 값 사용")
        return fallback_amount, fallback_price

    def _fallback_with_existing_data(self, position: dict, next_time_str: str):
        """
        캔들 데이터 수집 실패 시 기존 데이터 + 현재가로 폴백 매도 판단

        포지션 보유 중 캔들 데이터를 가져올 수 없을 때,
        마지막 저장된 캔들과 현재 시세를 활용하여 손절/익절 판단만 수행한다.
        (매수는 하지 않음 - 불완전한 데이터로 새 포지션 진입은 위험)
        """
        try:
            self.logger.info("📊 폴백 판단 시작: 기존 캔들 + 현재가 기반")

            # 기존 저장된 캔들 로드
            candles = self.storage.load_candles(limit=10)
            if len(candles) < 6:
                self.logger.warning("폴백 판단 불가 - 저장된 캔들 데이터 부족")
                self.notifier.send_candle_fetch_failed(
                    is_retry=True,
                    next_time=next_time_str,
                    position=position,
                    currency=self.config.ORDER_CURRENCY
                )
                return

            # 현재가 조회
            ticker = self.api.get_ticker(
                order_currency=self.config.ORDER_CURRENCY,
                payment_currency=self.config.TRADING_CURRENCY
            )
            current_price = float(ticker.get("closing_price", 0))

            if current_price <= 0:
                self.logger.warning("폴백 판단 불가 - 현재가 조회 실패")
                self.notifier.send_candle_fetch_failed(
                    is_retry=True,
                    next_time=next_time_str,
                    position=position,
                    currency=self.config.ORDER_CURRENCY
                )
                return

            entry_price = position.get("entry_price", 0)
            profit_percent = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0

            self.logger.info(
                f"폴백 현재가: {current_price:,.0f} | 진입가: {entry_price:,.0f} | 수익률: {profit_percent:+.2f}%"
            )

            # 매도 신호 확인 (기존 캔들 데이터 기반)
            sell_signal = self.strategy.check_sell_signal(candles, position)

            if sell_signal["should_sell"]:
                self.logger.info("🔴 폴백 판단: 매도 신호 발생 - 매도 실행")
                self._check_sell_position(candles)
                self.notifier.send_fallback_executed(
                    action="매도 실행",
                    current_price=current_price,
                    profit_percent=profit_percent,
                    next_time=next_time_str
                )
            else:
                self.logger.info("🟢 폴백 판단: 매도 신호 없음 - 포지션 유지")
                self.notifier.send_fallback_executed(
                    action="포지션 유지",
                    current_price=current_price,
                    profit_percent=profit_percent,
                    next_time=next_time_str
                )

        except Exception as e:
            self.logger.error(f"폴백 판단 중 에러: {str(e)}", exc_info=True)
            self.notifier.send_candle_fetch_failed(
                is_retry=True,
                next_time=next_time_str,
                position=position,
                currency=self.config.ORDER_CURRENCY
            )

    def _retry_candle_fetch(self):
        """캔들 데이터 재시도 (10분 간격, 최대 6회)"""
        self.logger.info(f"🔄 캔들 데이터 재시도 중... ({self._candle_retry_count + 1}/6회차)")
        if self.is_running and self._process_alive:
            self.on_candle_close(is_retry=True)
        else:
            self.logger.info("매매 중지 또는 종료 상태 - 캔들 재시도 건너뜀")

    def shutdown(self):
        """시스템 종료"""
        self.logger.info("⏹️  시스템 종료 중...")

        self.is_running = False
        self._process_alive = False

        # 대기 중인 지정가 주문 취소
        self._cancel_pending_order()

        # 캔들 재시도 타이머 취소
        if self._candle_retry_timer and self._candle_retry_timer.is_alive():
            self._candle_retry_timer.cancel()
            self.logger.info("캔들 재시도 타이머 취소됨")

        # 텔레그램 폴링 정지
        self.notifier.stop_polling()

        self.trade_logger.log_system_stop()

        # 시스템 상태 알림
        self.notifier.send_system_status("stopped", "자동매매 시스템이 종료되었습니다.")

        # 메트릭 요약
        metrics_summary = self.metrics_logger.get_summary()
        self.logger.info(f"📊 메트릭 요약: {metrics_summary}")

    # ─── 인트라데이 감시 ───

    def _setup_intraday_monitoring(self, candles: list):
        """
        캔들 마감 후 다음 봉 인트라데이 감시 설정

        조건 2&3이 모두 충족될 경우 감시를 시작하고,
        미충족 시 조건 분석 알림을 전송한다.

        Args:
            candles: 최신 마감 캔들 데이터
        """
        # 이미 대기 중인 지정가 주문이 있으면 스킵
        if self._pending_order_id:
            self.logger.info("📋 대기 중인 지정가 주문 있음 - 인트라데이 감시 설정 스킵")
            return

        watch_info = self.strategy.get_intraday_watch_price(candles)
        interval_ms = self._parse_candle_interval_hours() * 3600 * 1000

        # 다음 봉 시작 타임스탬프 = 현재 마감봉 타임스탬프 + 인터벌
        next_period_ts = candles[-1]["timestamp"] + interval_ms

        if watch_info["should_watch"]:
            self._intraday_target = watch_info["breakthrough_price"]
            self._intraday_period_ts = next_period_ts

            # 감시 만료 시각 계산 (다음 봉 마감 = 다음 봉 시작 + 인터벌)
            period_end_dt = datetime.fromtimestamp((next_period_ts + interval_ms) / 1000)
            period_end_str = period_end_dt.strftime('%H:%M')

            self.logger.info(
                f"👁 인트라데이 감시 시작: 돌파기준선={self._intraday_target:,.2f}, "
                f"5봉평균={watch_info['avg_close']:,.2f}, 만료={period_end_str}"
            )
            self.notifier.send_intraday_watch_started(
                currency=self.config.ORDER_CURRENCY,
                breakthrough_price=self._intraday_target,
                avg_close=watch_info["avg_close"],
                period_end_time=period_end_str
            )
        else:
            self._intraday_target = None
            self._intraday_period_ts = 0

            conditions = watch_info["conditions"]
            reasons = []
            if not conditions.get("above_avg"):
                reasons.append(
                    f"5봉평균 미달 (기준선={watch_info['breakthrough_price']:.2f} <= 평균={watch_info['avg_close']:.2f})"
                )
            if not conditions.get("volume_increase"):
                reasons.append("거래량 감소")
            self.logger.info(f"👁 인트라데이 감시 미설정: {', '.join(reasons)}")

            self._notify_intraday_conditions_failed(candles, watch_info)

    def _check_intraday_breakthrough(self):
        """
        매 60초 호출 - 현재가가 돌파기준선을 넘으면 즉시 지정가 매수

        메인 루프(실전 모드)에서만 호출됨.
        감시 중이 아니면 즉시 반환한다.
        """
        if self._intraday_target is None:
            return

        # 포지션 보유 or 대기 주문 있으면 감시 취소
        if self.portfolio.has_position() or self._pending_order_id:
            self._intraday_target = None
            self._intraday_period_ts = 0
            return

        # 감시 기간 유효성 확인 (봉 마감 여부)
        interval_ms = self._parse_candle_interval_hours() * 3600 * 1000
        now_ms = int(time.time() * 1000)
        period_end_ts = self._intraday_period_ts + interval_ms

        if now_ms >= period_end_ts:
            # 봉 마감 → 감시 만료 처리 (on_candle_close가 새 감시를 설정할 것)
            self.logger.info(
                f"⏰ 인트라데이 감시 만료 (돌파 없이 봉 마감): 기준선={self._intraday_target:,.2f}"
            )
            self.notifier.send_intraday_watch_expired(
                currency=self.config.ORDER_CURRENCY,
                breakthrough_price=self._intraday_target
            )
            self._intraday_target = None
            self._intraday_period_ts = 0
            return

        # 현재가 조회
        try:
            ticker = self.api.get_ticker(
                order_currency=self.config.ORDER_CURRENCY,
                payment_currency=self.config.TRADING_CURRENCY
            )
            current_price = float(ticker.get("closing_price", 0))
        except Exception as e:
            self.logger.warning(f"인트라데이 감시 - 현재가 조회 실패: {e}")
            return

        if current_price <= 0:
            return

        self.logger.debug(
            f"👁 인트라데이 감시 중: 현재가={current_price:,.2f}, 기준선={self._intraday_target:,.2f}"
        )

        # 돌파 감지!
        if current_price >= self._intraday_target:
            target = self._intraday_target
            self._intraday_target = None   # 중복 매수 방지
            self._intraday_period_ts = 0

            self.logger.info(
                f"🔥 인트라데이 돌파 감지! 현재가={current_price:,.2f} >= 기준선={target:,.2f}"
            )

            candles = self.storage.load_candles(limit=10)
            if len(candles) >= 6:
                self._execute_intraday_buy(candles, current_price, target)
            else:
                self.logger.warning("인트라데이 매수 불가 - 캔들 데이터 부족")

    def _execute_intraday_buy(self, candles: list, current_price: float, breakthrough_price: float):
        """
        인트라데이 돌파 감지 후 즉시 지정가 매수 실행

        Args:
            candles: 최신 마감 캔들 데이터 (진입봉 정보 포함)
            current_price: 돌파 감지 시점의 현재가
            breakthrough_price: 돌파 기준선 가격 (지정가 주문 가격)
        """
        # 이미 대기 중인 주문이 있으면 스킵
        if self._pending_order_id:
            self.logger.warning("이미 대기 중인 지정가 주문 있음 - 인트라데이 매수 스킵")
            return

        # 지정가 기준 매수 수량 계산
        try:
            amount, fee = self.portfolio.calculate_buy_amount(
                price=breakthrough_price,
                use_ratio=1.0
            )
        except Exception as e:
            self.logger.error(f"인트라데이 매수 수량 계산 실패: {str(e)}")
            return

        # 지정가 매수 주문 실행 (breakthrough_price에 지정가 주문)
        try:
            self.logger.info(
                f"📥 인트라데이 지정가 매수: {breakthrough_price:,.2f} KRW x {amount:.4f} {self.config.ORDER_CURRENCY}"
            )

            result = self.order_executor.limit_buy(
                order_currency=self.config.ORDER_CURRENCY,
                price=breakthrough_price,
                units=amount
            )

            order_id = result.get("uuid") if isinstance(result, dict) else None

            # avg_close 재계산 (send_buy_filled용)
            watch_info = self.strategy.get_intraday_watch_price(candles)

            if order_id:
                self._pending_order_id = order_id
                self._start_order_monitor(order_id, breakthrough_price, amount, candles[-1], watch_info)
                self.logger.info(f"📡 주문 체결 감시 시작: {order_id[:8]}...")
            else:
                self.logger.warning("주문 UUID 없음 - 체결 감시 불가")

            # 주문 접수 알림
            self.notifier.send_limit_order_placed(
                currency=self.config.ORDER_CURRENCY,
                amount=amount,
                price=breakthrough_price,
                breakthrough_price=breakthrough_price,
                avg_close=watch_info.get("avg_close")
            )

            self.trade_logger.log_buy(
                currency=self.config.ORDER_CURRENCY,
                amount=amount,
                price=breakthrough_price
            )

        except Exception as e:
            self.logger.error(f"인트라데이 매수 주문 실패: {str(e)}")
            self.notifier.send_error("IntradayBuyError", str(e))

    def _notify_intraday_conditions_failed(self, candles: list, watch_info: dict):
        """
        인트라데이 감시 조건 미충족 시 분석 결과를 텔레그램으로 전송

        Args:
            candles: 캔들 데이터
            watch_info: get_intraday_watch_price() 반환값
        """
        try:
            current = candles[-1]
            prev = candles[-2]
            ts = datetime.fromtimestamp(current["timestamp"] / 1000)

            conditions = watch_info.get("conditions", {})
            bp = watch_info.get("breakthrough_price", 0)
            avg_close = watch_info.get("avg_close", 0)

            c2 = conditions.get("above_avg", False)
            c3 = conditions.get("volume_increase", False)

            mark = lambda v: "O" if v else "X"

            msg = (
                f"[{ts.strftime('%m/%d %H:%M')}] 인트라데이 감시 미설정\n\n"
                f"[{mark(c2)}] 조건2: 5봉 평균 상회\n"
                f"  기준선({bp:,.1f}) {'>' if c2 else '<='} 평균({avg_close:,.1f})\n\n"
                f"[{mark(c3)}] 조건3: 거래량 증가\n"
                f"  현재({current['volume']:,.0f}) {'>' if c3 else '<='} 전봉({prev['volume']:,.0f})\n\n"
                f"돌파기준선: {bp:,.1f} KRW\n"
                f"결과: 감시 미설정"
            )

            self.notifier._send_message(msg)

        except Exception as e:
            self.logger.error(f"인트라데이 조건 분석 알림 실패: {e}")

    # ─── 매수 조건 분석 알림 (레거시) ───

    def _notify_buy_analysis(self, candles: list, buy_signal: dict):
        """
        매수 불발 시 조건 분석 결과를 텔레그램으로 전송

        Args:
            candles: 캔들 데이터
            buy_signal: 전략 엔진의 매수 신호 결과
        """
        try:
            current = candles[-1]
            prev = candles[-2]
            ts = datetime.fromtimestamp(current["timestamp"] / 1000)

            conditions = buy_signal.get("conditions", {})
            bp = buy_signal.get("breakthrough_price", 0)
            avg_close = buy_signal.get("avg_close", 0)

            prev_range = prev["high"] - prev["low"]

            # 조건별 PASS/FAIL 표시
            c1 = conditions.get("breakthrough", False)
            c2 = conditions.get("above_avg", False)
            c3 = conditions.get("volume_increase", False)

            mark = lambda v: "O" if v else "X"

            msg = (
                f"[{ts.strftime('%m/%d %H:%M')}] 매수 조건 분석\n\n"
                f"[{mark(c1)}] 조건1: 돌파 기준선\n"
                f"  종가({current['close']:,.0f}) {'>' if c1 else '<='} 기준선({bp:,.1f})\n"
                f"  기준선 = 시가({current['open']:,.0f}) + 변동폭({prev_range:,.0f}) x 0.5\n\n"
                f"[{mark(c2)}] 조건2: 5봉 평균 상회\n"
                f"  기준선({bp:,.1f}) {'>' if c2 else '<='} 평균({avg_close:,.1f})\n\n"
                f"[{mark(c3)}] 조건3: 거래량 증가\n"
                f"  현재({current['volume']:,.0f}) {'>' if c3 else '<='} 전봉({prev['volume']:,.0f})\n\n"
                f"결과: 매수 불발"
            )

            reasons = buy_signal.get("reasons", [])
            if reasons:
                msg += f" ({', '.join(reasons)})"

            self.notifier._send_message(msg)

        except Exception as e:
            self.logger.error(f"매수 분석 알림 실패: {e}")

    # ─── 텔레그램 명령어 핸들러 ───

    def _register_telegram_commands(self):
        """텔레그램 명령어 콜백 등록"""
        self.notifier.register_command("/start", self._cmd_start)
        self.notifier.register_command("/stop", self._cmd_stop)
        self.notifier.register_command("/status", self._cmd_status)
        self.notifier.register_command("/help", self._cmd_help)
        self.notifier.register_command("/balance", self._cmd_balance)

    def _cmd_start(self) -> str:
        """/start - 매매 재개"""
        if self.is_running:
            return "이미 매매가 실행 중입니다."

        self.is_running = True
        self.logger.info("텔레그램 /start 명령으로 매매 재개")
        return (
            "✅ 매매가 재개되었습니다.\n\n"
            "스케줄러가 활성화되어 다음 캔들 마감 시\n"
            "(00:00, 06:00, 12:00, 18:00 KST)\n"
            "매매를 실행합니다."
        )

    def _cmd_stop(self) -> str:
        """/stop - 매매 일시중지"""
        if not self.is_running:
            return "이미 매매가 중지된 상태입니다."

        self.is_running = False
        self.logger.info("텔레그램 /stop 명령으로 매매 일시중지")
        return (
            "⏸️ 매매가 일시중지되었습니다.\n\n"
            "봇 프로세스는 계속 실행 중이며\n"
            "텔레그램 명령은 계속 수신합니다.\n"
            "보유 포지션은 영향받지 않습니다.\n\n"
            "/start 로 매매를 재개할 수 있습니다."
        )

    def _cmd_status(self) -> str:
        """/status - 현재 상태 조회"""
        status = "🟢 실행 중" if self.is_running else "🔴 일시중지"

        # 포지션 정보
        if self.portfolio.has_position():
            pos = self.portfolio.get_position()
            entry_price = pos.get("entry_price", 0)
            amount = pos.get("amount", 0)
            entry_time = pos.get("entry_time")
            entry_str = entry_time.strftime('%m/%d %H:%M') if entry_time else "N/A"
            position_text = (
                f"{self.config.ORDER_CURRENCY} {amount:.4f}\n"
                f"   진입가: {entry_price:,.2f} KRW\n"
                f"   진입시간: {entry_str}"
            )
        else:
            position_text = "없음"

        # 마지막 캔들
        latest_candle = self.storage.get_latest_candle()
        if latest_candle:
            candle_time = datetime.fromtimestamp(latest_candle["timestamp"] / 1000)
            candle_str = candle_time.strftime('%m/%d %H:%M')
            candle_close = f"{latest_candle['close']:,.2f} KRW"
        else:
            candle_str = "N/A"
            candle_close = "N/A"

        return (
            f"📊 봇 상태: {status}\n\n"
            f"💵 KRW 잔고: {self.portfolio.krw_balance:,.0f}\n"
            f"🪙 {self.config.ORDER_CURRENCY} 잔고: {self.portfolio.coin_balance:.4f}\n\n"
            f"📦 포지션: {position_text}\n\n"
            f"🕯️ 마지막 캔들: {candle_str}\n"
            f"💰 종가: {candle_close}\n\n"
            f"⚙️ 전략: 래리 윌리엄스 ({self.config.BREAKTHROUGH_RATIO}x)\n"
            f"🕐 {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def _cmd_help(self) -> str:
        """/help - 사용 가능한 명령어"""
        return (
            "📋 사용 가능한 명령어\n\n"
            "/start   - 매매 재개\n"
            "/stop    - 매매 일시중지\n"
            "/status  - 현재 상태 조회\n"
            "/balance - 실시간 잔고 조회\n"
            "/help    - 이 도움말 표시"
        )

    def _cmd_balance(self) -> str:
        """/balance - 실시간 잔고 조회"""
        try:
            balance = self.order_executor.get_balance()
            krw = float(balance.get(f"available_{self.config.TRADING_CURRENCY.lower()}", 0))
            coin = float(balance.get(f"available_{self.config.ORDER_CURRENCY.lower()}", 0))

            ticker = self.api.get_ticker(
                order_currency=self.config.ORDER_CURRENCY,
                payment_currency=self.config.TRADING_CURRENCY
            )
            current_price = float(ticker.get("closing_price", 0))

            coin_value = coin * current_price
            total = krw + coin_value

            # 캐시 업데이트
            self.portfolio.update_balance(krw, coin)

            return (
                f"💼 잔고 현황\n\n"
                f"💵 KRW: {krw:,.0f}\n"
                f"🪙 {self.config.ORDER_CURRENCY}: {coin:.4f}"
                f" ({coin_value:,.0f} KRW)\n\n"
                f"📊 총 자산: {total:,.0f} KRW\n"
                f"💰 {self.config.ORDER_CURRENCY} 현재가: {current_price:,.2f} KRW\n\n"
                f"🕐 {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            self.logger.error(f"잔고 조회 실패: {e}")
            return f"❌ 잔고 조회 실패: {str(e)}"


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="XRP 자동매매 시스템")
    parser.add_argument(
        "--mode",
        choices=["collect", "backtest", "live"],
        default="backtest",
        help="실행 모드"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="백테스트 기간 (일)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="실전 모드 확인 프롬프트 생략 (Docker 환경용)"
    )

    args = parser.parse_args()

    # 설정 로드
    config = Config()

    # 트레이딩 봇 생성
    bot = TradingBot(config)

    # 모드별 실행
    if args.mode == "collect":
        print("📥 데이터 수집 모드")
        bot.data_collector.fetch_initial_data(
            order_currency=config.ORDER_CURRENCY,
            payment_currency=config.TRADING_CURRENCY,
            chart_intervals=config.CANDLE_PERIOD,
            days=args.days
        )

    elif args.mode == "backtest":
        print("📊 백테스트 모드")
        bot.run_backtest(days=args.days)

    elif args.mode == "live":
        print("🚀 실전 모드")
        print("⚠️  실전 모드에서는 실제 자산이 거래됩니다!")
        print("⚠️  소액으로 테스트 후 본격 운용을 권장합니다.")

        if not args.confirm:
            confirm = input("계속 진행하시겠습니까? (yes/no): ")
            if confirm.lower() not in ["yes", "y"]:
                print("❌ 취소되었습니다.")
                return

        bot.run_live()


if __name__ == "__main__":
    main()
