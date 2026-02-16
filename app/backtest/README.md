# Backtesting Framework

This directory contains the backtesting framework for validating the RSI + News Sentiment trading strategy.

## Overview

The backtesting engine simulates the strategy on historical data to evaluate its performance before risking real capital.

## Components

### 1. `backtest_engine.py`
Core backtesting engine that:
- Simulates trades based on RSI signals
- Manages risk with stop-loss and take-profit
- Tracks balance and calculates statistics
- Generates comprehensive performance metrics

### 2. `data_fetcher.py`
Fetches historical data from OANDA API:
- Supports multiple timeframes (D, H4, H1, M15, etc.)
- Can fetch up to 5000 candles
- Save/load data to CSV for faster re-runs

### 3. `results_analyzer.py`
Analyzes and presents backtest results:
- Formatted summary output
- Performance assessment
- Trade recommendations
- Export capabilities

### 4. `run_backtest.py`
Main runner script for executing backtests

## Quick Start

### Single Instrument Backtest

```bash
cd app
python -m backtest.run_backtest EUR_USD
```

### All Instruments Backtest

```bash
cd app
python -m backtest.run_backtest
```

## Configuration

Edit parameters in `run_backtest.py`:

```python
initial_balance = 10000.0   # Starting balance
risk_percentage = 1.0       # Risk 1% per trade
reward_ratio = 2.0          # 2:1 reward-to-risk
granularity = "D"           # Daily candles
count = 2000                # Number of candles to test
```

## Understanding Results

### Key Metrics

- **Win Rate**: Percentage of profitable trades (Target: ≥ 50%)
- **Profit Factor**: Gross profit / Gross loss (Target: ≥ 1.5)
- **Sharpe Ratio**: Risk-adjusted returns (Target: ≥ 0.5)
- **Max Drawdown**: Largest peak-to-trough decline (Target: ≤ 20%)

### Assessment Criteria

**APPROVED FOR DEMO TRADING:**
- Win Rate ≥ 50%
- Profit Factor ≥ 1.5
- Sharpe Ratio ≥ 0.5
- Max Drawdown ≤ 20%
- Positive returns

**NEEDS OPTIMIZATION:**
- Win Rate ≥ 40%
- Profit Factor ≥ 1.2
- Positive returns

**NOT READY:**
- Below optimization thresholds
- Requires strategy adjustments

## Example Output

```
================================================================================
BACKTEST RESULTS SUMMARY
================================================================================

📊 ACCOUNT PERFORMANCE
   Initial Balance:    $10,000.00
   Final Balance:      $12,450.00
   Total Return:       +$2,450.00 (+24.50%)
   Max Drawdown:       12.34%

📈 TRADE STATISTICS
   Total Trades:       85
   Winning Trades:     48 (56.5%)
   Losing Trades:      37
   Average Win:        +3.25%
   Average Loss:       -1.50%

⚠️  RISK METRICS
   Profit Factor:      2.17
   Sharpe Ratio:       1.25

✅ ASSESSMENT
   ✅ Excellent win rate (>= 60%)
   ✅ Excellent profit factor (>= 2.0)
   ✅ Good risk-adjusted returns (Sharpe >= 1.0)
   ✅ Low drawdown (<= 10%)
   ✅ Strong returns (>= 20%)

================================================================================
```

## Advanced Usage

### Custom Parameters

```python
from backtest.backtest_engine import BacktestEngine
from backtest.data_fetcher import BacktestDataFetcher

# Fetch data
fetcher = BacktestDataFetcher()
data = fetcher.fetch_data("EUR_USD", granularity="H4", count=3000)

# Run custom backtest
engine = BacktestEngine(
    initial_balance=25000.0,
    risk_percentage=2.0,
    reward_ratio=3.0,
    rsi_overbought=75,
    rsi_oversold=25
)

results = engine.run(data, "EUR_USD")
```

### Export Trades

```python
from backtest.results_analyzer import BacktestAnalyzer

analyzer = BacktestAnalyzer(results)
analyzer.export_trades_to_csv("my_trades.csv")
```

### Save Data for Later

```python
# Save data to CSV
fetcher.save_to_csv(data, "EUR_USD", directory="backtest/data")

# Load data later
data = fetcher.load_from_csv("backtest/data/EUR_USD_20260216.csv")
```

## Important Notes

⚠️ **Limitations:**
- Backtests use **RSI only** (historical news data not available)
- Actual strategy includes news sentiment confirmation
- Past performance doesn't guarantee future results
- Assumes no slippage or commissions

⚠️ **Best Practices:**
- Test on at least 2 years of data (500+ daily candles)
- Run multiple instruments to ensure consistency
- Consider different market conditions (trends, ranges, volatility)
- Start demo trading with minimum position sizes (0.01 lots)

## Troubleshooting

### "OANDA client not available"
- Ensure `OANDA_API_TOKEN` and `OANDA_ACCOUNT_ID` are set
- Check environment variables are exported

### "No data returned"
- Verify instrument name format (use underscore: EUR_USD not EURUSD)
- Check OANDA account has access to the instrument
- Reduce count if requesting too much data

### Import errors
- Run from `app/` directory: `cd app && python -m backtest.run_backtest`
- Ensure all dependencies are installed: `pip install -r requirements.txt`

## Next Steps

After successful backtesting:

1. ✅ **Validate Results**: Win rate ≥ 50%, Profit Factor ≥ 1.5
2. ✅ **Test Multiple Timeframes**: Daily, 4H, 1H
3. ✅ **Test Multiple Instruments**: All configured pairs
4. ✅ **Analyze Drawdowns**: Ensure acceptable risk
5. ➡️ **Demo Trading**: Start with 0.01 lots, monitor for 1 week
6. ➡️ **Paper Trading**: Track alongside real market for 1 month
7. ➡️ **Live Trading**: Only after consistent demo performance
