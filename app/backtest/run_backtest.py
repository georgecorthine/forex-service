#!/usr/bin/env python3
"""
Backtest Runner - Execute backtests and analyze results
"""
import sys
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
                       count: int = 2000):
    """
    Run backtest for a single instrument.

    Args:
        instrument: Trading pair (e.g., "EUR_USD")
        initial_balance: Starting balance
        risk_percentage: Risk per trade (%)
        reward_ratio: Reward-to-risk ratio
        granularity: Data granularity
        count: Number of candles

    Returns:
        Dictionary with backtest results
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"BACKTESTING: {instrument}")
    logger.info(f"{'='*80}")

    # Fetch data
    logger.info("Step 1: Fetching historical data...")
    fetcher = BacktestDataFetcher()
    try:
        data = fetcher.fetch_data(instrument, granularity, count)
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return None

    # Get RSI settings from config
    config = TRADING_PAIRS.get(instrument, {})
    rsi_overbought = config.get("overbought", 70)
    rsi_oversold = config.get("oversold", 30)

    # Run backtest
    logger.info("Step 2: Running backtest...")
    engine = BacktestEngine(
        initial_balance=initial_balance,
        risk_percentage=risk_percentage,
        reward_ratio=reward_ratio,
        rsi_overbought=rsi_overbought,
        rsi_oversold=rsi_oversold
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
                                  reward_ratio: float = 2.0):
    """
    Run backtest for multiple instruments and aggregate results.

    Args:
        instruments: List of trading pairs (if None, uses all from config)
        initial_balance: Starting balance
        risk_percentage: Risk per trade (%)
        reward_ratio: Reward-to-risk ratio

    Returns:
        Dictionary with aggregated results
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
            reward_ratio=reward_ratio
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
    """Save backtest results to JSON file."""
    if filename is None:
        filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Convert results to JSON-serializable format
    json_results = {}
    for instrument, data in results.items():
        json_data = data.copy()
        # Remove trades list for cleaner output (can be very long)
        if 'trades' in json_data:
            json_data['num_trades'] = len(json_data['trades'])
            del json_data['trades']
        json_results[instrument] = json_data

    with open(filename, 'w') as f:
        json.dump(json_results, f, indent=2)

    logger.info(f"Results saved to {filename}")
    return filename


if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1:
        # Run for specific instrument
        instrument = sys.argv[1].upper()
        results = run_single_backtest(instrument)
    else:
        # Run for all configured instruments
        results = run_multi_instrument_backtest()

    if results:
        save_results(results)
