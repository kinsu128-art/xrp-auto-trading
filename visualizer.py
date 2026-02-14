"""
시각화 모듈
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

# 한글 폰트 설정 (Windows)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False


class Visualizer:
    """시각화 클래스"""

    def __init__(self, figsize=(14, 10)):
        """
        시각화 초기화

        Args:
            figsize: 그래프 크기
        """
        self.figsize = figsize

    def plot_price_chart(
        self,
        candles: List[Dict],
        trades: Optional[List[Dict]] = None,
        title: str = "가격 차트",
        save_path: Optional[str] = None
    ):
        """
        가격 차트 그리기 (매수/매도 포인트 표시)

        Args:
            candles: 캔들 데이터 리스트
            trades: 거래 내역
            title: 차트 제목
            save_path: 저장 경로 (None이면 화면에 표시)
        """
        # 데이터프레임 변환
        df = pd.DataFrame(candles)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

        fig, ax = plt.subplots(figsize=self.figsize)

        # 가격 라인
        ax.plot(df['datetime'], df['close'], label='종가', linewidth=1, alpha=0.7)

        # 매수/매도 포인트 표시
        if trades:
            buy_points = []
            sell_points = []
            buy_dates = []
            sell_dates = []

            for trade in trades:
                if not trade.get("forced_close"):
                    # 매수 포인트
                    buy_points.append(trade['entry_price'])
                    buy_dates.append(trade['entry_time'])

                    # 매도 포인트
                    sell_points.append(trade['exit_price'])
                    sell_dates.append(trade['exit_time'])

            if buy_points:
                ax.scatter(buy_dates, buy_points, color='red', marker='^',
                          s=100, label='매수', zorder=5, alpha=0.8)
            if sell_points:
                ax.scatter(sell_dates, sell_points, color='blue', marker='v',
                          s=100, label='매도', zorder=5, alpha=0.8)

        # 차트 꾸미기
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('날짜', fontsize=12)
        ax.set_ylabel('가격 (KRW)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        # X축 날짜 포맷
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"📊 가격 차트 저장: {save_path}")
        else:
            plt.show()

    def plot_equity_curve(
        self,
        equity_curve: List[float],
        title: str = "수익률 곡선",
        save_path: Optional[str] = None
    ):
        """
        수익률 곡선 그리기

        Args:
            equity_curve: 자본 변화 리스트
            title: 차트 제목
            save_path: 저장 경로 (None이면 화면에 표시)
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        # 수익률 곡선
        x = range(len(equity_curve))
        ax.plot(x, equity_curve, label='자본', linewidth=2, color='green')

        # 초기 자본 기준선
        if equity_curve:
            ax.axhline(y=equity_curve[0], color='red', linestyle='--',
                       label='초기 자본', alpha=0.5)

        # 차트 꾸미기
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('거래 순서', fontsize=12)
        ax.set_ylabel('자본 (KRW)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"📊 수익률 곡선 저장: {save_path}")
        else:
            plt.show()

    def plot_trade_distribution(self, trades: List[Dict], save_path: Optional[str] = None):
        """
        거래 분포 그래프

        Args:
            trades: 거래 내역
            save_path: 저장 경로 (None이면 화면에 표시)
        """
        if not trades:
            print("거래 내역 없음")
            return

        # 수익/손실 분리
        profits = [t['profit'] for t in trades if t['profit'] > 0]
        losses = [t['profit'] for t in trades if t['profit'] < 0]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize)

        # 수익 분포
        if profits:
            ax1.hist(profits, bins=20, color='green', alpha=0.7, edgecolor='black')
            ax1.axvline(x=sum(profits)/len(profits), color='red',
                       linestyle='--', label=f'평균: {sum(profits)/len(profits):.0f} KRW')
            ax1.set_title('수익 분포', fontsize=14, fontweight='bold')
            ax1.set_xlabel('수익 (KRW)', fontsize=12)
            ax1.set_ylabel('빈도', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)

        # 손실 분포
        if losses:
            ax2.hist(losses, bins=20, color='red', alpha=0.7, edgecolor='black')
            ax2.axvline(x=sum(losses)/len(losses), color='red',
                       linestyle='--', label=f'평균: {sum(losses)/len(losses):.0f} KRW')
            ax2.set_title('손실 분포', fontsize=14, fontweight='bold')
            ax2.set_xlabel('손실 (KRW)', fontsize=12)
            ax2.set_ylabel('빈도', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"📊 거래 분포 저장: {save_path}")
        else:
            plt.show()

    def plot_drawdown(self, equity_curve: List[float], save_path: Optional[str] = None):
        """
        손실률(Drawdown) 차트

        Args:
            equity_curve: 자본 변화 리스트
            save_path: 저장 경로 (None이면 화면에 표시)
        """
        if not equity_curve:
            print("자본 곡선 없음")
            return

        # 손실률 계산
        peak = equity_curve[0]
        drawdowns = []

        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            drawdowns.append(drawdown)

        fig, ax = plt.subplots(figsize=self.figsize)

        # 손실률 차트
        x = range(len(drawdowns))
        ax.fill_between(x, drawdowns, 0, alpha=0.3, color='red')
        ax.plot(x, drawdowns, linewidth=2, color='red')

        # 최대 손실률 표시
        max_drawdown = max(drawdowns)
        ax.axhline(y=max_drawdown, color='darkred', linestyle='--',
                   label=f'최대 손실률: {max_drawdown:.2f}%')

        # 차트 꾸미기
        ax.set_title('손실률 (Drawdown)', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('거래 순서', fontsize=12)
        ax.set_ylabel('손실률 (%)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"📊 손실률 차트 저장: {save_path}")
        else:
            plt.show()

    def create_backtest_report(
        self,
        candles: List[Dict],
        trades: List[Dict],
        metrics: Dict,
        output_path: str = "reports/backtest_report.html"
    ):
        """
        백테스트 리포트 생성 (HTML)

        Args:
            candles: 캔들 데이터
            trades: 거래 내역
            metrics: 성과 지표
            output_path: 출력 경로
        """
        # HTML 템플릿
        html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>백테스트 리포트</title>
    <style>
        body {{
            font-family: 'Malgun Gothic', Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric {{
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 5px;
            border-left: 4px solid #4CAF50;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .positive {{
            color: #4CAF50;
        }}
        .negative {{
            color: #f44336;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .chart-placeholder {{
            background-color: #f9f9f9;
            border: 2px dashed #ddd;
            padding: 40px;
            text-align: center;
            margin: 20px 0;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 백테스트 리포트</h1>
        <p><strong>생성 시간:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2>📈 성과 지표</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">총 수익률</div>
                <div class="metric-value { 'positive' if metrics['total_return_percent'] > 0 else 'negative' }">
                    {metrics['total_return_percent']:.2f}%
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">연간 수익률</div>
                <div class="metric-value { 'positive' if metrics['annualized_return'] > 0 else 'negative' }">
                    {metrics['annualized_return']:.2f}%
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">승률</div>
                <div class="metric-value { 'positive' if metrics['win_rate'] >= 50 else 'negative' }">
                    {metrics['win_rate']:.2f}%
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">총 거래 횟수</div>
                <div class="metric-value">
                    {metrics['total_trades']}
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">승리 / 패배</div>
                <div class="metric-value">
                    {metrics['winning_trades']} / {metrics['losing_trades']}
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">평균 수익</div>
                <div class="metric-value positive">
                    {metrics['avg_profit']:.0f} KRW
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">평균 손실</div>
                <div class="metric-value negative">
                    {metrics['avg_loss']:.0f} KRW
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">손익비</div>
                <div class="metric-value { 'positive' if metrics['profit_factor'] > 1 else 'negative' }">
                    {metrics['profit_factor']:.2f}
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">최대 손실률</div>
                <div class="metric-value negative">
                    {metrics['max_drawdown_percent']:.2f}%
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">샤프 비율</div>
                <div class="metric-value { 'positive' if metrics['sharpe_ratio'] > 1 else 'negative' }">
                    {metrics['sharpe_ratio']:.2f}
                </div>
            </div>
        </div>

        <h2>📋 거래 내역</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>매수 시간</th>
                    <th>매수 가격</th>
                    <th>매도 시간</th>
                    <th>매도 가격</th>
                    <th>수익</th>
                    <th>수익률</th>
                    <th>보유 시간</th>
                </tr>
            </thead>
            <tbody>
"""

        # 거래 내역 테이블 추가
        for i, trade in enumerate(trades, 1):
            profit_class = 'positive' if trade['profit'] > 0 else 'negative'
            forced_close = ' (강제 청산)' if trade.get('forced_close') else ''

            html_template += f"""
                <tr>
                    <td>{i}</td>
                    <td>{trade['entry_time'].strftime('%Y-%m-%d %H:%M')}</td>
                    <td>{trade['entry_price']:.2f}</td>
                    <td>{trade['exit_time'].strftime('%Y-%m-%d %H:%M')}</td>
                    <td>{trade['exit_price']:.2f}</td>
                    <td class="{profit_class}">{trade['profit']:.0f} KRW</td>
                    <td class="{profit_class}">{trade['profit_percent']:.2f}%</td>
                    <td>{trade['duration_hours']:.1f}시간{forced_close}</td>
                </tr>
"""

        html_template += f"""
            </tbody>
        </table>

        <div class="chart-placeholder">
            <p>📊 차트는 별도의 PNG 파일로 저장됩니다.</p>
            <p>price_chart.png, equity_curve.png, drawdown.png</p>
        </div>

    </div>
</body>
</html>
"""

        # HTML 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_template)

        print(f"📄 백테스트 리포트 생성: {output_path}")

    def plot_all_charts(
        self,
        candles: List[Dict],
        trades: List[Dict],
        equity_curve: List[float],
        output_dir: str = "reports"
    ):
        """
        모든 차트 생성

        Args:
            candles: 캔들 데이터
            trades: 거래 내역
            equity_curve: 자본 변화 리스트
            output_dir: 출력 디렉토리
        """
        import os
        os.makedirs(output_dir, exist_ok=True)

        # 가격 차트
        self.plot_price_chart(
            candles,
            trades,
            title="가격 차트 (매수/매도 포인트)",
            save_path=f"{output_dir}/price_chart.png"
        )

        # 수익률 곡선
        self.plot_equity_curve(
            equity_curve,
            title="수익률 곡선",
            save_path=f"{output_dir}/equity_curve.png"
        )

        # 손실률 차트
        self.plot_drawdown(
            equity_curve,
            save_path=f"{output_dir}/drawdown.png"
        )

        # 거래 분포
        self.plot_trade_distribution(
            trades,
            save_path=f"{output_dir}/trade_distribution.png"
        )

        print(f"✅ 모든 차트 생성 완료: {output_dir}")
