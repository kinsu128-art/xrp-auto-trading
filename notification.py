"""
알림 모듈
"""
import logging
import threading
import time
import requests
from typing import Optional, Dict, Callable
from datetime import datetime, timezone, timedelta

# 한국 표준시 (UTC+9) - 시스템 타임존에 무관하게 KST 사용
KST = timezone(timedelta(hours=9))


class TelegramNotifier:
    """텔레그램 알림 클래스"""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        텔레그램 알림 초기화

        Args:
            bot_token: 텔레그램 봇 토큰
            chat_id: �트 ID
            logger: 로거
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.logger = logger or logging.getLogger(__name__)

        # 텔레그램 Bot API URL
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

        # 폴링 상태
        self._polling = False
        self._polling_thread = None
        self._last_update_id = 0

        # 명령어 콜백 (TradingBot에서 등록)
        self._command_callbacks = {}

    def _send_message(self, message: str) -> bool:
        """
        텔레그램 메시지 전송 (네트워크 실패 시 최대 3회 재시도, 반복문 방식)

        Args:
            message: 메시지 내용

        Returns:
            전송 성공 여부
        """
        max_retries = 3
        url = f"{self.api_url}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": message
        }

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(url, data=data, timeout=10)
                response.raise_for_status()

                result = response.json()
                if result.get("ok"):
                    self.logger.debug(f"텔레그램 메시지 전송 성공: {message[:50]}...")
                    return True
                else:
                    error_msg = result.get("description", "Unknown error")
                    self.logger.error(f"텔레그램 메시지 전송 실패: {error_msg}")
                    return False

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries:
                    wait = (attempt + 1) * 5  # 5초, 10초, 15초
                    self.logger.warning(
                        f"텔레그램 전송 실패 (재시도 {attempt + 1}/{max_retries}, {wait}초 후): {type(e).__name__}"
                    )
                    time.sleep(wait)
                else:
                    self.logger.error(f"텔레그램 전송 최종 실패 ({max_retries}회 재시도 소진): {str(e)}")
                    return False
            except requests.exceptions.RequestException as e:
                self.logger.error(f"텔레그램 요청 실패: {str(e)}")
                return False

        return False

    def send_buy_signal(
        self,
        currency: str,
        amount: float,
        price: float,
        breakthrough_price: Optional[float] = None,
        avg_close: Optional[float] = None
    ) -> bool:
        """
        매수 알림 전송

        Args:
            currency: 코인 심볼
            amount: 매수 수량
            price: 매수 가격
            breakthrough_price: 돌파 기준선 가격
            avg_close: 5봉 종가 평균

        Returns:
            전송 성공 여부
        """
        message = f"""📥 매수 신호

💰 코인: {currency}
📈 매수 가격: {price:.2f} KRW
📊 매수 수량: {amount:.8f}
💵 주문 금액: {amount * price:,.0f} KRW
⏰ 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"""

        if breakthrough_price is not None:
            message += f"\n\n🎯 돌파 기준선: {breakthrough_price:.2f} KRW"
        if avg_close is not None:
            message += f"\n📊 5봉 종가 평균: {avg_close:.2f} KRW"

        return self._send_message(message)

    def send_limit_order_placed(
        self,
        currency: str,
        amount: float,
        price: float,
        breakthrough_price: Optional[float] = None,
        avg_close: Optional[float] = None
    ) -> bool:
        """
        지정가 매수 주문 접수 알림

        Args:
            currency: 코인 심볼
            amount: 주문 수량
            price: 지정가
            breakthrough_price: 돌파 기준선 가격
            avg_close: 5봉 종가 평균

        Returns:
            전송 성공 여부
        """
        message = f"""📋 지정가 매수 주문 접수

💰 코인: {currency}
🎯 주문 가격: {price:,.2f} KRW
📊 주문 수량: {amount:.4f}
💵 주문 금액: {amount * price:,.0f} KRW
⏰ 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"""

        if breakthrough_price is not None:
            message += f"\n\n🎯 돌파 기준선: {breakthrough_price:,.2f} KRW"
        if avg_close is not None:
            message += f"\n📊 5봉 종가 평균: {avg_close:,.2f} KRW"

        message += "\n\n⏳ 체결 대기 중..."

        return self._send_message(message)

    def send_buy_filled(
        self,
        currency: str,
        amount: float,
        price: float,
        breakthrough_price: Optional[float] = None,
        avg_close: Optional[float] = None
    ) -> bool:
        """
        지정가 매수 체결 완료 알림

        Args:
            currency: 코인 심볼
            amount: 체결 수량
            price: 체결 가격
            breakthrough_price: 돌파 기준선 가격
            avg_close: 5봉 종가 평균

        Returns:
            전송 성공 여부
        """
        message = f"""✅ 매수 체결 완료

💰 코인: {currency}
📥 체결 가격: {price:,.2f} KRW
📊 체결 수량: {amount:.4f}
💵 체결 금액: {amount * price:,.0f} KRW
⏰ 체결 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"""

        if breakthrough_price is not None:
            message += f"\n\n🎯 돌파 기준선: {breakthrough_price:,.2f} KRW"
        if avg_close is not None:
            message += f"\n📊 5봉 종가 평균: {avg_close:,.2f} KRW"

        return self._send_message(message)

    def send_sell_signal(
        self,
        currency: str,
        amount: float,
        price: float,
        profit: float,
        profit_percent: float,
        duration_hours: float,
        reason: Optional[str] = None
    ) -> bool:
        """
        매도 알림 전송

        Args:
            currency: 코인 심볼
            amount: 매도 수량
            price: 매도 가격
            profit: 수익 (KRW)
            profit_percent: 수익률 (%)
            duration_hours: 보유 시간 (시간)
            reason: 매도 사유 (예: "돌파 기준선 미달, 거래량 감소")

        Returns:
            전송 성공 여부
        """
        profit_emoji = "📈" if profit > 0 else "📉"
        profit_color = profit_percent >= 0

        message = f"""{profit_emoji} 매도 신호

💰 코인: {currency}
📉 매도 가격: {price:.2f} KRW
📊 매도 수량: {amount:.8f}
💵 회수 금액: {amount * price:,.0f} KRW
{'✅' if profit_color else '❌'} 수익: {profit:+,.0f} KRW ({profit_percent:+.2f}%)
⏰ 보유 시간: {duration_hours:.1f}시간
🕐 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"""

        if reason:
            message += f"\n\n📋 매도 사유: {reason}"

        return self._send_message(message)

    def send_hold_signal(
        self,
        currency: str,
        amount: float,
        entry_price: float,
        current_price: float,
        duration_hours: float
    ) -> bool:
        """
        포지션 보유 알림 전송 (매수 조건 유지 중)

        Args:
            currency: 코인 심볼
            amount: 보유 수량
            entry_price: 진입 가격
            current_price: 현재 가격
            duration_hours: 보유 시간 (시간)

        Returns:
            전송 성공 여부
        """
        unrealized_profit = (current_price - entry_price) * amount
        unrealized_percent = (current_price - entry_price) / entry_price * 100
        profit_emoji = "📈" if unrealized_profit >= 0 else "📉"

        message = f"""🔒 포지션 보유 중 (매수 조건 유지)

💰 코인: {currency}
📥 진입 가격: {entry_price:.2f} KRW
💹 현재 가격: {current_price:.2f} KRW
📊 보유 수량: {amount:.8f}
{profit_emoji} 미실현 손익: {unrealized_profit:+,.0f} KRW ({unrealized_percent:+.2f}%)
⏰ 보유 시간: {duration_hours:.1f}시간
🕐 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"""

        return self._send_message(message)

    def send_balance(
        self,
        krw_balance: float,
        coin_balance: float,
        coin_symbol: str = "XRP",
        coin_price: Optional[float] = None
    ) -> bool:
        """
        잔고 알림 전송

        Args:
            krw_balance: KRW 잔고
            coin_balance: 코인 잔고
            coin_symbol: 코인 심볼
            coin_price: 코인 가격 (선택사항)

        Returns:
            전송 성공 여부
        """
        message = f"""💼 잔고 현황

💵 KRW 잔고: {krw_balance:,.0f} KRW
🪙 {coin_symbol} 잔고: {coin_balance:.8f}"""

        if coin_price is not None:
            coin_value = coin_balance * coin_price
            total_value = krw_balance + coin_value
            message += f"\n\n💰 {coin_symbol} 가치: {coin_value:,.0f} KRW"
            message += f"\n📊 총 자산: {total_value:,.0f} KRW (약 {coin_price:.2f} KRW/{coin_symbol})"

        message += f"\n\n🕐 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"

        return self._send_message(message)

    def send_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None
    ) -> bool:
        """
        에러 알림 전송

        Args:
            error_type: 에러 타입
            error_message: 에러 메시지
            context: 추가 컨텍스트 정보

        Returns:
            전송 성공 여부
        """
        message = f"""⚠️ 에러 발생

❌ 에러 타입: {error_type}
📝 에러 메시지: {error_message}
🕐 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"""

        if context:
            message += "\n\n추가 정보:"
            for key, value in context.items():
                message += f"\n• {key}: {value}"

        return self._send_message(message)

    def send_backtest_summary(
        self,
        metrics: Dict,
        trades_count: int
    ) -> bool:
        """
        백테스트 요약 알림 전송

        Args:
            metrics: 성과 지표
            trades_count: 총 거래 횟수

        Returns:
            전송 성공 여부
        """
        message = f"""📊 백테스트 요약

📈 총 수익률: {metrics['total_return_percent']:+.2f}%
📅 연간 수익률: {metrics['annualized_return']:+.2f}%
✅ 승률: {metrics['win_rate']:.2f}%
🔄 총 거래: {trades_count}회
💵 평균 수익: {metrics['avg_profit']:,.0f} KRW
📉 평균 손실: {metrics['avg_loss']:,.0f} KRW
⚖️ 손익비: {metrics['profit_factor']:.2f}
📉 최대 손실률: {metrics['max_drawdown_percent']:.2f}%
📊 샤프 비율: {metrics['sharpe_ratio']:.2f}

🕐 생성 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"""

        return self._send_message(message)

    def send_system_status(
        self,
        status: str,
        message: str
    ) -> bool:
        """
        시스템 상태 알림 전송

        Args:
            status: 상태 (started, stopped, error)
            message: 상태 메시지

        Returns:
            전송 성공 여부
        """
        status_emoji = {
            "started": "🚀",
            "stopped": "⏹️",
            "error": "❌",
            "warning": "⚠️"
        }.get(status, "ℹ️")

        message = f"""{status_emoji} 시스템 상태

{status.upper()}: {message}
🕐 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"""

        return self._send_message(message)

    def send_candle_fetch_failed(
        self,
        is_retry: bool,
        next_time: str,
        position: Optional[Dict] = None,
        currency: str = "XRP"
    ) -> bool:
        """
        캔들 데이터 수집 실패 알림

        Args:
            is_retry: 재시도 여부 (True=재시도에서도 실패, False=첫 실패)
            next_time: 다음 재시도 시각 또는 다음 캔들 시각 (HH:MM)
            position: 포지션 정보 (보유 중일 때만 전달)

        Returns:
            전송 성공 여부
        """
        now_str = datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')

        if is_retry:
            title = "⚠️ 캔들 데이터 재시도 실패"
            next_line = f"다음 캔들({next_time})까지 대기합니다."
        else:
            title = "⚠️ 캔들 데이터 수집 실패"
            next_line = f"10분 후 자동 재시도합니다.\n재시도 실패 시 다음 캔들: {next_time}"

        position_line = ""
        if position:
            title += " [포지션 보유 중]"
            position_line = (
                f"\n진입가: {position['entry_price']:,.0f} KRW"
                f" | 수량: {position['amount']:.4f} {currency}"
            )

        message = f"{title}\n🕐 {now_str}{position_line}\n{next_line}"

        return self._send_message(message)

    def send_fallback_executed(
        self,
        action: str,
        current_price: float,
        profit_percent: float,
        next_time: str
    ) -> bool:
        """
        캔들 수집 실패 폴백 판단 결과 알림

        Args:
            action: 실행된 조치 (예: "매도 실행", "포지션 유지")
            current_price: 현재 시세
            profit_percent: 현재 수익률
            next_time: 다음 캔들 시각 (HH:MM)

        Returns:
            전송 성공 여부
        """
        now_str = datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')
        emoji = "🔴" if "매도" in action else "🟢"
        message = (
            f"📊 캔들 수집 실패 - 폴백 판단 실행\n"
            f"🕐 {now_str}\n"
            f"{emoji} 결과: {action}\n"
            f"현재가: {current_price:,.0f} KRW | 수익률: {profit_percent:+.2f}%\n"
            f"다음 정규 캔들: {next_time}"
        )
        return self._send_message(message)

    def send_intraday_watch_started(
        self,
        currency: str,
        breakthrough_price: float,
        avg_close: float,
        period_end_time: str
    ) -> bool:
        """
        인트라데이 감시 시작 알림

        Args:
            currency: 코인 심볼
            breakthrough_price: 돌파 기준선 가격
            avg_close: 5봉 종가 평균
            period_end_time: 감시 만료 시각 (HH:MM)

        Returns:
            전송 성공 여부
        """
        message = f"""👁 인트라데이 감시 시작

💰 코인: {currency}
🎯 돌파 기준선: {breakthrough_price:,.2f} KRW
📊 5봉 종가 평균: {avg_close:,.2f} KRW
⏰ 감시 만료: {period_end_time} KST
🕐 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}

현재가가 돌파 기준선 도달 시 즉시 시장가 매수합니다."""

        return self._send_message(message)

    def send_intraday_watch_expired(
        self,
        currency: str,
        breakthrough_price: float
    ) -> bool:
        """
        인트라데이 감시 만료 알림 (돌파 없이 봉 마감)

        Args:
            currency: 코인 심볼
            breakthrough_price: 감시 중이던 돌파 기준선 가격

        Returns:
            전송 성공 여부
        """
        message = f"""⏰ 인트라데이 감시 만료

💰 코인: {currency}
🎯 감시 기준선: {breakthrough_price:,.2f} KRW
🕐 만료 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}

돌파 없이 봉이 마감되었습니다.
다음 봉 마감 시 새 기준선을 설정합니다."""

        return self._send_message(message)

    def send_daily_report(
        self,
        trades: list,
        total_pnl: float,
        total_pnl_percent: float
    ) -> bool:
        """
        일일 리포트 알림 전송

        Args:
            trades: 오늘의 거래 내역
            total_pnl: 총 수익
            total_pnl_percent: 총 수익률

        Returns:
            전송 성공 여부
        """
        message = f"""📈 일간 리포트

💵 총 수익: {total_pnl:+,.0f} KRW ({total_pnl_percent:+.2f}%)
🔄 거래 횟수: {len(trades)}회
🕐 기간: {datetime.now(KST).strftime('%Y-%m-%d')}"""

        if trades:
            message += "\n\n거래 내역:"
            for i, trade in enumerate(trades, 1):
                profit_emoji = "✅" if trade['profit'] > 0 else "❌"
                message += f"""
{profit_emoji} {i}회: {trade['profit_percent']:+.2f}% ({trade['profit']:+,.0f} KRW)"""

        return self._send_message(message)

    def test_connection(self) -> bool:
        """
        텔레그램 연결 테스트

        Returns:
            연결 성공 여부
        """
        message = f"""✅ 테스트 메시지

XRP 자동매매 시스템이 성공적으로 텔레그램에 연결되었습니다.

🕐 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"""

        return self._send_message(message)

    # ─── 텔레그램 명령어 수신 (폴링) ───

    def register_command(self, command: str, callback: Callable[[], str]):
        """
        텔레그램 명령어 콜백 등록

        Args:
            command: 명령어 (예: "/start")
            callback: 콜백 함수 (인자 없음, 응답 문자열 반환)
        """
        self._command_callbacks[command] = callback

    def start_polling(self):
        """텔레그램 메시지 폴링 스레드 시작"""
        if self._polling:
            self.logger.warning("텔레그램 폴링이 이미 실행 중입니다")
            return

        self._polling = True
        self._polling_thread = threading.Thread(
            target=self._polling_loop,
            name="TelegramPolling",
            daemon=True
        )
        self._polling_thread.start()
        self.logger.info("텔레그램 폴링 스레드 시작")

    def stop_polling(self):
        """텔레그램 메시지 폴링 스레드 정지"""
        self._polling = False
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=15)
        self.logger.info("텔레그램 폴링 스레드 정지")

    def _polling_loop(self):
        """getUpdates 폴링 루프 (데몬 스레드에서 실행, 에러 시 지수 백오프)"""
        consecutive_errors = 0
        while self._polling:
            try:
                updates = self._get_updates()
                for update in updates:
                    self._handle_update(update)
                consecutive_errors = 0  # 성공 시 리셋
            except requests.exceptions.RequestException as e:
                consecutive_errors += 1
                # 지수 백오프: 3초, 6초, 12초, ... 최대 120초
                backoff = min(3 * (2 ** (consecutive_errors - 1)), 120)
                if consecutive_errors <= 3 or consecutive_errors % 10 == 0:
                    self.logger.error(
                        f"텔레그램 폴링 네트워크 오류 (연속 {consecutive_errors}회, {backoff}초 대기): {e}"
                    )
                time.sleep(backoff)
                continue
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"텔레그램 폴링 오류: {e}", exc_info=True)

            time.sleep(3)

    def _get_updates(self) -> list:
        """
        Telegram getUpdates API 호출 (long polling)

        Returns:
            업데이트 리스트
        """
        url = f"{self.api_url}/getUpdates"
        params = {
            "offset": self._last_update_id + 1,
            "timeout": 10,
            "allowed_updates": '["message"]'
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()

        data = response.json()
        if not data.get("ok"):
            self.logger.error(f"getUpdates 실패: {data}")
            return []

        return data.get("result", [])

    def _handle_update(self, update: dict):
        """
        수신된 Telegram 업데이트 처리

        Args:
            update: Telegram Update 객체
        """
        update_id = update.get("update_id", 0)
        self._last_update_id = max(self._last_update_id, update_id)

        message = update.get("message")
        if not message:
            return

        # 인증: 허가된 chat_id만 처리
        chat_id = str(message.get("chat", {}).get("id", ""))
        if chat_id != str(self.chat_id):
            self.logger.warning(f"미인증 chat_id: {chat_id}")
            return

        text = message.get("text", "").strip()
        if not text.startswith("/"):
            return

        # 명령어 파싱 ("/command@botname" 형식 대응)
        command = text.split()[0].split("@")[0].lower()

        callback = self._command_callbacks.get(command)
        if callback:
            try:
                response_text = callback()
                self._send_message(response_text)
            except Exception as e:
                self.logger.error(f"명령어 처리 오류 ({command}): {e}", exc_info=True)
                self._send_message(f"명령어 처리 중 오류 발생: {str(e)}")
        else:
            self._send_message(
                f"알 수 없는 명령어: {command}\n/help 로 사용 가능한 명령어를 확인하세요."
            )


class NotificationManager:
    """알림 매니저 클래스"""

    def __init__(self, notifier: TelegramNotifier):
        """
        알림 매니저 초기화

        Args:
            notifier: 텔레그램 알림 객체
        """
        self.notifier = notifier

    def notify_all(
        self,
        message: str,
        include_telegram: bool = True
    ) -> bool:
        """
        모든 알림 채널에 알림 전송

        Args:
            message: 메시지
            include_telegram: 텔레그램 포함 여부

        Returns:
            전송 성공 여부
        """
        success = True

        if include_telegram:
            success &= self.notifier._send_message(message)

        # 로그에도 기록
        logging.getLogger(__name__).info(f"알림: {message}")

        return success
