#!/usr/bin/env python3
"""
Parameter Optimization - Grid search over strategy parameters to find optimal settings.
"""
import sys
import logging
import itertools
from datetime import datetime
from backtest.backtest_engine import BacktestEngine
from backtest.data_fetcher import BacktestDataFetcher
from config.config import TRADING_PAIRS

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("optimizer")
logger.setLevel(logging.INFO)


# Parameter grid
PARAM_GRID = {
    "ema_period": [20, 50, 100],
    "pullback_thresholds": [(40, 60), (45, 55)],
    "atr_sl_multiplier": [1.5, 2.0, 2.5],
}


def score_results(results: dict) -> float:
    """
    Composite score for ranking parameter sets.
    Higher is better.
    """
    if not results or results["total_trades"] < 10:
        return -999.0

    win_rate = results["win_rate"] / 100  # normalize to 0-1
    pf = min(results["profit_factor"], 5.0) / 5.0  # cap and normalize
    sharpe = min(max(results["sharpe_ratio"], 0), 3.0) / 3.0  # cap and normalize
    dd_score = 1.0 - min(results["max_drawdown"], 100) / 100

    return (win_rate * 0.3) + (pf * 0.3) + (sharpe * 0.2) + (dd_score * 0.2)


def run_optimization(instrument: str, granularity: str = "H4",
                     count: int = None, years: float = 1.0, top_n: int = 5):
    """
    Run grid search optimization for a single instrument.
    """
    # Fetch data once
    if count is None:
        candles_per_year = {"H1": 8760, "H4": 2190, "D": 365, "W": 52}
        count = int(candles_per_year.get(granularity, 365) * years)

    logger.info(f"Fetching {count} {granularity} candles for {instrument}...")
    fetcher = BacktestDataFetcher()
    data = fetcher.fetch_data(instrument, granularity, count)
    logger.info(f"Data: {len(data)} candles from {data.index[0]} to {data.index[-1]}")

    config = TRADING_PAIRS.get(instrument, {})

    # Generate all parameter combinations
    combinations = list(itertools.product(
        PARAM_GRID["ema_period"],
        PARAM_GRID["pullback_thresholds"],
        PARAM_GRID["atr_sl_multiplier"],
    ))

    logger.info(f"Testing {len(combinations)} parameter combinations...")

    results_list = []
    for i, (ema, (pb_buy, pb_sell), atr_mult) in enumerate(combinations):
        engine = BacktestEngine(
            initial_balance=10000.0,
            risk_percentage=config.get("risk_percentage", 1.0),
            reward_ratio=config.get("reward_ratio", 2.0),
            rsi_overbought=config.get("overbought", 70),
            rsi_oversold=config.get("oversold", 30),
            ema_period=ema,
            use_trend_filter=True,
            use_macd_filter=config.get("use_macd_filter", True),
            macd_fast=config.get("macd_fast", 12),
            macd_slow=config.get("macd_slow", 26),
            macd_signal=config.get("macd_signal", 9),
            atr_period=config.get("atr_period", 14),
            atr_sl_multiplier=atr_mult,
            use_divergence=config.get("use_divergence", True),
            divergence_lookback=config.get("divergence_lookback", 20),
            use_trailing_stop=config.get("use_trailing_stop", True),
            trailing_stop_atr_multiplier=config.get("trailing_stop_atr_multiplier", 2.0),
            max_hold_candles=config.get("max_hold_candles", 30),
        )

        # Monkey-patch pullback thresholds into the engine for this run
        original_generate = engine._generate_signal

        def make_patched_generate(buy_thresh, sell_thresh, orig_fn):
            def patched_generate(rsi, price, instrument, ema=None, macd_data=None, divergence="none"):
                # Temporarily override the thresholds used in signal generation
                # We need to replicate the logic with custom thresholds
                divergence_buy = divergence == "bullish"
                divergence_sell = divergence == "bearish"

                in_uptrend = True
                in_downtrend = True
                if engine.use_trend_filter and ema is not None:
                    in_uptrend = price > ema
                    in_downtrend = price < ema

                macd_ok_buy = True
                macd_ok_sell = True
                if engine.use_macd_filter and macd_data is not None:
                    macd_ok_buy = (macd_data["histogram"] > 0 or
                                   macd_data["histogram"] > macd_data["prev_histogram"])
                    macd_ok_sell = (macd_data["histogram"] < 0 or
                                    macd_data["histogram"] < macd_data["prev_histogram"])

                if engine.use_trend_filter and ema is not None:
                    if in_uptrend and rsi < buy_thresh and macd_ok_buy:
                        return "BUY"
                    if in_downtrend and rsi > sell_thresh and macd_ok_sell:
                        return "SELL"

                if not engine.use_trend_filter:
                    if rsi < engine.rsi_oversold and macd_ok_buy:
                        return "BUY"
                    if rsi > engine.rsi_overbought and macd_ok_sell:
                        return "SELL"

                if engine.use_divergence:
                    if divergence_buy and macd_ok_buy:
                        return "BUY"
                    if divergence_sell and macd_ok_sell:
                        return "SELL"

                return "WAIT"
            return patched_generate

        engine._generate_signal = make_patched_generate(pb_buy, pb_sell, original_generate)

        results = engine.run(data.copy(), instrument)

        combo_score = score_results(results)
        results_list.append({
            "ema_period": ema,
            "pullback_buy": pb_buy,
            "pullback_sell": pb_sell,
            "atr_sl_multiplier": atr_mult,
            "score": combo_score,
            "win_rate": results["win_rate"],
            "profit_factor": results["profit_factor"],
            "sharpe_ratio": results["sharpe_ratio"],
            "max_drawdown": results["max_drawdown"],
            "total_return_pct": results["total_return_pct"],
            "total_trades": results["total_trades"],
        })

        logger.info(
            f"  [{i+1}/{len(combinations)}] EMA={ema} PB=({pb_buy},{pb_sell}) ATR×{atr_mult} → "
            f"WR={results['win_rate']:.1f}% PF={results['profit_factor']:.2f} "
            f"Sharpe={results['sharpe_ratio']:.2f} Score={combo_score:.3f}"
        )

    # Sort by score and show top N
    results_list.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n{'='*90}")
    print(f"TOP {top_n} PARAMETER SETS FOR {instrument} ({granularity}, {len(data)} candles)")
    print(f"{'='*90}")
    print(f"{'Rank':<5} {'EMA':<5} {'PB Buy/Sell':<12} {'ATR×':<6} {'WinRate':<9} {'PF':<7} {'Sharpe':<8} {'MaxDD':<8} {'Return':<9} {'Trades':<7} {'Score':<7}")
    print("-" * 90)

    for rank, r in enumerate(results_list[:top_n], 1):
        print(
            f"{rank:<5} {r['ema_period']:<5} {r['pullback_buy']}/{r['pullback_sell']:<7} "
            f"{r['atr_sl_multiplier']:<6.1f} {r['win_rate']:<9.1f} {r['profit_factor']:<7.2f} "
            f"{r['sharpe_ratio']:<8.2f} {r['max_drawdown']:<8.2f} {r['total_return_pct']:<+9.2f} "
            f"{r['total_trades']:<7} {r['score']:<7.3f}"
        )

    print(f"{'='*90}\n")

    return results_list


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Optimize strategy parameters')
    parser.add_argument('instrument', nargs='?', help='Instrument to optimize (e.g., USD_CHF). Omit for all.')
    parser.add_argument('--granularity', '-g', default="H4", help='Timeframe (default: H4)')
    parser.add_argument('--years', '-y', type=float, default=1.0, help='Years of data (default: 1.0)')
    parser.add_argument('--count', '-c', type=int, help='Number of candles (overrides --years)')
    parser.add_argument('--top', '-t', type=int, default=5, help='Show top N results (default: 5)')

    args = parser.parse_args()

    instruments = [args.instrument.upper()] if args.instrument else list(TRADING_PAIRS.keys())

    for instrument in instruments:
        run_optimization(
            instrument=instrument,
            granularity=args.granularity,
            count=args.count,
            years=args.years,
            top_n=args.top,
        )
