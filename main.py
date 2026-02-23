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
from datetime import datetime, timedelta
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

        # 포트폴리오
        self.portfolio = Portfolio(
            order_currency=config.ORDER_CURRENCY,
            payment_currency=config.TRADING_CURRENCY,
            logger=self.logger
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

        # 일일 거래 기록
        self.daily_trades = []

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
            fee_rate=0.0015,  # 0.15% 수수료
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

        # 스케줄러 설정 (4시간 봉 마감 시)
        self.setup_scheduler()

        # 메인 루프
        try:
            self.logger.info("🚀 실전 모드 시작")
            self.notifier.send_system_status("started", "실전 모드가 시작되었습니다.\n/help 로 사용 가능한 명령어를 확인하세요.")

            while self._process_alive:
                if self.is_running:
                    schedule.run_pending()
                time.sleep(60)  # 1분마다 체크

        except KeyboardInterrupt:
            self.logger.info("⏹️  사용자 중단 신호 수신")
            self.shutdown()
        except Exception as e:
            self.logger.error(f"❌ 치명적 에러: {str(e)}", exc_info=True)
            self.notifier.send_error("CriticalError", str(e))
            self.shutdown()

    def setup_scheduler(self):
        """
        스케줄러 설정 (4시간 봉 마감 + 일일 로그 정리)
        """
        # 4시간 봉 마감 시간대: 한국시간 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
        schedule.every().day.at("00:00").do(self.on_candle_close)
        schedule.every().day.at("04:00").do(self.on_candle_close)
        schedule.every().day.at("08:00").do(self.on_candle_close)
        schedule.every().day.at("12:00").do(self.on_candle_close)
        schedule.every().day.at("16:00").do(self.on_candle_close)
        schedule.every().day.at("20:00").do(self.on_candle_close)

        # 매일 03:00에 오래된 로그 정리
        schedule.every().day.at("03:00").do(self.cleanup_logs)

        self.logger.info("📅 스케줄러 설정 완료 (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 / 로그 정리 03:00)")

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
        try:
            self.logger.info("=" * 50)
            self.logger.info(f"🕐 캔들 마감 처리 시작: {datetime.now()}")

            # 1. 데이터 업데이트
            self.logger.info("1️⃣ 데이터 업데이트 중...")
            updated_count = self.data_collector.update_data(
                order_currency=self.config.ORDER_CURRENCY,
                payment_currency=self.config.TRADING_CURRENCY,
                chart_intervals=self.config.CANDLE_PERIOD
            )
            self.logger.info(f"   {updated_count}개 캔들 업데이트 완료")

            if updated_count == 0:
                # 다음 캔들 시간 계산
                _now = datetime.now()
                _candle_hours = [0, 4, 8, 12, 16, 20]
                _next_hour = next((h for h in _candle_hours if h > _now.hour), None)
                if _next_hour is None:
                    _next_dt = (_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    _next_dt = _now.replace(hour=_next_hour, minute=0, second=0, microsecond=0)
                _next_time_str = _next_dt.strftime('%H:%M')

                position = self.portfolio.get_position() if self.portfolio.has_position() else None

                _retry_interval = 600   # 재시도 간격: 10분
                _max_retries = 6        # 최대 재시도 횟수: 6회 (총 1시간)

                if is_retry:
                    self._candle_retry_count += 1
                    if self._candle_retry_count >= _max_retries:
                        # 최대 재시도 초과 → 다음 캔들까지 대기
                        self.logger.warning(
                            f"⚠️ 캔들 데이터 없음 - 최대 재시도 {_max_retries}회 초과, 다음 캔들까지 대기"
                        )
                        self.notifier.send_candle_fetch_failed(
                            is_retry=True,
                            next_time=_next_time_str,
                            position=position
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
                        position=position
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

            # 4. 포지션 확인 및 매도 처리
            if self.portfolio.has_position():
                self.logger.info("4️⃣ 포지션 매도 확인 중...")
                self._check_sell_position(candles)
            else:
                self.logger.info("4️⃣ 매수 신호 확인 중...")
                self._check_buy_signal(candles)

            self.logger.info("=" * 50)

        except Exception as e:
            self.logger.error(f"❌ 캔들 마감 처리 에러: {str(e)}", exc_info=True)
            self.notifier.send_error("CandleCloseError", str(e))

    def _check_buy_signal(self, candles: list):
        """
        매수 신호 확인 및 실행

        Args:
            candles: 캔들 데이터
        """
        # 매수 조건 확인
        buy_signal = self.strategy.check_buy_signal(candles)

        if buy_signal["should_buy"]:
            self.logger.info("✅ 매수 신호 발생!")

            # 매수 수량 계산
            try:
                amount, fee = self.portfolio.calculate_buy_amount(
                    price=buy_signal["breakthrough_price"],
                    use_ratio=1.0  # 전체 자본 사용
                )
            except Exception as e:
                self.logger.error(f"매수 수량 계산 실패: {str(e)}")
                return

            # 매수 실행
            try:
                order_krw = amount * buy_signal["breakthrough_price"]
                self.logger.info(f"📥 매수 실행: {order_krw:,.0f} KRW (기준선: {buy_signal['breakthrough_price']:.2f})")

                # 매수 전 코인 잔고 저장
                coin_balance_before = self.portfolio.coin_balance

                result = self.order_executor.market_buy(
                    order_currency=self.config.ORDER_CURRENCY,
                    amount_krw=order_krw
                )

                # 체결 반영 대기 후 잔고 재조회
                import time as _time
                _time.sleep(3)
                balance_after = self.order_executor.get_balance()
                coin_balance_after = float(balance_after.get(
                    f"available_{self.config.ORDER_CURRENCY.lower()}", 0
                ))
                actual_amount = coin_balance_after - coin_balance_before

                if actual_amount <= 0:
                    self.logger.warning(
                        f"⚠️ 실제 체결 수량 확인 불가 (잔고 차이: {actual_amount:.8f}), 계산값 사용"
                    )
                    actual_amount = amount

                # 실제 체결 단가 계산
                actual_price = order_krw / actual_amount

                self.logger.info(f"✅ 체결 확인: {actual_amount:.8f} XRP @ {actual_price:.2f} KRW")

                # 포지션 오픈 (실제 체결 수량/가격 사용)
                self.portfolio.open_position(
                    amount=actual_amount,
                    price=actual_price,
                    candle=candles[-1]
                )

                # 잔고 업데이트
                krw_balance_after = float(balance_after.get(
                    f"available_{self.config.TRADING_CURRENCY.lower()}", 0
                ))
                self.portfolio.update_balance(krw_balance_after, coin_balance_after)

                # 알림
                self.notifier.send_buy_signal(
                    currency=self.config.ORDER_CURRENCY,
                    amount=actual_amount,
                    price=actual_price,
                    breakthrough_price=buy_signal.get("breakthrough_price"),
                    avg_close=buy_signal.get("avg_close")
                )

                self.trade_logger.log_buy(
                    currency=self.config.ORDER_CURRENCY,
                    amount=actual_amount,
                    price=actual_price
                )

                self.metrics_logger.log_trade()

            except Exception as e:
                self.logger.error(f"매수 실행 실패: {str(e)}")
                self.notifier.send_error("BuyError", str(e))
        else:
            self.logger.info(f"매수 조건 미충족: {', '.join(buy_signal.get('reasons', []))}")
            self._notify_buy_analysis(candles, buy_signal)

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

                # 포지션 클로즈
                position_info = self.portfolio.close_position(sell_signal["sell_price"])

                # 알림
                self.notifier.send_sell_signal(
                    currency=self.config.ORDER_CURRENCY,
                    amount=amount,
                    price=sell_signal["sell_price"],
                    profit=position_info["profit"],
                    profit_percent=position_info["profit_percent"],
                    duration_hours=position_info.get("duration_hours", 0)
                )

                self.trade_logger.log_sell(
                    currency=self.config.ORDER_CURRENCY,
                    amount=amount,
                    price=sell_signal["sell_price"],
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

    # ─── 매수 조건 분석 알림 ───

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
                f"  고가({current['high']:,.0f}) {'>' if c1 else '<='} 기준선({bp:,.1f})\n"
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
            "(00:00, 04:00, 08:00, 12:00, 16:00, 20:00 KST)\n"
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
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
                f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
