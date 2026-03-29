#!/usr/bin/env python3
"""
Backtest Runner - Execute backtests and analyze results
"""
import sys
import os
import logging
import json
from datetime import datetime
from backtest.backtest_engine import BacktestEngine
from backtest.data_fetcher import BacktestDataFetcher
from backtest.results_analyzer import BacktestAnalyzer
from config.config import TRADING_PAIRS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("backtest")


def run_single_backtest(instrument: str,
                       initial_balance: float = 10000.0,
                       risk_percentage: float = 1.0,
                       reward_ratio: float = 2.0,
                       granularity: str = "D",
                       count: int = None,
                       years: float = 1.0):
    """
    Run backtest for a single instrument.
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"BACKTESTING: {instrument}")
    logger.info(f"{'='*80}")

    # Get strategy settings from config
    config = TRADING_PAIRS.get(instrument, {})
    # Allow config to override granularity, but respect function parameter if provided
    if granularity == "D" and "granularity" in config:
        granularity = config.get("granularity", "D")

    # Auto-calculate count based on granularity and years
    if count is None:
        candles_per_year = {
            "H1": 8760,   # ~24 candles/day * 365
            "H4": 2190,   # ~6 candles/day * 365
            "D": 365,
            "W": 52,
        }
        base = candles_per_year.get(granularity, 365)
        count = int(base * years)

    # Fetch data
    logger.info("Step 1: Fetching historical data...")
    fetcher = BacktestDataFetcher()
    try:
        data = fetcher.fetch_data(instrument, granularity, count)
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return None

    # Run backtest with all config parameters
    logger.info("Step 2: Running backtest...")
    engine = BacktestEngine(
        initial_balance=initial_balance,
        risk_percentage=risk_percentage,
        reward_ratio=reward_ratio,
        rsi_overbought=config.get("overbought", 70),
        rsi_oversold=config.get("oversold", 30),
        # Enhanced indicators from config
        ema_period=config.get("ema_period", 50),
        use_trend_filter=config.get("use_trend_filter", True),
        use_macd_filter=config.get("use_macd_filter", True),
        macd_fast=config.get("macd_fast", 12),
        macd_slow=config.get("macd_slow", 26),
        macd_signal=config.get("macd_signal", 9),
        atr_period=config.get("atr_period", 14),
        atr_sl_multiplier=config.get("atr_sl_multiplier", 1.5),
        use_divergence=config.get("use_divergence", True),
        divergence_lookback=config.get("divergence_lookback", 20),
        use_trailing_stop=config.get("use_trailing_stop", True),
        trailing_stop_atr_multiplier=config.get("trailing_stop_atr_multiplier", 2.0),
        max_hold_candles=config.get("max_hold_candles", 20),
        # Regime detection
        use_regime_filter=config.get("use_regime_filter", True),
        adx_period=config.get("adx_period", 14),
        adx_trending_threshold=config.get("adx_trending_threshold", 25.0),
        adx_ranging_threshold=config.get("adx_ranging_threshold", 20.0),
        atr_volatility_multiplier=config.get("atr_volatility_multiplier", 1.5),
        atr_volatility_ma_length=config.get("atr_volatility_ma_length", 50),
        # Multi-timeframe confirmation
        use_mtf_confirmation=config.get("use_mtf_confirmation", True),
        mtf_ema_period=config.get("mtf_ema_period", 50),
    )

    results = engine.run(data, instrument)

    # Analyze results
    logger.info("Step 3: Analyzing results...")
    analyzer = BacktestAnalyzer(results)
    analyzer.print_summary()

    return results


def run_multi_instrument_backtest(instruments: list = None,
                                  initial_balance: float = 10000.0,
                                  risk_percentage: float = 1.0,
                                  reward_ratio: float = 2.0,
                                  granularity: str = "D",
                                  count: int = None,
                                  years: float = 1.0):
    """
    Run backtest for multiple instruments and aggregate results.
    """
    if instruments is None:
        instruments = list(TRADING_PAIRS.keys())

    logger.info(f"\n{'='*80}")
    logger.info(f"MULTI-INSTRUMENT BACKTEST: {', '.join(instruments)}")
    logger.info(f"{'='*80}\n")

    all_results = {}

    for instrument in instruments:
        results = run_single_backtest(
            instrument=instrument,
            initial_balance=initial_balance,
            risk_percentage=risk_percentage,
            reward_ratio=reward_ratio,
            granularity=granularity,
            count=count,
            years=years,
        )

        if results:
            all_results[instrument] = results

    # Print aggregate summary
    logger.info(f"\n{'='*80}")
    logger.info("AGGREGATE RESULTS")
    logger.info(f"{'='*80}")

    total_trades = sum(r['total_trades'] for r in all_results.values())
    total_wins = sum(r['winning_trades'] for r in all_results.values())
    avg_win_rate = sum(r['win_rate'] for r in all_results.values()) / len(all_results) if all_results else 0
    avg_return = sum(r['total_return_pct'] for r in all_results.values()) / len(all_results) if all_results else 0

    logger.info(f"Instruments Tested: {len(all_results)}")
    logger.info(f"Total Trades: {total_trades}")
    logger.info(f"Total Wins: {total_wins}")
    logger.info(f"Average Win Rate: {avg_win_rate:.2f}%")
    logger.info(f"Average Return: {avg_return:+.2f}%")
    logger.info(f"{'='*80}\n")

    return all_results


def save_results(results: dict, filename: str = None):
    """Save backtest results to backtest/test_results/ directory."""
    results_dir = os.path.join(os.path.dirname(__file__), "test_results")
    os.makedirs(results_dir, exist_ok=True)

    if filename is None:
        filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    filepath = os.path.join(results_dir, filename)

    # Convert results to JSON-serializable format
    json_results = {}
    for instrument, data in results.items():
        json_data = data.copy()
        # Remove trades list for cleaner output (can be very long)
        if 'trades' in json_data:
            json_data['num_trades'] = len(json_data['trades'])
            del json_data['trades']
        json_results[instrument] = json_data

    with open(filepath, 'w') as f:
        json.dump(json_results, f, indent=2)

    logger.info(f"Results saved to {filepath}")
    return filepath


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run forex backtest')
    parser.add_argument('instrument', nargs='?', help='Specific instrument to test (e.g., USD_CHF)')
    parser.add_argument('--granularity', '-g', help='Timeframe: D, H4, H1, etc. (overrides config)')
    parser.add_argument('--count', '-c', type=int, help='Number of candles to fetch (overrides --years)')
    parser.add_argument('--years', '-y', type=float, default=1.0, help='Years of data to backtest (default: 1.0)')

    args = parser.parse_args()

    if args.instrument:
        # Run for specific instrument
        instrument = args.instrument.upper()
        single_result = run_single_backtest(
            instrument,
            granularity=args.granularity if args.granularity else "D",
            count=args.count,
            years=args.years,
        )
        # Wrap single result in a dict for save_results
        results = {instrument: single_result} if single_result else None
    else:
        # Run for all configured instruments
        results = run_multi_instrument_backtest(
            granularity=args.granularity if args.granularity else "D",
            count=args.count,
            years=args.years,
        )

    if results:
        save_results(results)
