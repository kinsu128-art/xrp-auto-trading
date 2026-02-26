"""
데이터 수집 모듈
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time

import requests

from bithumb_api import BithumbAPI, BithumbAPIError
from data_storage import DataStorage


class DataCollector:
    """데이터 수집기 클래스"""

    @staticmethod
    def _interval_ms(chart_intervals: str) -> int:
        """차트 간격 문자열을 밀리초로 변환 (예: '6h' → 21600000)"""
        unit = chart_intervals[-1]
        value = int(chart_intervals[:-1])
        return value * {"h": 3600, "m": 60, "d": 86400}.get(unit, 3600) * 1000

    @staticmethod
    def _filter_forming(candles: List[Dict], chart_intervals: str) -> List[Dict]:
        """현재 형성 중인(아직 마감되지 않은) 캔들을 제거한다.

        빗썸 캔들 API는 현재 진행 중인 봉도 함께 반환한다.
        이 봉은 일부 데이터만 포함하므로 DB에 저장하지 않는다.

        빗썸은 캔들 시작 시각(KST)을 타임스탬프로 사용한다.
        형성 중인 봉의 시작 시각은 현재 UTC 구간 내에 속하므로
        UTC 기준 현재 구간 시작 시각을 기준으로 필터링한다.
        - timestamp < current_period_start → 완성된 봉 → 저장
        - timestamp >= current_period_start → 형성 중인 봉 → 제외
        """
        interval_ms = DataCollector._interval_ms(chart_intervals)
        current_period_start = (int(time.time() * 1000) // interval_ms) * interval_ms
        return [c for c in candles if c["timestamp"] < current_period_start]

    def __init__(self, api: BithumbAPI, storage: DataStorage, logger: Optional[logging.Logger] = None):
        """
        데이터 수집기 초기화

        Args:
            api: 빗썸 API 클라이언트
            storage: 데이터 저장소
            logger: 로거
        """
        self.api = api
        self.storage = storage
        self.logger = logger or logging.getLogger(__name__)

    def fetch_initial_data(
        self,
        order_currency: str = "XRP",
        payment_currency: str = "KRW",
        chart_intervals: str = "6h",
        days: int = 365
    ) -> int:
        """
        과거 데이터 초기 수집

        Args:
            order_currency: 주문 통화
            payment_currency: 결제 통화
            chart_intervals: 차트 간격
            days: 수집할 일수

        Returns:
            수집된 캔들 개수
        """
        self.logger.info(f"{order_currency} 과거 데이터 수집 시작... ({days}일)")

        # 필요한 캔들 개수 계산 (1일 = 4개의 6시간 봉)
        count = days * 4 + 10  # 여유분 추가

        try:
            # API에서 캔들 데이터 수집
            candles = self.api.get_candlestick(
                order_currency=order_currency,
                payment_currency=payment_currency,
                chart_intervals=chart_intervals,
                count=count
            )

            if not candles:
                self.logger.warning("수집된 캔들 데이터가 없습니다.")
                return 0

            # 현재 형성 중인 봉 제거 (마감되지 않은 불완전 데이터)
            candles = self._filter_forming(candles, chart_intervals)
            if not candles:
                self.logger.warning("형성 중인 봉 제외 후 저장할 캔들이 없습니다.")
                return 0

            # 데이터 저장
            saved_count = self.storage.save_candles(candles, order_currency)

            self.logger.info(f"총 {len(candles)}개 캔들 수집, {saved_count}개 저장 완료")

            # 저장된 데이터 정보 로깅
            timestamp_range = self.storage.get_timestamp_range()
            if timestamp_range[0] > 0:
                start_date = datetime.fromtimestamp(timestamp_range[0] / 1000)
                end_date = datetime.fromtimestamp(timestamp_range[1] / 1000)
                self.logger.info(f"데이터 기간: {start_date} ~ {end_date}")

            return saved_count

        except BithumbAPIError as e:
            self.logger.error(f"캔들 데이터 수집 실패: {str(e)}")
            return 0

    def update_data(
        self,
        order_currency: str = "XRP",
        payment_currency: str = "KRW",
        chart_intervals: str = "6h"
    ) -> int:
        """
        실시간 데이터 업데이트

        Args:
            order_currency: 주문 통화
            payment_currency: 결제 통화
            chart_intervals: 차트 간격

        Returns:
            업데이트된 캔들 개수
        """
        self.logger.info(f"{order_currency} 실시간 데이터 업데이트 시작...")

        try:
            # 최신 캔들 조회
            latest_candle = self.storage.get_latest_candle()

            if not latest_candle:
                # 저장된 데이터가 없는 경우 초기 수집
                return self.fetch_initial_data(order_currency, payment_currency, chart_intervals)

            # 캔들 마감 직후 API 데이터 갱신 지연 대비 30초 대기
            self.logger.info("캔들 마감 데이터 반영 대기 (30초)...")
            time.sleep(30)

            # 신규 캔들 조회 재시도 (최대 3회, 30초 간격)
            candle_fetch_max_retries = 3

            for candle_attempt in range(candle_fetch_max_retries):
                new_candles = []
                max_retries = 3

                for attempt in range(max_retries):
                    try:
                        # 최신 데이터 수집 (10개)
                        candles = self.api.get_candlestick(
                            order_currency=order_currency,
                            payment_currency=payment_currency,
                            chart_intervals=chart_intervals,
                            count=10
                        )

                        # 최신 캔들 이후의 데이터 필터링
                        for candle in candles:
                            if candle["timestamp"] > latest_candle["timestamp"]:
                                new_candles.append(candle)

                        break

                    except BithumbAPIError as e:
                        self.logger.warning(f"API 요청 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                        else:
                            raise
                    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                        self.logger.warning(f"네트워크 오류 (시도 {attempt + 1}/{max_retries}): {type(e).__name__}: {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(5)
                        else:
                            self.logger.error(f"네트워크 오류로 캔들 데이터 수집 실패: {str(e)}")
                            return 0

                if new_candles:
                    # 현재 형성 중인 봉 제거 (마감되지 않은 불완전 데이터)
                    completed = self._filter_forming(new_candles, chart_intervals)
                    forming_count = len(new_candles) - len(completed)
                    if forming_count > 0:
                        self.logger.debug(f"형성 중인 봉 {forming_count}개 제외 (미마감)")
                    new_candles = completed

                if new_candles:
                    # 데이터 저장
                    saved_count = self.storage.save_candles(new_candles, order_currency)
                    self.logger.info(f"{len(new_candles)}개 신규 캔들 수집, {saved_count}개 저장 완료")
                    return saved_count

                # 마지막 시도가 아니면 30초 후 재시도
                if candle_attempt < candle_fetch_max_retries - 1:
                    self.logger.info(f"새로운 캔들 없음, 30초 후 재시도 ({candle_attempt + 1}/{candle_fetch_max_retries})")
                    time.sleep(30)

            self.logger.info("새로운 캔들 데이터가 없습니다. (재시도 모두 소진)")
            return 0

        except BithumbAPIError as e:
            self.logger.error(f"데이터 업데이트 실패 (API 오류): {str(e)}")
            return 0
        except (requests.exceptions.RequestException, OSError) as e:
            self.logger.error(f"데이터 업데이트 실패 (네트워크 오류): {type(e).__name__}: {str(e)}")
            return 0
        except Exception as e:
            self.logger.error(f"데이터 업데이트 실패 (예기치 않은 오류): {type(e).__name__}: {str(e)}")
            return 0

    def get_current_candle(
        self,
        order_currency: str = "XRP",
        payment_currency: str = "KRW",
        chart_intervals: str = "6h"
    ) -> Optional[Dict]:
        """
        현재 봉 데이터 조회

        Args:
            order_currency: 주문 통화
            payment_currency: 결제 통화
            chart_intervals: 차트 간격

        Returns:
            현재 캔들 데이터 (마감 전일 경우 None)
        """
        try:
            # 최신 데이터 수집
            candles = self.api.get_candlestick(
                order_currency=order_currency,
                payment_currency=payment_currency,
                chart_intervals=chart_intervals,
                count=5
            )

            if not candles:
                return None

            # 마감된 가장 최신 캔들 반환
            return candles[-1]

        except BithumbAPIError as e:
            self.logger.error(f"현재 캔들 조회 실패: {str(e)}")
            return None

    def validate_candles(self, candles: List[Dict]) -> List[Dict]:
        """
        캔들 데이터 검증 및 정제

        Args:
            candles: 캔들 데이터 리스트

        Returns:
            검증된 캔들 데이터 리스트
        """
        valid_candles = []

        for candle in candles:
            # 필수 필드 확인
            required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
            if not all(field in candle for field in required_fields):
                self.logger.warning(f"필수 필드 누락: {candle}")
                continue

            # Null 값 확인
            if any(candle[field] is None for field in required_fields):
                self.logger.warning(f"Null 값 포함: {candle}")
                continue

            # 데이터 타입 검증
            try:
                candle["timestamp"] = int(candle["timestamp"])
                candle["open"] = float(candle["open"])
                candle["high"] = float(candle["high"])
                candle["low"] = float(candle["low"])
                candle["close"] = float(candle["close"])
                candle["volume"] = float(candle["volume"])
            except (ValueError, TypeError) as e:
                self.logger.warning(f"데이터 타입 오류: {candle}, {str(e)}")
                continue

            # OHLCV 논리 검증
            if not (candle["low"] <= candle["open"] <= candle["high"]):
                self.logger.warning(f"시가가 저가-고가 범위를 벗어남: {candle}")
                continue

            if not (candle["low"] <= candle["close"] <= candle["high"]):
                self.logger.warning(f"종가가 저가-고가 범위를 벗어남: {candle}")
                continue

            if candle["volume"] < 0:
                self.logger.warning(f"음수 거래량: {candle}")
                continue

            valid_candles.append(candle)

        return valid_candles

    def get_latest_closed_candle(
        self,
        order_currency: str = "XRP",
        payment_currency: str = "KRW",
        chart_intervals: str = "6h"
    ) -> Optional[Dict]:
        """
        마감된 최신 캔들 조회

        Args:
            order_currency: 주문 통화
            payment_currency: 결제 통화
            chart_intervals: 차트 간격

        Returns:
            마감된 최신 캔들 데이터
        """
        # 데이터베이스에서 최신 캔들 조회
        latest_candle = self.storage.get_latest_candle()

        if latest_candle:
            return latest_candle

        # 데이터베이스에 데이터가 없는 경우 API에서 조회
        return self.get_current_candle(order_currency, payment_currency, chart_intervals)

    def get_candles_for_backtest(
        self,
        order_currency: str = "XRP",
        days: int = 365
    ) -> List[Dict]:
        """
        백테스트용 캔들 데이터 조회

        Args:
            order_currency: 주문 통화
            days: 조회할 일수

        Returns:
            캔들 데이터 리스트
        """
        # 시작 타임스탬프 계산
        start_timestamp = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

        # 데이터베이스에서 조회
        candles = self.storage.load_candles(start_timestamp=start_timestamp)

        if not candles:
            self.logger.warning(f"백테스트용 데이터가 없습니다. {days}일치 데이터 수집을 먼저 수행하세요.")
        else:
            self.logger.info(f"백테스트용 {len(candles)}개 캔들 로드 완료")

        return candles
