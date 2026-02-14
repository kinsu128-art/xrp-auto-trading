"""
빗썸 API 클라이언트
"""
import time
import hashlib
import hmac
import base64
import uuid
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime


class BithumbAPIError(Exception):
    """빗썸 API 에러"""
    pass


class BithumbAPI:
    """빗썸 API 클라이언트 클래스"""

    def __init__(self, api_key: str, api_secret: str, api_url: str = "https://api.bithumb.com"):
        """
        빗썸 API 클라이언트 초기화

        Args:
            api_key: 빗썸 API 키
            api_secret: 빗썸 API 시크릿 키
            api_url: 빗썸 API URL
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_url = api_url
        self.session = requests.Session()

    def _request(self, endpoint: str, params: Optional[Dict] = None, signed: bool = False) -> Dict:
        """
        API 요청 공통 메서드

        Args:
            endpoint: API 엔드포인트
            params: 요청 파라미터
            signed: 서명 여부 (private API인 경우 True)

        Returns:
            API 응답

        Raises:
            BithumbAPIError: API 요청 실패 시
        """
        url = f"{self.api_url}{endpoint}"
        headers = {}

        if signed:
            # 서명 생성
            nonce = str(uuid.uuid4())
            timestamp = str(int(time.time() * 1000))

            if params is None:
                params = {}

            # 쿼리 파라미터 생성
            query = self._make_query(params)
            query += f"&nonce={nonce}&timestamp={timestamp}"

            # HMAC-SHA512 서명
            signature = self._sign(query)
            encoded_signature = base64.b64encode(signature)

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Api-Key": self.api_key,
                "Api-Sign": encoded_signature.decode("utf-8"),
                "Api-Nonce": nonce,
                "Api-Timestamp": timestamp,
            }

            # POST 요청
            response = self.session.post(url, data=params, headers=headers)
        else:
            # GET 요청 (public API)
            if params:
                url += f"?{self._make_query(params)}"
            response = self.session.get(url)

        # 응답 확인
        response.raise_for_status()
        data = response.json()

        # API 에러 확인
        if "status" in data and data["status"] != "0000":
            raise BithumbAPIError(f"API Error: {data.get('message', 'Unknown error')}")

        return data

    def _make_query(self, params: Dict) -> str:
        """
        쿼리 문자열 생성

        Args:
            params: 파라미터 딕셔너리

        Returns:
            쿼리 문자열
        """
        # 파라미터 정렬
        sorted_params = sorted(params.items())
        return "&".join([f"{k}={v}" for k, v in sorted_params])

    def _sign(self, data: str) -> bytes:
        """
        HMAC-SHA512 서명 생성

        Args:
            data: 서명할 데이터

        Returns:
            서명된 바이트
        """
        return hmac.new(
            bytes(self.api_secret, "utf-8"),
            bytes(data, "utf-8"),
            hashlib.sha512
        ).digest()

    def get_candlestick(
        self,
        order_currency: str = "XRP",
        payment_currency: str = "KRW",
        chart_intervals: str = "6h",
        count: int = 100
    ) -> List[Dict]:
        """
        캔들 데이터 조회

        Args:
            order_currency: 주문 통화 (예: XRP)
            payment_currency: 결제 통화 (예: KRW)
            chart_intervals: 차트 간격 (예: 1m, 5m, 10m, 30m, 1h, 6h, 12h, 24h, D, M)
            count: 가져올 캔들 개수 (최대 2000)

        Returns:
            캔들 데이터 리스트

        Raises:
            BithumbAPIError: API 요청 실패 시
        """
        endpoint = f"/public/candlestick/{order_currency}_{payment_currency}/{chart_intervals}"
        params = {"count": count}

        try:
            response = self._request(endpoint, params, signed=False)
            candles = response.get("data", [])

            # 데이터 형식 변환
            formatted_candles = []
            for candle in candles:
                formatted_candles.append({
                    "timestamp": candle[0],  # 타임스탬프
                    "open": float(candle[1]),   # 시가
                    "high": float(candle[2]),   # 고가
                    "low": float(candle[3]),    # 저가
                    "close": float(candle[4]),  # 종가
                    "volume": float(candle[5])  # 거래량
                })

            # 시간순 정렬 (오름차순)
            formatted_candles.sort(key=lambda x: x["timestamp"])
            return formatted_candles

        except Exception as e:
            raise BithumbAPIError(f"캔들 데이터 조회 실패: {str(e)}")

    def get_balance(self, order_currency: Optional[str] = None) -> Dict:
        """
        잔고 조회

        Args:
            order_currency: 특정 통화 잔고 조회 (예: XRP, KRW)

        Returns:
            잔고 정보 딕셔너리

        Raises:
            BithumbAPIError: API 요청 실패 시
        """
        endpoint = "/info/balance"
        params = {}

        if order_currency:
            params["order_currency"] = order_currency

        try:
            response = self._request(endpoint, params, signed=True)
            return response.get("data", {})
        except Exception as e:
            raise BithumbAPIError(f"잔고 조회 실패: {str(e)}")

    def market_buy(
        self,
        order_currency: str,
        payment_currency: str = "KRW",
        units: Optional[str] = None,
        price: Optional[str] = None
    ) -> Dict:
        """
        시장가 매수

        Args:
            order_currency: 주문 통화 (예: XRP)
            payment_currency: 결제 통화 (예: KRW)
            units: 주문 수량
            price: 주문 가격 (KRW, units가 없는 경우)

        Returns:
            주문 결과

        Raises:
            BithumbAPIError: 주문 실패 시
        """
        endpoint = "/trade/market_buy"
        params = {
            "order_currency": order_currency,
            "payment_currency": payment_currency,
        }

        if units:
            params["units"] = units
        elif price:
            params["price"] = price
        else:
            raise BithumbAPIError("units 또는 price 중 하나는 필수입니다.")

        try:
            response = self._request(endpoint, params, signed=True)
            return response.get("data", {})
        except Exception as e:
            raise BithumbAPIError(f"시장가 매수 실패: {str(e)}")

    def market_sell(
        self,
        order_currency: str,
        payment_currency: str = "KRW",
        units: Optional[str] = None,
        price: Optional[str] = None
    ) -> Dict:
        """
        시장가 매도

        Args:
            order_currency: 주문 통화 (예: XRP)
            payment_currency: 결제 통화 (예: KRW)
            units: 주문 수량
            price: 주문 가격 (KRW, units가 없는 경우)

        Returns:
            주문 결과

        Raises:
            BithumbAPIError: 주문 실패 시
        """
        endpoint = "/trade/market_sell"
        params = {
            "order_currency": order_currency,
            "payment_currency": payment_currency,
        }

        if units:
            params["units"] = units
        elif price:
            params["price"] = price
        else:
            raise BithumbAPIError("units 또는 price 중 하나는 필수입니다.")

        try:
            response = self._request(endpoint, params, signed=True)
            return response.get("data", {})
        except Exception as e:
            raise BithumbAPIError(f"시장가 매도 실패: {str(e)}")

    def get_order_detail(self, order_id: str, order_currency: str) -> Dict:
        """
        주문 상세 조회

        Args:
            order_id: 주문 ID
            order_currency: 주문 통화

        Returns:
            주문 상세 정보

        Raises:
            BithumbAPIError: 조회 실패 시
        """
        endpoint = "/info/order_detail"
        params = {
            "order_id": order_id,
            "order_currency": order_currency,
            "payment_currency": "KRW",
        }

        try:
            response = self._request(endpoint, params, signed=True)
            return response.get("data", {})
        except Exception as e:
            raise BithumbAPIError(f"주문 상세 조회 실패: {str(e)}")

    def get_ticker(self, order_currency: str = "XRP", payment_currency: str = "KRW") -> Dict:
        """
        현재가 정보 조회

        Args:
            order_currency: 주문 통화
            payment_currency: 결제 통화

        Returns:
            현재가 정보

        Raises:
            BithumbAPIError: 조회 실패 시
        """
        endpoint = f"/public/ticker/{order_currency}_{payment_currency}"

        try:
            response = self._request(endpoint, signed=False)
            return response.get("data", {})
        except Exception as e:
            raise BithumbAPIError(f"현재가 조회 실패: {str(e)}")
