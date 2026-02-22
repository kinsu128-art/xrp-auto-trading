"""
전략 엔진 모듈
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class StrategyEngine:
    """전략 엔진 기본 클래스"""

    def check_buy_signal(self, candles: List[Dict]) -> Dict:
        """
        매수 신호 확인

        Args:
            candles: 캔들 데이터 리스트

        Returns:
            매수 신호 정보
        """
        raise NotImplementedError

    def check_sell_signal(self, candles: List[Dict], position: Dict) -> Dict:
        """
        매도 신호 확인

        Args:
            candles: 캔들 데이터 리스트
            position: 포지션 정보

        Returns:
            매도 신호 정보
        """
        raise NotImplementedError


class LarryWilliamsStrategy(StrategyEngine):
    """래리 윌리엄스 돌파 전략"""

    def __init__(
        self,
        breakthrough_ratio: float = 0.5,
        num_candles_for_avg: int = 5,
        logger: Optional[logging.Logger] = None
    ):
        """
        래리 윌리엄스 전략 초기화

        Args:
            breakthrough_ratio: 돌파 배율 (기본 0.5)
            num_candles_for_avg: 평균 계산 캔들 개수 (기본 5)
            logger: 로거
        """
        self.breakthrough_ratio = breakthrough_ratio
        self.num_candles_for_avg = num_candles_for_avg
        self.logger = logger or logging.getLogger(__name__)

    def check_buy_signal(self, candles: List[Dict]) -> Dict:
        """
        래리 윌리엄스 매수 조건 확인

        조건 (3가지 모두 충족):
        1. 현재봉 고가 > 시가 + (전봉 고가 - 전봉 저가) × 0.5
        2. 돌파 기준선 가격 > 최근 5봉 종가 평균
        3. 전봉 거래량 < 현재봉 거래량

        Args:
            candles: 캔들 데이터 리스트 (최소 6개 필요)

        Returns:
            매수 신호 정보:
            {
                "should_buy": bool,
                "breakthrough_price": float,
                "reasons": List[str],
                "conditions": Dict[str, bool]
            }
        """
        if len(candles) < self.num_candles_for_avg + 1:
            self.logger.warning(f"매수 조건 확인 불가: 필요한 캔들 개수 부족 (현재: {len(candles)}, 필요: {self.num_candles_for_avg + 1})")
            return {
                "should_buy": False,
                "breakthrough_price": 0.0,
                "reasons": ["데이터 부족"],
                "conditions": {}
            }

        # 현재 캔들과 이전 캔들 분리
        current_candle = candles[-1]
        prev_candle = candles[-2]
        last_n_candles = candles[-(self.num_candles_for_avg + 1):-1]  # 최근 N봉 (현재봉 제외)

        # 돌파 기준선 가격 계산
        breakthrough_price = self._calculate_breakthrough_price(prev_candle, current_candle)

        # 매수 조건 검증
        conditions = {}
        reasons = []

        # 조건 1: 돌파 기준선 돌파
        condition1 = current_candle["high"] > breakthrough_price
        conditions["breakthrough"] = condition1
        if not condition1:
            reasons.append("돌파 기준선 미달")

        # 조건 2: 5봉 종가 평균 상회
        avg_close = sum(c["close"] for c in last_n_candles) / len(last_n_candles)
        condition2 = breakthrough_price > avg_close
        conditions["above_avg"] = condition2
        if not condition2:
            reasons.append("5봉 종가 평균 미달")

        # 조건 3: 거래량 증가
        condition3 = prev_candle["volume"] < current_candle["volume"]
        conditions["volume_increase"] = condition3
        if not condition3:
            reasons.append("거래량 감소")

        # 모든 조건 충족 시 매수 신호
        should_buy = all(conditions.values())

        if should_buy:
            self.logger.info(f"✅ 매수 신호 발생! 돌파 기준선: {breakthrough_price:.2f}, 평균 종가: {avg_close:.2f}")
        else:
            self.logger.debug(f"❌ 매수 조건 미충족: {', '.join(reasons)}")

        return {
            "should_buy": should_buy,
            "breakthrough_price": breakthrough_price,
            "avg_close": avg_close,
            "reasons": reasons,
            "conditions": conditions
        }

    def check_sell_signal(self, candles: List[Dict], position: Dict) -> Dict:
        """
        래리 윌리엄스 매도 조건 확인

        조건: 매수 후 다음 4시간 봉 시가에 매도

        Args:
            candles: 캔들 데이터 리스트
            position: 포지션 정보

        Returns:
            매도 신호 정보:
            {
                "should_sell": bool,
                "sell_price": float,
                "reason": str
            }
        """
        if not position:
            return {
                "should_sell": False,
                "sell_price": 0.0,
                "reason": "포지션 없음"
            }

        # 다음 캔들 확인
        if len(candles) < 2:
            return {
                "should_sell": False,
                "sell_price": 0.0,
                "reason": "다음 캔들 없음"
            }

        # 현재 캔들 (매수가 발생한 캔들)과 다음 캔들 확인
        buy_candle = position["entry_candle"]
        current_candle = candles[-1]

        # 매수 후 첫 번째 마감 캔들인지 확인
        if current_candle["timestamp"] <= buy_candle["timestamp"]:
            return {
                "should_sell": False,
                "sell_price": 0.0,
                "reason": "아직 매수 캔들 마감 안됨"
            }

        # 다음 캔들의 시가에 매도
        should_sell = True
        sell_price = current_candle["open"]

        self.logger.info(f"📤 매도 신호 발생! 매도 가격: {sell_price:.2f}")

        return {
            "should_sell": should_sell,
            "sell_price": sell_price,
            "reason": "다음 4시간 봉 시가"
        }

    def _calculate_breakthrough_price(self, prev_candle: Dict, current_candle: Dict) -> float:
        """
        돌파 기준선 가격 계산

        돌파 기준선 = 현재봉 시가 + (전봉 고가 - 전봉 저가) × 배율

        Args:
            prev_candle: 이전 캔들
            current_candle: 현재 캔들

        Returns:
            돌파 기준선 가격
        """
        prev_range = prev_candle["high"] - prev_candle["low"]
        breakthrough_price = current_candle["open"] + prev_range * self.breakthrough_ratio
        return breakthrough_price

    def calculate_expected_profit(self, buy_price: float, sell_price: float) -> Dict:
        """
        예상 수익 계산

        Args:
            buy_price: 매수 가격
            sell_price: 매도 가격

        Returns:
            수익 정보:
            {
                "profit": float,
                "profit_percent": float,
                "is_profit": bool
            }
        """
        profit = sell_price - buy_price
        profit_percent = (profit / buy_price) * 100 if buy_price > 0 else 0

        return {
            "profit": profit,
            "profit_percent": profit_percent,
            "is_profit": profit > 0
        }

    def validate_candles(self, candles: List[Dict]) -> bool:
        """
        캔들 데이터 유효성 검증

        Args:
            candles: 캔들 데이터 리스트

        Returns:
            유효하면 True, 아니면 False
        """
        if not candles:
            self.logger.warning("캔들 데이터 없음")
            return False

        if len(candles) < self.num_candles_for_avg + 1:
            self.logger.warning(f"캔들 데이터 부족 (현재: {len(candles)}, 필요: {self.num_candles_for_avg + 1})")
            return False

        # 필수 필드 확인
        required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
        for candle in candles:
            if not all(field in candle for field in required_fields):
                self.logger.error(f"필수 필드 누락: {candle}")
                return False

        return True

    def get_strategy_summary(self) -> Dict:
        """
        전략 요약 정보 반환

        Returns:
            전략 요약:
            {
                "name": str,
                "breakthrough_ratio": float,
                "num_candles_for_avg": int,
                "buy_conditions": List[str],
                "sell_conditions": List[str]
            }
        """
        return {
            "name": "Larry Williams Breakthrough Strategy",
            "breakthrough_ratio": self.breakthrough_ratio,
            "num_candles_for_avg": self.num_candles_for_avg,
            "buy_conditions": [
                f"현재봉 고가 > 시가 + (전봉 고가 - 전봉 저가) × {self.breakthrough_ratio}",
                f"돌파 기준선 가격 > 최근 {self.num_candles_for_avg}봉 종가 평균",
                "전봉 거래량 < 현재봉 거래량"
            ],
            "sell_conditions": [
                "매수 후 다음 4시간 봉 시가에 매도"
            ]
        }
