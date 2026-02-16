# Backtesting Framework

This directory contains the backtesting framework for validating the RSI + News Sentiment trading strategy.

## Quick Reference

```bash
# Test all pairs (default: Daily)
python -m backtest.run_backtest

# Test all pairs on H4
DEFAULT_GRANULARITY=H4 python -m backtest.run_backtest

# Test specific pair
python -m backtest.run_backtest USD_CHF -g H4

# Compare timeframes
python -m backtest.run_backtest USD_CHF -g D    # Daily
python -m backtest.run_backtest USD_CHF -g H4   # 4-hour
python -m backtest.run_backtest USD_CHF -g H1   # Hourly
```

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

### All Instruments Backtest (Default: Daily)

```bash
cd app
python -m backtest.run_backtest
```

### Single Instrument Backtest

```bash
cd app
python -m backtest.run_backtest USD_CHF
```

### Test with H4 Timeframe

```bash
cd app
python -m backtest.run_backtest USD_CHF --granularity H4
# Or short form
python -m backtest.run_backtest USD_CHF -g H4
```

### All Instruments on H4

```bash
cd app
DEFAULT_GRANULARITY=H4 python -m backtest.run_backtest
```

## Configuration

### Method 1: Command-Line Arguments (Recommended for Testing)

```bash
# Test specific instrument on H4
python -m backtest.run_backtest USD_CHF --granularity H4

# Test with custom candle count
python -m backtest.run_backtest GBP_USD -g H4 -c 1000

# Available granularities: M1, M5, M15, M30, H1, H4, D, W, M
python -m backtest.run_backtest USD_CHF -g H1
```

**Command-line options:**
- `instrument` - Specific instrument to test (optional, runs all if omitted)
- `-g, --granularity` - Timeframe: D (daily), H4 (4-hour), H1 (hourly), etc.
- `-c, --count` - Number of candles to fetch (auto-calculated if omitted)

### Method 2: Environment Variables (Recommended for Live Trading)

```bash
# Set default for all pairs
export DEFAULT_GRANULARITY=H4
python -m backtest.run_backtest

# Set per-pair (mix and match!)
export USD_CHF_GRANULARITY=H4
export GBP_USD_GRANULARITY=D
python -m backtest.run_backtest

# Or create a .env file:
DEFAULT_GRANULARITY=H4
USD_CHF_GRANULARITY=H4
GBP_USD_GRANULARITY=D
```

### Method 3: Config File (Fallback)

Edit `config/config.py`:

```python
TRADING_PAIRS = {
    "USD_CHF": {
        "granularity": os.getenv("USD_CHF_GRANULARITY", "D"),
        "rsi_length": 14,
        "overbought": 70,
        "oversold": 30,
        ...
    }
}
```

**Priority order:** Command-line args → Environment variables → Config file

### Strategy Parameters

```python
initial_balance = 10000.0   # Starting balance
risk_percentage = 1.0       # Risk 1% per trade
reward_ratio = 2.0          # 2:1 reward-to-risk
rsi_overbought = 70         # RSI sell threshold
rsi_oversold = 30           # RSI buy threshold
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

## Timeframe Comparison

### Choosing the Right Timeframe

| Timeframe | Candles/Year | Trades/Year* | Best For | Notes |
|-----------|--------------|--------------|----------|-------|
| **D** (Daily) | 365 | 10-20 | Long-term, low maintenance | 1 signal per day, less noise |
| **H4** (4-hour) | 2,190 | 60-120 | Swing trading, active | 6 signals per day, balanced |
| **H1** (Hourly) | 8,760 | 240-480 | Day trading, very active | 24 signals per day, more noise |

*Approximate, depends on market conditions

### Quick Comparison Test

```bash
# Compare same pair on different timeframes
python -m backtest.run_backtest USD_CHF -g D
python -m backtest.run_backtest USD_CHF -g H4
python -m backtest.run_backtest USD_CHF -g H1

# Compare results to find optimal timeframe for each pair
```

## Advanced Usage

### Custom Parameters (Programmatic)

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

### Batch Testing Multiple Timeframes

```bash
# Test all timeframes for a pair
for tf in D H4 H1; do
  echo "Testing $tf..."
  python -m backtest.run_backtest USD_CHF -g $tf
done
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
