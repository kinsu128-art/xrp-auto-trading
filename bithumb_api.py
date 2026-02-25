"""
빗썸 API 클라이언트 (v2 - JWT 인증)
"""
import time
import math
import hashlib
import uuid
import json
import requests
import jwt
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import urlencode


class BithumbAPIError(Exception):
    """빗썸 API 에러"""
    pass


class BithumbAPI:
    """빗썸 API 클라이언트 클래스 (JWT HS256 인증)"""

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

    # ─── JWT 인증 ───

    def _make_jwt(self, params: Optional[Dict] = None) -> str:
        """
        JWT 토큰 생성 (HS256)

        Args:
            params: 요청 파라미터 (있으면 query_hash 포함)

        Returns:
            JWT 토큰 문자열
        """
        payload = {
            "access_key": self.api_key,
            "nonce": str(uuid.uuid4()),
            "timestamp": round(time.time() * 1000),
        }

        if params:
            query = urlencode(params).encode()
            h = hashlib.sha512()
            h.update(query)
            payload["query_hash"] = h.hexdigest()
            payload["query_hash_alg"] = "SHA512"

        return jwt.encode(payload, self.api_secret, algorithm="HS256")

    def _private_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> any:
        """
        Private API 요청 (JWT 인증)

        Args:
            method: HTTP 메서드 ("GET" 또는 "POST")
            endpoint: API 엔드포인트 (예: "/v1/accounts")
            params: 요청 파라미터

        Returns:
            API 응답 (JSON 파싱 결과)

        Raises:
            BithumbAPIError: API 요청 실패 시
        """
        url = f"{self.api_url}{endpoint}"
        token = self._make_jwt(params)
        headers = {"Authorization": f"Bearer {token}"}

        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            else:
                headers["Content-Type"] = "application/json"
                response = self.session.post(url, json=params, headers=headers, timeout=10)

            response.raise_for_status()
            data = response.json()

            # v2 API 에러 응답 처리
            if isinstance(data, dict) and "error" in data:
                error_info = data["error"]
                error_name = error_info.get("name", "Unknown")
                error_msg = error_info.get("message", str(error_info))
                raise BithumbAPIError(f"API Error: {error_name} - {error_msg}")

            return data

        except requests.exceptions.HTTPError as e:
            try:
                error_detail = response.json()
            except Exception:
                error_detail = response.text[:500]
            raise BithumbAPIError(f"API 요청 실패: {str(e)} - 응답: {error_detail}")
        except requests.exceptions.RequestException as e:
            raise BithumbAPIError(f"API 요청 실패: {str(e)}")

    # ─── Public API (인증 불필요) ───

    def _public_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Public API 요청 (인증 없음)

        Args:
            endpoint: API 엔드포인트
            params: 요청 파라미터

        Returns:
            API 응답

        Raises:
            BithumbAPIError: API 요청 실패 시
        """
        url = f"{self.api_url}{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "status" in data and data["status"] != "0000":
                raise BithumbAPIError(f"API Error: {data.get('message', 'Unknown error')}")

            return data

        except requests.exceptions.RequestException as e:
            raise BithumbAPIError(f"API 요청 실패: {str(e)}")

    def get_candlestick(
        self,
        order_currency: str = "XRP",
        payment_currency: str = "KRW",
        chart_intervals: str = "6h",
        count: int = 100
    ) -> List[Dict]:
        """
        캔들 데이터 조회 (Public API)

        Args:
            order_currency: 주문 통화 (예: XRP)
            payment_currency: 결제 통화 (예: KRW)
            chart_intervals: 차트 간격 (예: 6h)
            count: 가져올 캔들 개수

        Returns:
            캔들 데이터 리스트
        """
        endpoint = f"/public/candlestick/{order_currency}_{payment_currency}/{chart_intervals}"

        try:
            response = self._public_request(endpoint)
            candles = response.get("data", [])

            formatted_candles = []
            for candle in candles:
                formatted_candles.append({
                    "timestamp": candle[0],
                    "open": float(candle[1]),
                    "close": float(candle[2]),
                    "high": float(candle[3]),
                    "low": float(candle[4]),
                    "volume": float(candle[5])
                })

            formatted_candles.sort(key=lambda x: x["timestamp"])

            # count 제한
            if len(formatted_candles) > count:
                formatted_candles = formatted_candles[-count:]

            return formatted_candles

        except Exception as e:
            raise BithumbAPIError(f"캔들 데이터 조회 실패: {str(e)}")

    def get_ticker(self, order_currency: str = "XRP", payment_currency: str = "KRW") -> Dict:
        """
        현재가 정보 조회 (Public API)

        Args:
            order_currency: 주문 통화
            payment_currency: 결제 통화

        Returns:
            현재가 정보
        """
        endpoint = f"/public/ticker/{order_currency}_{payment_currency}"

        try:
            response = self._public_request(endpoint)
            return response.get("data", {})
        except Exception as e:
            raise BithumbAPIError(f"현재가 조회 실패: {str(e)}")

    # ─── Private API (JWT 인증) ───

    def get_balance(self, order_currency: Optional[str] = None) -> Dict:
        """
        잔고 조회 (v2 API: GET /v1/accounts)

        구버전 호환 형식으로 반환:
            {"available_krw": float, "total_krw": float, "available_xrp": float, ...}

        Args:
            order_currency: 특정 통화 (사용하지 않지만 호환성 유지)

        Returns:
            잔고 정보 딕셔너리
        """
        try:
            accounts = self._private_request("GET", "/v1/accounts")

            # 배열 응답을 flat dict로 변환 (구버전 호환)
            result = {}
            for acct in accounts:
                currency = acct.get("currency", "").lower()
                balance = float(acct.get("balance", 0))
                locked = float(acct.get("locked", 0))

                result[f"total_{currency}"] = balance
                result[f"available_{currency}"] = balance - locked

            return result

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
        시장가 매수 (v2 API: POST /v2/orders)

        Args:
            order_currency: 주문 통화 (예: XRP)
            payment_currency: 결제 통화 (예: KRW)
            units: 매수 수량 (시세 환산하여 KRW 금액으로 변환)
            price: 매수 금액 (KRW)

        Returns:
            주문 결과
        """
        market = f"{payment_currency}-{order_currency}"

        if price:
            # KRW 금액으로 시장가 매수
            params = {
                "market": market,
                "side": "bid",
                "ord_type": "price",
                "price": str(price),
            }
        elif units:
            # 수량 지정 매수: 현재 시세로 KRW 환산
            ticker = self.get_ticker(order_currency, payment_currency)
            current_price = float(ticker.get("closing_price", 0))
            krw_amount = float(units) * current_price * 1.01  # 1% 여유 (시장가 슬리피지)
            params = {
                "market": market,
                "side": "bid",
                "ord_type": "price",
                "price": str(int(krw_amount)),
            }
        else:
            raise BithumbAPIError("units 또는 price 중 하나는 필수입니다.")

        try:
            result = self._private_request("POST", "/v2/orders", params)
            return result
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
        시장가 매도 (v2 API: POST /v2/orders)

        Args:
            order_currency: 주문 통화 (예: XRP)
            payment_currency: 결제 통화 (예: KRW)
            units: 매도 수량
            price: 매도 금액 (KRW, 시세 환산하여 수량으로 변환)

        Returns:
            주문 결과

        Note:
            Bithumb v2 API의 ord_type="market" 매도 시 invalid_price_ask 오류 발생.
            현재가 기준 5% 하한 지정가(limit)로 즉시 체결 처리.
            XRP 호가 단위 = 1원 → int(price) 로 단위 맞춤.
        """
        market = f"{payment_currency}-{order_currency}"

        # 현재 시세 조회 (호가 단위 맞추기 위해 필수)
        ticker = self.get_ticker(order_currency, payment_currency)
        current_price = float(ticker.get("closing_price", 0))
        if current_price <= 0:
            raise BithumbAPIError("현재가 조회 실패 - 매도 불가")

        # XRP 호가 단위(1원) 맞추기: 정수로 버림
        # 현재가의 95% 하한가 → 5% 슬리피지 허용으로 즉시 체결 보장
        sell_price = max(1, int(current_price * 0.95))

        if units:
            # 수량 지정 매도 (소수점 4자리 버림 - API 주문 단위 제한)
            volume = float(units)
            truncated = math.floor(volume * 10000) / 10000
            params = {
                "market": market,
                "side": "ask",
                "ord_type": "limit",
                "price": str(sell_price),
                "volume": f"{truncated:.4f}",
            }
        elif price:
            # KRW 금액 지정 매도: 현재 시세로 수량 환산
            volume = float(price) / current_price
            truncated_vol = math.floor(volume * 10000) / 10000
            params = {
                "market": market,
                "side": "ask",
                "ord_type": "limit",
                "price": str(sell_price),
                "volume": f"{truncated_vol:.4f}",
            }
        else:
            raise BithumbAPIError("units 또는 price 중 하나는 필수입니다.")

        try:
            result = self._private_request("POST", "/v2/orders", params)
            return result
        except Exception as e:
            raise BithumbAPIError(f"시장가 매도 실패: {str(e)}")

    def get_order_detail(self, order_id: str, order_currency: str = "") -> Dict:
        """
        주문 상세 조회 (v2 API: GET /v1/order)

        Args:
            order_id: 주문 UUID
            order_currency: 주문 통화 (v2에서는 미사용, 호환성 유지)

        Returns:
            주문 상세 정보
        """
        params = {"uuid": order_id}

        try:
            result = self._private_request("GET", "/v1/order", params)
            return result
        except Exception as e:
            raise BithumbAPIError(f"주문 상세 조회 실패: {str(e)}")

    def get_order_chance(self, order_currency: str = "XRP", payment_currency: str = "KRW") -> Dict:
        """
        주문 가능 정보 조회 (v2 API: GET /v1/orders/chance)

        Args:
            order_currency: 주문 통화
            payment_currency: 결제 통화

        Returns:
            주문 가능 정보 (수수료율, 최소 주문 금액 등)
        """
        market = f"{payment_currency}-{order_currency}"
        params = {"market": market}

        try:
            result = self._private_request("GET", "/v1/orders/chance", params)
            return result
        except Exception as e:
            raise BithumbAPIError(f"주문 가능 정보 조회 실패: {str(e)}")
