"""
포트폴리오 관리 모듈
"""
import logging
from typing import Dict, Optional, Tuple, Any


class PortfolioError(Exception):
    """포트폴리오 에러"""
    pass


class Portfolio:
    """포트폴리오 클래스"""

    def __init__(
        self,
        order_currency: str = "XRP",
        payment_currency: str = "KRW",
        min_order_krw: float = 1000.0,  # 최소 주문 금액
        min_order_units: float = 0.001,  # 최소 주문 수량
        fee_rate: float = 0.0025,  # 수수료율 0.25% (빗썸 기본 수수료)
        logger: Optional[logging.Logger] = None,
        storage=None
    ):
        """
        포트폴리오 초기화

        Args:
            order_currency: 주문 통화
            payment_currency: 결제 통화
            min_order_krw: 최소 주문 금액 (KRW)
            min_order_units: 최소 주문 수량
            fee_rate: 수수료율
            logger: 로거
            storage: DataStorage 인스턴스 (포지션 영속화용)
        """
        self.order_currency = order_currency
        self.payment_currency = payment_currency
        self.min_order_krw = min_order_krw
        self.min_order_units = min_order_units
        self.fee_rate = fee_rate
        self.logger = logger or logging.getLogger(__name__)
        self.storage = storage

        # 잔고 초기화
        self.krw_balance = 0.0
        self.coin_balance = 0.0

        # 포지션 초기화
        self.position = None  # {"amount": float, "entry_price": float, "entry_time": datetime}
        self.position_count = 0  # 포지션 횟수

        # DB에서 포지션 복원
        self._restore_position()

    def _restore_position(self):
        """DB에서 포지션 정보 복원 (프로세스 재시작 시)"""
        if not self.storage:
            return

        try:
            saved = self.storage.load_position()
            if saved:
                self.position = {
                    "amount": saved["amount"],
                    "entry_price": saved["entry_price"],
                    "entry_time": saved["entry_time"],
                    "entry_candle": saved["entry_candle"]
                }
                self.position_count = saved["position_count"]
                self.logger.info(
                    f"📦 포지션 복원: {saved['amount']:.8f} @ {saved['entry_price']:.2f} "
                    f"(진입: {saved['entry_time'].strftime('%m/%d %H:%M')})"
                )
        except Exception as e:
            self.logger.error(f"포지션 복원 실패: {e}")

    def update_balance(self, krw_balance: float, coin_balance: float):
        """
        잔고 업데이트

        Args:
            krw_balance: KRW 잔고
            coin_balance: 코인 잔고
        """
        self.krw_balance = krw_balance
        self.coin_balance = coin_balance

        self.logger.debug(
            f"잔고 업데이트: KRW={krw_balance:.2f}, {self.order_currency}={coin_balance:.4f}"
        )

    def get_available_krw(self, use_ratio: float = 1.0) -> float:
        """
        가용 KRW 조회

        Args:
            use_ratio: 사용할 비율 (0.0 ~ 1.0)

        Returns:
            가용 KRW
        """
        available = self.krw_balance * use_ratio

        # 최소 주문 금액 체크
        if available < self.min_order_krw:
            self.logger.warning(f"가용 금액 부족: {available:.0f} < {self.min_order_krw}")

        return available

    def get_coin_balance(self) -> float:
        """
        코인 잔고 조회

        Returns:
            코인 잔고
        """
        return self.coin_balance

    def calculate_buy_amount(
        self,
        price: float,
        use_ratio: float = 1.0,
        min_order_check: bool = True
    ) -> Tuple[float, float]:
        """
        매수 수량 계산

        Args:
            price: 가격
            use_ratio: 사용할 비율 (0.0 ~ 1.0)
            min_order_check: 최소 주문 체크 여부

        Returns:
            (매수 수량, 수수료)
        """
        # 가용 KRW
        available_krw = self.get_available_krw(use_ratio)

        # 수수료 고려한 구매 가능 금액
        buy_amount_krw = available_krw / (1 + self.fee_rate)
        fee = available_krw - buy_amount_krw

        # 수량 계산
        amount = buy_amount_krw / price

        # 최소 주문 수량 체크
        if min_order_check and amount < self.min_order_units:
            raise PortfolioError(
                f"매수 수량이 최소 주문 수량보다 적습니다: "
                f"{amount:.8f} < {self.min_order_units}"
            )

        # 최소 주문 금액 체크
        if min_order_check and (amount * price) < self.min_order_krw:
            raise PortfolioError(
                f"주문 금액이 최소 주문 금액보다 적습니다: "
                f"{amount * price:.0f} < {self.min_order_krw}"
            )

        self.logger.debug(
            f"매수 수량 계산: 가격={price:.2f}, "
            f"수량={amount:.8f}, 수수료={fee:.0f}"
        )

        return amount, fee

    def calculate_sell_amount(
        self,
        price: float,
        use_ratio: float = 1.0,
        min_order_check: bool = True
    ) -> Tuple[float, float]:
        """
        매도 수량 계산

        Args:
            price: 가격
            use_ratio: 사용할 비율 (0.0 ~ 1.0)
            min_order_check: 최소 주문 체크 여부

        Returns:
            (매도 수량, 수수료)
        """
        # 보유 코인
        available_coin = self.coin_balance * use_ratio

        # 매도 금액
        sell_amount_krw = available_coin * price
        fee = sell_amount_krw * self.fee_rate

        # 최소 주문 수량 체크
        if min_order_check and available_coin < self.min_order_units:
            raise PortfolioError(
                f"매도 수량이 최소 주문 수량보다 적습니다: "
                f"{available_coin:.8f} < {self.min_order_units}"
            )

        # 최소 주문 금액 체크
        if min_order_check and sell_amount_krw < self.min_order_krw:
            raise PortfolioError(
                f"주문 금액이 최소 주문 금액보다 적습니다: "
                f"{sell_amount_krw:.0f} < {self.min_order_krw}"
            )

        self.logger.debug(
            f"매도 수량 계산: 가격={price:.2f}, "
            f"수량={available_coin:.8f}, 수수료={fee:.0f}"
        )

        return available_coin, fee

    def open_position(self, amount: float, price: float, candle: Dict):
        """
        포지션 오픈

        Args:
            amount: 수량
            price: 진입 가격
            candle: 캔들 데이터
        """
        from datetime import datetime

        self.position = {
            "amount": amount,
            "entry_price": price,
            "entry_time": datetime.now(),
            "entry_candle": candle
        }
        self.position_count += 1

        # DB에 포지션 영속화
        if self.storage:
            try:
                self.storage.save_position(self.position, self.position_count)
            except Exception as e:
                self.logger.error(f"포지션 DB 저장 실패: {e}")

        self.logger.info(
            f"📥 포지션 오픈: 수량={amount:.8f}, "
            f"진입 가격={price:.2f}, 포지션 #{self.position_count}"
        )

    def close_position(self, price: float) -> Dict:
        """
        포지션 클로즈

        Args:
            price: 청산 가격

        Returns:
            포지션 수익 정보
        """
        if not self.position:
            raise PortfolioError("오픈된 포지션이 없습니다.")

        from datetime import datetime

        entry_price = self.position["entry_price"]
        entry_time = self.position["entry_time"]
        amount = self.position["amount"]

        # 수익 계산
        profit = (price - entry_price) * amount
        profit_percent = (profit / (entry_price * amount)) * 100
        duration = datetime.now() - entry_time

        position_info = {
            "amount": amount,
            "entry_price": entry_price,
            "exit_price": price,
            "profit": profit,
            "profit_percent": profit_percent,
            "entry_time": entry_time,
            "exit_time": datetime.now(),
            "duration": duration,
            "duration_hours": duration.total_seconds() / 3600,
            "position_count": self.position_count
        }

        self.position = None

        # DB에서 포지션 삭제
        if self.storage:
            try:
                self.storage.delete_position()
            except Exception as e:
                self.logger.error(f"포지션 DB 삭제 실패: {e}")

        self.logger.info(
            f"📤 포지션 클로즈: 수익={profit:.0f} ({profit_percent:.2f}%), "
            f"청산 가격={price:.2f}, 포지션 #{position_info['position_count']}"
        )

        return position_info

    def has_position(self) -> bool:
        """
        포지션 보유 여부 확인

        Returns:
            포지션 보유 여부
        """
        return self.position is not None

    def get_position(self) -> Optional[Dict]:
        """
        현재 포지션 조회

        Returns:
            포지션 정보 (없으면 None)
        """
        return self.position

    def get_position_pnl(self, current_price: float) -> Dict:
        """
        현재 포지션의 미실현 수익(PnL) 계산

        Args:
            current_price: 현재 가격

        Returns:
            미실현 수익 정보
        """
        if not self.position:
            return {
                "pnl": 0.0,
                "pnl_percent": 0.0,
                "value": 0.0
            }

        entry_price = self.position["entry_price"]
        amount = self.position["amount"]

        pnl = (current_price - entry_price) * amount
        pnl_percent = (pnl / (entry_price * amount)) * 100
        value = current_price * amount

        return {
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "value": value
        }

    def get_total_value(self, current_price: float) -> float:
        """
        총 자산 가치 계산

        Args:
            current_price: 현재 코인 가격

        Returns:
            총 자산 가치 (KRW)
        """
        coin_value = self.coin_balance * current_price
        total_value = self.krw_balance + coin_value

        return total_value

    def validate_order(
        self,
        is_buy: bool,
        price: float,
        amount: float
    ) -> bool:
        """
        주문 유효성 검증

        Args:
            is_buy: 매수 여부
            price: 가격
            amount: 수량

        Returns:
            유효하면 True, 아니면 False
        """
        # 가격 유효성
        if price <= 0:
            self.logger.error(f"가격이 0 이하입니다: {price}")
            return False

        # 수량 유효성
        if amount <= 0:
            self.logger.error(f"수량이 0 이하입니다: {amount}")
            return False

        # 최소 주문 수량 체크
        if amount < self.min_order_units:
            self.logger.error(
                f"수량이 최소 주문 수량보다 적습니다: "
                f"{amount} < {self.min_order_units}"
            )
            return False

        # 주문 금액 체크
        order_value = price * amount
        if order_value < self.min_order_krw:
            self.logger.error(
                f"주문 금액이 최소 주문 금액보다 적습니다: "
                f"{order_value} < {self.min_order_krw}"
            )
            return False

        # 잔고 체크
        if is_buy:
            if self.krw_balance < order_value:
                self.logger.error(f"KRW 잔고 부족: {self.krw_balance} < {order_value}")
                return False
        else:
            if self.coin_balance < amount:
                self.logger.error(
                    f"{self.order_currency} 잔고 부족: "
                    f"{self.coin_balance} < {amount}"
                )
                return False

        return True

    def get_summary(self, current_price: float) -> Dict:
        """
        포트폴리오 요약

        Args:
            current_price: 현재 코인 가격

        Returns:
            요약 정보
        """
        total_value = self.get_total_value(current_price)
        position_pnl = self.get_position_pnl(current_price)

        return {
            "krw_balance": self.krw_balance,
            "coin_balance": self.coin_balance,
            "coin_value": self.coin_balance * current_price,
            "total_value": total_value,
            "has_position": self.has_position(),
            "position_count": self.position_count,
            "position_pnl": position_pnl.get("pnl", 0.0),
            "position_pnl_percent": position_pnl.get("pnl_percent", 0.0)
        }
