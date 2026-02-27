"""
주문 실행 모듈
"""
import logging
import time
from typing import Dict, Optional
from datetime import datetime

from bithumb_api import BithumbAPI, BithumbAPIError


class OrderExecutionError(Exception):
    """주문 실행 에러"""
    pass


class OrderExecutor:
    """주문 실행기 클래스"""

    def __init__(
        self,
        api: BithumbAPI,
        logger: Optional[logging.Logger] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        주문 실행기 초기화

        Args:
            api: 빗썸 API 클라이언트
            logger: 로거
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 간격 (초)
        """
        self.api = api
        self.logger = logger or logging.getLogger(__name__)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def market_buy(
        self,
        order_currency: str = "XRP",
        payment_currency: str = "KRW",
        amount_krw: Optional[float] = None,
        units: Optional[float] = None
    ) -> Dict:
        """
        시장가 매수

        Args:
            order_currency: 주문 통화
            payment_currency: 결제 통화
            amount_krw: 매수 금액 (KRW)
            units: 매수 수량

        Returns:
            주문 결과 딕셔너리

        Raises:
            OrderExecutionError: 주문 실행 실패 시
        """
        for attempt in range(self.max_retries):
            try:
                if amount_krw:
                    # 금액으로 매수
                    self.logger.info(f"📥 시장가 매수 시도... ({amount_krw:.0f} KRW)")
                    result = self.api.market_buy(
                        order_currency=order_currency,
                        payment_currency=payment_currency,
                        price=str(int(amount_krw))
                    )
                elif units:
                    # 수량으로 매수
                    self.logger.info(f"📥 시장가 매수 시도... ({units:.4f} {order_currency})")
                    result = self.api.market_buy(
                        order_currency=order_currency,
                        payment_currency=payment_currency,
                        units=str(units)
                    )
                else:
                    raise OrderExecutionError("amount_krw 또는 units 중 하나는 필수입니다.")

                self.logger.info(f"✅ 시장가 매수 완료: {result}")
                return result

            except BithumbAPIError as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(
                        f"⚠️  시장가 매수 실패 (시도 {attempt + 1}/{self.max_retries}): {str(e)}"
                    )
                    time.sleep(self.retry_delay * (attempt + 1))  # 지수 백오프
                else:
                    self.logger.error(f"❌ 시장가 매수 최종 실패: {str(e)}")
                    raise OrderExecutionError(f"시장가 매수 실패: {str(e)}")

    def market_sell(
        self,
        order_currency: str = "XRP",
        payment_currency: str = "KRW",
        units: Optional[float] = None,
        price_krw: Optional[float] = None
    ) -> Dict:
        """
        시장가 매도

        Args:
            order_currency: 주문 통화
            payment_currency: 결제 통화
            units: 매도 수량
            price_krw: 매도 금액 (KRW, units가 없는 경우)

        Returns:
            주문 결과 딕셔너리

        Raises:
            OrderExecutionError: 주문 실행 실패 시
        """
        for attempt in range(self.max_retries):
            try:
                if units:
                    # 수량으로 매도
                    self.logger.info(f"📤 시장가 매도 시도... ({units:.4f} {order_currency})")
                    result = self.api.market_sell(
                        order_currency=order_currency,
                        payment_currency=payment_currency,
                        units=str(units)
                    )
                elif price_krw:
                    # 금액으로 매도
                    self.logger.info(f"📤 시장가 매도 시도... ({price_krw:.0f} KRW)")
                    result = self.api.market_sell(
                        order_currency=order_currency,
                        payment_currency=payment_currency,
                        price=str(int(price_krw))
                    )
                else:
                    raise OrderExecutionError("units 또는 price_krw 중 하나는 필수입니다.")

                self.logger.info(f"✅ 시장가 매도 완료: {result}")
                return result

            except BithumbAPIError as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(
                        f"⚠️  시장가 매도 실패 (시도 {attempt + 1}/{self.max_retries}): {str(e)}"
                    )
                    time.sleep(self.retry_delay * (attempt + 1))  # 지수 백오프
                else:
                    self.logger.error(f"❌ 시장가 매도 최종 실패: {str(e)}")
                    raise OrderExecutionError(f"시장가 매도 실패: {str(e)}")

    def limit_buy(
        self,
        order_currency: str = "XRP",
        payment_currency: str = "KRW",
        price: float = 0.0,
        units: float = 0.0
    ) -> Dict:
        """
        지정가 매수

        Args:
            order_currency: 주문 통화
            payment_currency: 결제 통화
            price: 지정가 (KRW)
            units: 매수 수량

        Returns:
            주문 결과 딕셔너리

        Raises:
            OrderExecutionError: 주문 실행 실패 시
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"📥 지정가 매수 주문... ({units:.4f} {order_currency} @ {price:,.2f} KRW)")
                result = self.api.limit_buy(
                    order_currency=order_currency,
                    payment_currency=payment_currency,
                    price=price,
                    volume=units
                )
                self.logger.info(f"✅ 지정가 매수 주문 접수: {result}")
                return result

            except BithumbAPIError as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(
                        f"⚠️  지정가 매수 실패 (시도 {attempt + 1}/{self.max_retries}): {str(e)}"
                    )
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    self.logger.error(f"❌ 지정가 매수 최종 실패: {str(e)}")
                    raise OrderExecutionError(f"지정가 매수 실패: {str(e)}")

    def cancel_order(self, order_id: str) -> Dict:
        """
        주문 취소

        Args:
            order_id: 주문 UUID

        Returns:
            취소 결과 딕셔너리

        Raises:
            OrderExecutionError: 취소 실패 시
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"🚫 주문 취소 시도... ({order_id[:8]}...)")
                result = self.api.cancel_order(order_id)
                self.logger.info(f"✅ 주문 취소 완료: {result}")
                return result

            except BithumbAPIError as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(
                        f"⚠️  주문 취소 실패 (시도 {attempt + 1}/{self.max_retries}): {str(e)}"
                    )
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    self.logger.error(f"❌ 주문 취소 최종 실패: {str(e)}")
                    raise OrderExecutionError(f"주문 취소 실패: {str(e)}")

    def get_balance(self, currency: Optional[str] = None) -> Dict:
        """
        잔고 조회

        Args:
            currency: 특정 통화 잔고 (None이면 전체 잔고)

        Returns:
            잔고 정보 딕셔너리

        Raises:
            OrderExecutionError: 조회 실패 시
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"📊 잔고 조회 시도... ({currency or '전체'})")
                result = self.api.get_balance(order_currency=currency)
                self.logger.debug(f"✅ 잔고 조회 완료: {result}")
                return result

            except BithumbAPIError as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(
                        f"⚠️  잔고 조회 실패 (시도 {attempt + 1}/{self.max_retries}): {str(e)}"
                    )
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    self.logger.error(f"❌ 잔고 조회 최종 실패: {str(e)}")
                    raise OrderExecutionError(f"잔고 조회 실패: {str(e)}")

    def get_order_status(self, order_id: str, order_currency: str) -> Dict:
        """
        주문 상태 조회

        Args:
            order_id: 주문 ID
            order_currency: 주문 통화

        Returns:
            주문 상태 딕셔너리

        Raises:
            OrderExecutionError: 조회 실패 시
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"📋 주문 상태 조회... ({order_id})")
                result = self.api.get_order_detail(order_id, order_currency)
                self.logger.debug(f"✅ 주문 상태 조회 완료: {result}")
                return result

            except BithumbAPIError as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(
                        f"⚠️  주문 상태 조회 실패 (시도 {attempt + 1}/{self.max_retries}): {str(e)}"
                    )
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    self.logger.error(f"❌ 주문 상태 조회 최종 실패: {str(e)}")
                    raise OrderExecutionError(f"주문 상태 조회 실패: {str(e)}")
