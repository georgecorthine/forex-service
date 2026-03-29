"""
Backtest Results Analyzer - Analyze and visualize backtest results
"""
import logging
from typing import Dict

logger = logging.getLogger("backtest")


class BacktestAnalyzer:
    """Analyzes backtest results and provides insights."""

    def __init__(self, results: Dict):
        """
        Initialize analyzer with backtest results.

        Args:
            results: Dictionary from BacktestEngine.run()
        """
        self.results = results

    def print_summary(self):
        """Print formatted summary of backtest results."""
        r = self.results

        print(f"\n{'='*80}")
        print(f"BACKTEST RESULTS SUMMARY")
        print(f"{'='*80}\n")

        # Account Performance
        print("📊 ACCOUNT PERFORMANCE")
        print(f"   Initial Balance:    ${r['initial_balance']:,.2f}")
        print(f"   Final Balance:      ${r['final_balance']:,.2f}")
        print(f"   Total Return:       ${r['total_return']:+,.2f} ({r['total_return_pct']:+.2f}%)")
        print(f"   Max Drawdown:       {r['max_drawdown']:.2f}%")
        print()

        # Trade Statistics
        print("📈 TRADE STATISTICS")
        print(f"   Total Trades:       {r['total_trades']}")
        print(f"   Winning Trades:     {r['winning_trades']} ({r['win_rate']:.1f}%)")
        print(f"   Losing Trades:      {r['losing_trades']}")
        print(f"   Average Win:        {r['avg_win']:+.2f}%")
        print(f"   Average Loss:       {r['avg_loss']:+.2f}%")
        print()

        # Risk Metrics
        print("⚠️  RISK METRICS")
        print(f"   Profit Factor:      {r['profit_factor']:.2f}")
        print(f"   Sharpe Ratio:       {r['sharpe_ratio']:.2f}")
        print()

        # Exit Reasons (if available)
        if r.get('exit_reasons'):
            print("🚪 EXIT REASONS")
            for reason, count in sorted(r['exit_reasons'].items(), key=lambda x: -x[1]):
                pct = (count / r['total_trades']) * 100
                print(f"   {reason:15s}  {count:3d} ({pct:.1f}%)")
            print()

        # Performance Assessment
        print("✅ ASSESSMENT")
        self._print_assessment(r)
        print(f"\n{'='*80}\n")

    def _print_assessment(self, results: Dict):
        """Print assessment of backtest performance."""
        assessments = []

        # Win Rate Assessment
        if results['win_rate'] >= 60:
            assessments.append("   ✅ Excellent win rate (>= 60%)")
        elif results['win_rate'] >= 50:
            assessments.append("   ✔️  Good win rate (>= 50%)")
        elif results['win_rate'] >= 40:
            assessments.append("   ⚠️  Acceptable win rate (>= 40%)")
        else:
            assessments.append("   ❌ Poor win rate (< 40%)")

        # Profit Factor Assessment
        if results['profit_factor'] >= 2.0:
            assessments.append("   ✅ Excellent profit factor (>= 2.0)")
        elif results['profit_factor'] >= 1.5:
            assessments.append("   ✔️  Good profit factor (>= 1.5)")
        elif results['profit_factor'] >= 1.0:
            assessments.append("   ⚠️  Marginal profit factor (>= 1.0)")
        else:
            assessments.append("   ❌ Losing strategy (< 1.0)")

        # Sharpe Ratio Assessment
        if results['sharpe_ratio'] >= 1.0:
            assessments.append("   ✅ Good risk-adjusted returns (Sharpe >= 1.0)")
        elif results['sharpe_ratio'] >= 0.5:
            assessments.append("   ⚠️  Moderate risk-adjusted returns (Sharpe >= 0.5)")
        else:
            assessments.append("   ❌ Poor risk-adjusted returns (Sharpe < 0.5)")

        # Max Drawdown Assessment
        if results['max_drawdown'] <= 10:
            assessments.append("   ✅ Low drawdown (<= 10%)")
        elif results['max_drawdown'] <= 20:
            assessments.append("   ⚠️  Moderate drawdown (<= 20%)")
        else:
            assessments.append("   ❌ High drawdown (> 20%)")

        # Total Return Assessment
        if results['total_return_pct'] >= 20:
            assessments.append("   ✅ Strong returns (>= 20%)")
        elif results['total_return_pct'] >= 10:
            assessments.append("   ✔️  Good returns (>= 10%)")
        elif results['total_return_pct'] > 0:
            assessments.append("   ⚠️  Modest returns (> 0%)")
        else:
            assessments.append("   ❌ Negative returns")

        for assessment in assessments:
            print(assessment)

    def get_recommendation(self) -> str:
        """Get recommendation based on backtest results."""
        r = self.results

        # Decision matrix
        if (r['win_rate'] >= 50 and
            r['profit_factor'] >= 1.5 and
            r['sharpe_ratio'] >= 0.5 and
            r['max_drawdown'] <= 20 and
            r['total_return_pct'] > 0):
            return "APPROVED FOR DEMO TRADING"
        elif (r['win_rate'] >= 40 and
              r['profit_factor'] >= 1.2 and
              r['total_return_pct'] > 0):
            return "NEEDS OPTIMIZATION"
        else:
            return "NOT READY - REQUIRES MAJOR CHANGES"

    def export_trades_to_csv(self, filename: str = "backtest_trades.csv"):
        """Export trade history to CSV in backtest/test_results/ directory."""
        import os
        import pandas as pd

        if 'trades' not in self.results or not self.results['trades']:
            logger.warning("No trades to export")
            return None

        results_dir = os.path.join(os.path.dirname(__file__), "test_results")
        os.makedirs(results_dir, exist_ok=True)
        filepath = os.path.join(results_dir, filename)

        df = pd.DataFrame(self.results['trades'])
        df.to_csv(filepath, index=False)
        logger.info(f"Exported {len(df)} trades to {filepath}")

        return filepath

    def calculate_monthly_returns(self):
        """Calculate monthly return breakdown."""
        import pandas as pd

        if 'trades' not in self.results or not self.results['trades']:
            return None

        trades_df = pd.DataFrame(self.results['trades'])
        trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
        trades_df['month'] = trades_df['entry_time'].dt.to_period('M')

        monthly_returns = trades_df.groupby('month')['profit_loss_pct'].sum()

        return monthly_returns
