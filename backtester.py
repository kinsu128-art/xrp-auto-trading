"""
백테스터 모듈
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np

from strategy_engine import StrategyEngine


class BacktestResult:
    """백테스트 결과 클래스"""

    def __init__(self):
        self.trades = []  # 거래 내역
        self.equity_curve = []  # 수익률 곡선
        self.initial_capital = 1000000.0  # 초기 자본 (KRW)
        self.final_capital = 0.0  # 최종 자본
        self.total_trades = 0  # 총 거래 횟수
        self.winning_trades = 0  # 승리 횟수
        self.losing_trades = 0  # 패배 횟수
        self.total_profit = 0.0  # 총 수익
        self.total_loss = 0.0  # 총 손실
        self.max_profit = 0.0  # 최대 수익
        self.max_loss = 0.0  # 최대 손실
        self.max_drawdown = 0.0  # 최대 손실률
        self.max_drawdown_duration = 0  # 최대 손실 지속 기간

    def add_trade(self, trade: Dict):
        """거래 추가"""
        self.trades.append(trade)

    def calculate_metrics(self) -> Dict:
        """
        성과 지표 계산

        Returns:
            성과 지표 딕셔너리
        """
        if not self.trades:
            return {
                "total_return": 0.0,
                "total_return_percent": 0.0,
                "annualized_return": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "avg_profit": 0.0,
                "avg_loss": 0.0
            }

        # 총 수익률 계산
        total_return = self.final_capital - self.initial_capital
        total_return_percent = (total_return / self.initial_capital) * 100

        # 연간 수익률 계산 (첫 거래 ~ 마지막 거래의 실제 기간 사용)
        first_trade_time = self.trades[0]["entry_time"]
        last_trade_time = self.trades[-1]["exit_time"]
        duration = (last_trade_time - first_trade_time).total_seconds()
        days = duration / 86400 if duration > 0 else 0
        if days > 0:
            annualized_return = ((self.final_capital / self.initial_capital) ** (365 / days) - 1) * 100
        else:
            annualized_return = 0.0

        # 승률 계산
        win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0

        # 손익비 계산
        avg_profit = self.total_profit / self.winning_trades if self.winning_trades > 0 else 0
        avg_loss = abs(self.total_loss / self.losing_trades) if self.losing_trades > 0 else 0
        profit_factor = self.total_profit / abs(self.total_loss) if self.total_loss != 0 else float('inf')

        # 샤프 비율 계산 (무위험 이자율 0% 가정)
        if self.equity_curve and len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                ret = (self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1]
                returns.append(ret)

            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = (avg_return / std_return) * np.sqrt(365 * 4) if std_return > 0 else 0
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0

        return {
            "total_return": total_return,
            "total_return_percent": total_return_percent,
            "annualized_return": annualized_return,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_percent": self.max_drawdown * 100,
            "sharpe_ratio": sharpe_ratio,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "max_profit": self.max_profit,
            "max_loss": self.max_loss
        }


class Backtester:
    """백테스터 클래스"""

    def __init__(
        self,
        strategy: StrategyEngine,
        initial_capital: float = 1000000.0,
        fee_rate: float = 0.0015,  # 0.15% 수수료
        logger: Optional[logging.Logger] = None
    ):
        """
        백테스터 초기화

        Args:
            strategy: 전략 엔진
            initial_capital: 초기 자본 (KRW)
            fee_rate: 수수료율
            logger: 로거
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.logger = logger or logging.getLogger(__name__)

    def run(self, candles: List[Dict]) -> BacktestResult:
        """
        백테스트 실행

        Args:
            candles: 캔들 데이터 리스트

        Returns:
            백테스트 결과
        """
        self.logger.info(f"백테스트 시작... 캔들 개수: {len(candles)}")

        result = BacktestResult()
        result.initial_capital = self.initial_capital
        capital = self.initial_capital
        position = None  # 포지션 정보
        peak_equity = self.initial_capital
        current_drawdown = 0.0
        current_drawdown_duration = 0

        # 수수료 계산 (0.15% 매수/매도 각각)
        buy_fee_rate = self.fee_rate
        sell_fee_rate = self.fee_rate

        # 캔들 데이터 순회 (최소 6개 필요: 매수 조건 1개 + 이전 5봉)
        for i, candle in enumerate(candles):
            # 초기 6봉은 스킵 (매수 조건 확인 불가)
            if i < 6:
                continue

            # 현재까지의 캔들 데이터
            current_candles = candles[:i+1]

            # 매수 조건 확인 (포지션 없을 때만) - 인트라데이 방식
            if position is None:
                watch_info = self.strategy.get_intraday_watch_price(current_candles)

                if watch_info["should_watch"] and i + 1 < len(candles):
                    next_candle = candles[i + 1]
                    breakthrough_price = watch_info["breakthrough_price"]

                    # 다음 봉에서 돌파기준선 도달 여부 (고가 기준)
                    if next_candle["high"] >= breakthrough_price:
                        buy_price = breakthrough_price
                        buy_fee = capital * buy_fee_rate
                        buy_amount = (capital - buy_fee) / buy_price

                        position = {
                            "entry_price": buy_price,
                            "amount": buy_amount,
                            "capital": capital,
                            "entry_candle": next_candle,   # 실제 체결된 봉
                            "entry_index": i + 1,
                            "entry_time": datetime.fromtimestamp(next_candle["timestamp"] / 1000)
                        }

                        self.logger.debug(
                            f"📥 매수: 돌파기준선={buy_price:.2f}, "
                            f"수량={buy_amount:.4f}, 자본={capital:.0f}"
                        )

            # 매도 조건 확인 (포지션 있을 때만)
            else:
                sell_signal = self.strategy.check_sell_signal(current_candles, position)

                if sell_signal["should_sell"]:
                    # 매도 실행
                    sell_price = sell_signal["sell_price"]
                    sell_fee = position["amount"] * sell_price * sell_fee_rate
                    sell_amount = position["amount"] * sell_price - sell_fee

                    # 수익 계산
                    profit = sell_amount - position["capital"]
                    profit_percent = (profit / position["capital"]) * 100

                    # 거래 내역 저장
                    trade = {
                        "entry_price": position["entry_price"],
                        "exit_price": sell_price,
                        "amount": position["amount"],
                        "profit": profit,
                        "profit_percent": profit_percent,
                        "entry_time": position["entry_time"],
                        "exit_time": datetime.fromtimestamp(candle["timestamp"] / 1000),
                        "duration_hours": (candle["timestamp"] - position["entry_candle"]["timestamp"]) / 3600000
                    }
                    result.add_trade(trade)

                    # 통계 업데이트
                    result.total_trades += 1
                    if profit > 0:
                        result.winning_trades += 1
                        result.total_profit += profit
                        result.max_profit = max(result.max_profit, profit)
                    else:
                        result.losing_trades += 1
                        result.total_loss += profit
                        result.max_loss = min(result.max_loss, profit)

                    # 자본 업데이트
                    capital = sell_amount

                    self.logger.debug(f"📤 매도: 가격 {sell_price:.2f}, 수익 {profit:.0f} ({profit_percent:.2f}%)")

                    # 수익률 곡선 업데이트
                    result.equity_curve.append(capital)

                    # 최대 손실률 계산
                    if capital > peak_equity:
                        peak_equity = capital
                        current_drawdown = 0.0
                        current_drawdown_duration = 0
                    else:
                        drawdown = (peak_equity - capital) / peak_equity
                        if drawdown > result.max_drawdown:
                            result.max_drawdown = drawdown
                        current_drawdown = drawdown
                        current_drawdown_duration += 1

                    # 포지션 초기화
                    position = None

        # 포지션이 남아있는 경우 강제 청산 (마지막 가격으로)
        if position:
            last_candle = candles[-1]
            sell_price = last_candle["close"]
            sell_fee = position["amount"] * sell_price * sell_fee_rate
            sell_amount = position["amount"] * sell_price - sell_fee
            profit = sell_amount - position["capital"]
            profit_percent = (profit / position["capital"]) * 100

            trade = {
                "entry_price": position["entry_price"],
                "exit_price": sell_price,
                "amount": position["amount"],
                "profit": profit,
                "profit_percent": profit_percent,
                "entry_time": position["entry_time"],
                "exit_time": datetime.fromtimestamp(last_candle["timestamp"] / 1000),
                "duration_hours": (last_candle["timestamp"] - position["entry_candle"]["timestamp"]) / 3600000,
                "forced_close": True
            }
            result.add_trade(trade)

            result.total_trades += 1
            if profit > 0:
                result.winning_trades += 1
                result.total_profit += profit
            else:
                result.losing_trades += 1
                result.total_loss += profit

            capital = sell_amount
            result.equity_curve.append(capital)
            position = None

        result.final_capital = capital

        # 성과 지표 계산
        metrics = result.calculate_metrics()

        self.logger.info(f"백테스트 완료!")
        self.logger.info(f"  총 수익률: {metrics['total_return_percent']:.2f}%")
        self.logger.info(f"  연간 수익률: {metrics['annualized_return']:.2f}%")
        self.logger.info(f"  승률: {metrics['win_rate']:.2f}%")
        self.logger.info(f"  손익비: {metrics['profit_factor']:.2f}")
        self.logger.info(f"  최대 손실률: {metrics['max_drawdown_percent']:.2f}%")
        self.logger.info(f"  샤프 비율: {metrics['sharpe_ratio']:.2f}")
        self.logger.info(f"  총 거래: {metrics['total_trades']} (승: {metrics['winning_trades']}, 패: {metrics['losing_trades']})")

        return result

    def _calculate_fee(self, amount: float, price: float, is_buy: bool) -> float:
        """
        수수료 계산

        Args:
            amount: 거래 수량
            price: 가격
            is_buy: 매수 여부

        Returns:
            수수료 (KRW)
        """
        total_value = amount * price
        return total_value * self.fee_rate
