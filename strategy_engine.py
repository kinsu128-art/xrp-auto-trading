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
        1. 현재봉 종가 > 시가 + (전봉 고가 - 전봉 저가) × 0.5
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

        # 조건 1: 돌파 기준선 돌파 (종가 기준)
        condition1 = current_candle["close"] > breakthrough_price
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

        조건: 돌파기준선이 5봉 평균 이하로 내려가면 매도 (조건 2 미충족)
              인트라데이 방식에서는 조건 1은 다음 봉 진입 시 사용하므로 매도에는 제외

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

        if len(candles) < 2:
            return {
                "should_sell": False,
                "sell_price": 0.0,
                "reason": "캔들 데이터 부족"
            }

        buy_candle = position["entry_candle"]
        current_candle = candles[-1]

        # 매수 캔들이 아직 마감되지 않았으면 대기
        if current_candle["timestamp"] <= buy_candle["timestamp"]:
            return {
                "should_sell": False,
                "sell_price": 0.0,
                "reason": "아직 매수 캔들 마감 안됨"
            }

        # 인트라데이 감시 조건 재평가 (조건 2: above_avg 만 확인)
        watch_info = self.get_intraday_watch_price(candles)
        above_avg = watch_info["conditions"].get("above_avg", False)

        if above_avg:
            # 조건 2 유지 → 포지션 보유 계속
            self.logger.info(
                f"📊 매수 조건 유지 중 - 포지션 보유 계속 "
                f"(돌파기준선={watch_info['breakthrough_price']:.2f} > 5봉평균={watch_info['avg_close']:.2f})"
            )
            return {
                "should_sell": False,
                "sell_price": 0.0,
                "reason": "매수 조건 유지 중"
            }
        else:
            # 조건 2 미충족 → 매도 (현재 마감봉 종가 기준 시장가 매도)
            sell_price = current_candle["close"]
            reason_str = f"돌파기준선({watch_info['breakthrough_price']:.2f}) <= 5봉평균({watch_info['avg_close']:.2f})"
            self.logger.info(f"📤 매도 신호 발생! 사유: {reason_str}, 매도 가격: {sell_price:.2f}")
            return {
                "should_sell": True,
                "sell_price": sell_price,
                "reason": reason_str
            }

    def get_intraday_watch_price(self, closed_candles: List[Dict]) -> Dict:
        """
        인트라데이 감시용 돌파 기준선 및 사전 조건 확인

        캔들 마감 시 호출 → 다음 봉 형성 기간 동안 감시할 기준선 반환

        조건 평가 기준 (이전 마감 봉):
          - 조건 2: 돌파기준선 > 최근 5봉 종가 평균 (마감 봉 기준)
          - 조건 3: 직전 마감 봉 거래량 > 그 이전 봉 거래량 (마감 봉 기준)

        Returns:
            {
                "should_watch": bool,
                "breakthrough_price": float,
                "avg_close": float,
                "conditions": {"above_avg": bool, "volume_increase": bool}
            }
        """
        if len(closed_candles) < self.num_candles_for_avg + 1:
            return {
                "should_watch": False,
                "breakthrough_price": 0.0,
                "avg_close": 0.0,
                "conditions": {"above_avg": False, "volume_increase": False}
            }

        current_candle = closed_candles[-1]
        prev_candle = closed_candles[-2]
        last_n_candles = closed_candles[-(self.num_candles_for_avg + 1):-1]

        # 돌파기준선 계산
        breakthrough_price = self._calculate_breakthrough_price(prev_candle, current_candle)

        # 조건 2: 돌파기준선 > 최근 5봉 종가 평균
        avg_close = sum(c["close"] for c in last_n_candles) / len(last_n_candles)
        condition2 = breakthrough_price > avg_close

        # 조건 3: 이전봉 거래량 < 현재봉 거래량
        condition3 = prev_candle["volume"] < current_candle["volume"]

        should_watch = condition2 and condition3

        if should_watch:
            self.logger.info(
                f"👁 인트라데이 감시 시작: 돌파기준선={breakthrough_price:.2f}, "
                f"5봉평균={avg_close:.2f}"
            )
        else:
            self.logger.debug(
                f"👁 인트라데이 감시 미설정: above_avg={condition2}, volume_inc={condition3}"
            )

        return {
            "should_watch": should_watch,
            "breakthrough_price": breakthrough_price,
            "avg_close": avg_close,
            "conditions": {
                "above_avg": condition2,
                "volume_increase": condition3
            }
        }

    def _calculate_breakthrough_price(self, prev_candle: Dict, current_candle: Dict) -> float:
        """
        돌파 기준선 가격 계산

        돌파 기준선 = 현재봉 종가 + (현재봉 고가 - 현재봉 저가) × 배율

        Args:
            prev_candle: 이전 캔들
            current_candle: 현재 캔들

        Returns:
            돌파 기준선 가격
        """
        current_range = current_candle["high"] - current_candle["low"]
        breakthrough_price = current_candle["close"] + current_range * self.breakthrough_ratio
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
                f"현재봉 종가 > 시가 + (전봉 고가 - 전봉 저가) × {self.breakthrough_ratio}",
                f"돌파 기준선 가격 > 최근 {self.num_candles_for_avg}봉 종가 평균",
                "전봉 거래량 < 현재봉 거래량"
            ],
            "sell_conditions": [
                "조건2 미충족 시 매도 (돌파기준선 <= 5봉 평균)",
                "조건3(거래량)은 매도 판단에서 제외",
                "조건2 유지 중이면 포지션 보유 계속"
            ]
        }
