"""
알림 모듈
"""
import logging
import threading
import time
import requests
from typing import Optional, Dict, Callable
from datetime import datetime


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

    def _send_message(
        self,
        message: str,
        parse_mode: Optional[str] = None
    ) -> bool:
        """
        텔레그램 메시지 전송

        Args:
            message: 메시지 내용
            parse_mode: 파싱 모드 (Markdown, HTML)

        Returns:
            전송 성공 여부
        """
        url = f"{self.api_url}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": message
        }

        if parse_mode:
            data["parse_mode"] = parse_mode

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

        except requests.exceptions.Timeout:
            self.logger.error("텔레그램 요청 타임아웃")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"텔레그램 요청 실패: {str(e)}")
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
        message = f"""📥 **매수 신호**

💰 코인: {currency}
📈 매수 가격: {price:.2f} KRW
📊 매수 수량: {amount:.8f}
💵 주문 금액: {amount * price:,.0f} KRW
⏰ 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        if breakthrough_price is not None:
            message += f"\n\n🎯 돌파 기준선: {breakthrough_price:.2f} KRW"
        if avg_close is not None:
            message += f"\n📊 5봉 종가 평균: {avg_close:.2f} KRW"

        return self._send_message(message, parse_mode="Markdown")

    def send_sell_signal(
        self,
        currency: str,
        amount: float,
        price: float,
        profit: float,
        profit_percent: float,
        duration_hours: float
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

        Returns:
            전송 성공 여부
        """
        profit_emoji = "📈" if profit > 0 else "📉"
        profit_color = profit_percent >= 0

        message = f"""{profit_emoji} **매도 신호**

💰 코인: {currency}
📉 매도 가격: {price:.2f} KRW
📊 매도 수량: {amount:.8f}
💵 회수 금액: {amount * price:,.0f} KRW
{'✅' if profit_color else '❌'} 수익: {profit:+,.0f} KRW ({profit_percent:+.2f}%)
⏰ 보유 시간: {duration_hours:.1f}시간
🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        return self._send_message(message, parse_mode="Markdown")

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
        message = f"""💼 **잔고 현황**

💵 KRW 잔고: {krw_balance:,.0f} KRW
🪙 {coin_symbol} 잔고: {coin_balance:.8f}"""

        if coin_price is not None:
            coin_value = coin_balance * coin_price
            total_value = krw_balance + coin_value
            message += f"\n\n💰 {coin_symbol} 가치: {coin_value:,.0f} KRW"
            message += f"\n📊 총 자산: {total_value:,.0f} KRW (약 {coin_price:.2f} KRW/{coin_symbol})"

        message += f"\n\n🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return self._send_message(message, parse_mode="Markdown")

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
        message = f"""⚠️ **에러 발생**

❌ 에러 타입: {error_type}
📝 에러 메시지: {error_message}
🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        if context:
            message += "\n\n**추가 정보:**"
            for key, value in context.items():
                message += f"\n• {key}: {value}"

        return self._send_message(message, parse_mode="Markdown")

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
        message = f"""📊 **백테스트 요약**

📈 총 수익률: {metrics['total_return_percent']:+.2f}%
📅 연간 수익률: {metrics['annualized_return']:+.2f}%
✅ 승률: {metrics['win_rate']:.2f}%
🔄 총 거래: {trades_count}회
💵 평균 수익: {metrics['avg_profit']:,.0f} KRW
📉 평균 손실: {metrics['avg_loss']:,.0f} KRW
⚖️ 손익비: {metrics['profit_factor']:.2f}
📉 최대 손실률: {metrics['max_drawdown_percent']:.2f}%
📊 샤프 비율: {metrics['sharpe_ratio']:.2f}

🕐 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        return self._send_message(message, parse_mode="Markdown")

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

        message = f"""{status_emoji} **시스템 상태**

{status.upper()}: {message}
🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        return self._send_message(message, parse_mode="Markdown")

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
        message = f"""📈 **일간 리포트**

💵 총 수익: {total_pnl:+,.0f} KRW ({total_pnl_percent:+.2f}%)
🔄 거래 횟수: {len(trades)}회
🕐 기간: {datetime.now().strftime('%Y-%m-%d')}"""

        if trades:
            message += "\n\n**거래 내역:**"
            for i, trade in enumerate(trades, 1):
                profit_emoji = "✅" if trade['profit'] > 0 else "❌"
                message += f"""
{profit_emoji} {i}회: {trade['profit_percent']:+.2f}% ({trade['profit']:+,.0f} KRW)"""

        return self._send_message(message, parse_mode="Markdown")

    def test_connection(self) -> bool:
        """
        텔레그램 연결 테스트

        Returns:
            연결 성공 여부
        """
        message = f"""✅ **테스트 메시지**

XRP 자동매매 시스템이 성공적으로 텔레그램에 연결되었습니다.

🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        return self._send_message(message, parse_mode="Markdown")

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
        """getUpdates 폴링 루프 (데몬 스레드에서 실행)"""
        while self._polling:
            try:
                updates = self._get_updates()
                for update in updates:
                    self._handle_update(update)
            except requests.exceptions.RequestException as e:
                self.logger.error(f"텔레그램 폴링 네트워크 오류: {e}")
            except Exception as e:
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
