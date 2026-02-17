"""
Backtesting Engine for Enhanced RSI + EMA + MACD + ATR Strategy
"""
import pandas as pd
import logging
from typing import List, Dict
from datetime import datetime
from utils.indicators import (
    calculate_rsi, calculate_rsi_series, calculate_ema,
    calculate_atr, calculate_atr_series, calculate_macd,
    detect_rsi_divergence, calculate_adx, detect_regime,
)
from utils.risk_management import calculate_trade_levels

logger = logging.getLogger("backtest")


class Trade:
    """Represents a single trade in the backtest."""
    def __init__(self, instrument: str, trade_type: str, entry_price: float,
                 stop_loss: float, take_profit: float, entry_time: datetime,
                 position_size: float = 1.0, atr_at_entry: float = 0.0,
                 entry_bar_index: int = 0):
        self.instrument = instrument
        self.type = trade_type
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.entry_time = entry_time
        self.exit_time = None
        self.exit_price = None
        self.profit_loss = 0.0
        self.profit_loss_pct = 0.0
        self.position_size = position_size
        self.status = "OPEN"  # OPEN, WIN, LOSS
        self.exit_reason = ""  # SL, TP, TRAILING, TIME, CLOSE
        self.atr_at_entry = atr_at_entry
        self.entry_bar_index = entry_bar_index
        self.trailing_stop = stop_loss  # initialized to SL, updated as trade progresses

    def close(self, exit_price: float, exit_time: datetime, reason: str = ""):
        """Close the trade and calculate profit/loss."""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = reason

        if self.type == "BUY":
            self.profit_loss_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:  # SELL
            self.profit_loss_pct = ((self.entry_price - exit_price) / self.entry_price) * 100

        self.profit_loss = self.profit_loss_pct * self.position_size
        self.status = "WIN" if self.profit_loss > 0 else "LOSS"

    def update_trailing_stop(self, current_price: float, atr: float,
                             trailing_atr_multiplier: float = 2.0):
        """
        Update trailing stop based on current price and ATR.
        Only activates after price has moved at least 1:1 R:R in our favor
        (i.e., past breakeven by the risk distance).
        """
        if atr is None or atr <= 0:
            return

        # Use ATR at entry for consistent trailing distance
        trail_distance = self.atr_at_entry * trailing_atr_multiplier
        if trail_distance <= 0:
            return

        # Calculate how far price has moved in our favor
        sl_distance = abs(self.entry_price - self.stop_loss)

        if self.type == "BUY":
            # Only trail once price has moved 1:1 past entry (breakeven + risk distance)
            if current_price < self.entry_price + sl_distance:
                return
            new_trail = current_price - trail_distance
            # Only move trailing stop up, never down
            if new_trail > self.trailing_stop:
                self.trailing_stop = new_trail
        else:  # SELL
            if current_price > self.entry_price - sl_distance:
                return
            new_trail = current_price + trail_distance
            # Only move trailing stop down, never up
            if new_trail < self.trailing_stop:
                self.trailing_stop = new_trail

    def check_exit(self, current_high: float, current_low: float,
                   current_close: float, current_time: datetime,
                   current_bar_index: int = 0,
                   use_trailing_stop: bool = False,
                   max_hold_candles: int = 0) -> bool:
        """Check if stop loss, take profit, trailing stop, or time exit was hit."""

        # Check time-based exit first
        if max_hold_candles > 0:
            bars_held = current_bar_index - self.entry_bar_index
            if bars_held >= max_hold_candles:
                self.close(current_close, current_time, reason="TIME")
                return True

        if self.type == "BUY":
            # Check trailing stop (if enabled and moved above initial SL)
            effective_sl = self.trailing_stop if use_trailing_stop else self.stop_loss
            if current_low <= effective_sl:
                reason = "TRAILING" if (use_trailing_stop and self.trailing_stop > self.stop_loss) else "SL"
                self.close(effective_sl, current_time, reason=reason)
                return True
            elif current_high >= self.take_profit:
                self.close(self.take_profit, current_time, reason="TP")
                return True
        else:  # SELL
            effective_sl = self.trailing_stop if use_trailing_stop else self.stop_loss
            if current_high >= effective_sl:
                reason = "TRAILING" if (use_trailing_stop and self.trailing_stop < self.stop_loss) else "SL"
                self.close(effective_sl, current_time, reason=reason)
                return True
            elif current_low <= self.take_profit:
                self.close(self.take_profit, current_time, reason="TP")
                return True
        return False

    def to_dict(self) -> dict:
        """Convert trade to dictionary for analysis."""
        return {
            'instrument': self.instrument,
            'type': self.type,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry_time': self.entry_time,
            'exit_time': self.exit_time,
            'profit_loss_pct': self.profit_loss_pct,
            'profit_loss': self.profit_loss,
            'status': self.status,
            'exit_reason': self.exit_reason,
            'duration_hours': (self.exit_time - self.entry_time).total_seconds() / 3600 if self.exit_time else None
        }


class BacktestEngine:
    """Engine for backtesting the enhanced multi-indicator strategy."""

    def __init__(self,
                 initial_balance: float = 10000.0,
                 risk_percentage: float = 1.0,
                 reward_ratio: float = 2.0,
                 rsi_period: int = 14,
                 rsi_overbought: int = 70,
                 rsi_oversold: int = 30,
                 max_concurrent_trades: int = 1,
                 # Trend filter
                 ema_period: int = 50,
                 use_trend_filter: bool = True,
                 # MACD
                 use_macd_filter: bool = True,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 # ATR stops
                 atr_period: int = 14,
                 atr_sl_multiplier: float = 1.5,
                 # RSI divergence
                 use_divergence: bool = True,
                 divergence_lookback: int = 20,
                 # Trailing stop
                 use_trailing_stop: bool = True,
                 trailing_stop_atr_multiplier: float = 2.0,
                 # Time-based exit
                 max_hold_candles: int = 20,
                 # Regime detection
                 use_regime_filter: bool = True,
                 adx_period: int = 14,
                 adx_trending_threshold: float = 25.0,
                 adx_ranging_threshold: float = 20.0,
                 atr_volatility_multiplier: float = 1.5,
                 atr_volatility_ma_length: int = 50,
                 # Multi-timeframe confirmation
                 use_mtf_confirmation: bool = True,
                 mtf_ema_period: int = 50,
                 # Legacy compatibility
                 ma_period: int = 200,
                 ):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.risk_percentage = risk_percentage
        self.reward_ratio = reward_ratio
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.max_concurrent_trades = max_concurrent_trades

        # Enhanced indicators
        self.ema_period = ema_period
        self.use_trend_filter = use_trend_filter
        self.use_macd_filter = use_macd_filter
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.atr_period = atr_period
        self.atr_sl_multiplier = atr_sl_multiplier
        self.use_divergence = use_divergence
        self.divergence_lookback = divergence_lookback
        self.use_trailing_stop = use_trailing_stop
        self.trailing_stop_atr_multiplier = trailing_stop_atr_multiplier
        self.max_hold_candles = max_hold_candles

        # Regime detection
        self.use_regime_filter = use_regime_filter
        self.adx_period = adx_period
        self.adx_trending_threshold = adx_trending_threshold
        self.adx_ranging_threshold = adx_ranging_threshold
        self.atr_volatility_multiplier = atr_volatility_multiplier
        self.atr_volatility_ma_length = atr_volatility_ma_length

        # Multi-timeframe confirmation
        self.use_mtf_confirmation = use_mtf_confirmation
        self.mtf_ema_period = mtf_ema_period

        self.trades: List[Trade] = []
        self.open_trades: List[Trade] = []

    def run(self, data: pd.DataFrame, instrument: str = "EUR_USD") -> Dict:
        """
        Run backtest on historical data.
        """
        logger.info(f"Starting backtest for {instrument} with {len(data)} candles")
        logger.info(
            f"Strategy: RSI({self.rsi_period}) OB={self.rsi_overbought}/OS={self.rsi_oversold} | "
            f"EMA({self.ema_period})={'ON' if self.use_trend_filter else 'OFF'} | "
            f"MACD({self.macd_fast},{self.macd_slow},{self.macd_signal})={'ON' if self.use_macd_filter else 'OFF'} | "
            f"ATR({self.atr_period}) SL×{self.atr_sl_multiplier} | "
            f"Trailing={'ON' if self.use_trailing_stop else 'OFF'} | "
            f"MaxHold={self.max_hold_candles} | "
            f"Divergence={'ON' if self.use_divergence else 'OFF'} | "
            f"Regime={'ON' if self.use_regime_filter else 'OFF'} ADX({self.adx_period}) | "
            f"MTF={'ON' if self.use_mtf_confirmation else 'OFF'}"
        )

        # Reset state
        self.balance = self.initial_balance
        self.trades = []
        self.open_trades = []

        data = data.copy()

        # Minimum bars needed before we can generate signals
        min_bars = max(self.rsi_period + 1, self.ema_period + 1,
                       self.macd_slow + self.macd_signal + 1,
                       self.atr_period + 1,
                       2 * self.adx_period + 1 if self.use_regime_filter else 0)

        for i in range(min_bars, len(data)):
            current_time = data.index[i]
            current_row = data.iloc[i]
            history = data.iloc[:i+1]

            # Calculate all indicators
            rsi = calculate_rsi(history, length=self.rsi_period)
            atr = calculate_atr(history, length=self.atr_period)
            ema = calculate_ema(history, length=self.ema_period) if self.use_trend_filter else None

            macd_data = None
            if self.use_macd_filter:
                macd_data = calculate_macd(
                    history, fast=self.macd_fast,
                    slow=self.macd_slow, signal=self.macd_signal,
                )

            divergence = "none"
            if self.use_divergence:
                rsi_series = calculate_rsi_series(history, length=self.rsi_period)
                divergence = detect_rsi_divergence(
                    history, rsi_series, lookback=self.divergence_lookback,
                )

            # Regime detection
            regime = "neutral"
            if self.use_regime_filter:
                adx_data = calculate_adx(history, length=self.adx_period)
                atr_series = calculate_atr_series(history, length=self.atr_period)
                if adx_data is not None and len(atr_series.dropna()) > 0:
                    regime = detect_regime(
                        adx_value=adx_data["adx"],
                        atr_series=atr_series,
                        adx_trending_threshold=self.adx_trending_threshold,
                        adx_ranging_threshold=self.adx_ranging_threshold,
                        atr_volatility_multiplier=self.atr_volatility_multiplier,
                        atr_ma_length=self.atr_volatility_ma_length,
                    )

            # Multi-timeframe confirmation
            daily_trend = "neutral"
            if self.use_mtf_confirmation:
                daily_trend = self._get_daily_trend(data, i)

            # Update trailing stops and check exits for open trades
            for trade in self.open_trades[:]:
                if self.use_trailing_stop and atr is not None:
                    trade.update_trailing_stop(
                        current_row['Close'], atr,
                        self.trailing_stop_atr_multiplier,
                    )

                if trade.check_exit(
                    current_row['High'], current_row['Low'], current_row['Close'],
                    current_time, current_bar_index=i,
                    use_trailing_stop=self.use_trailing_stop,
                    max_hold_candles=self.max_hold_candles,
                ):
                    self.open_trades.remove(trade)
                    self.balance += (trade.profit_loss_pct / 100) * self.balance

            # Only enter new trades if we have room
            if len(self.open_trades) >= self.max_concurrent_trades:
                continue

            # Generate signal with all filters
            signal = self._generate_signal(
                rsi=rsi,
                price=current_row['Close'],
                instrument=instrument,
                ema=ema,
                macd_data=macd_data,
                divergence=divergence,
                regime=regime,
                daily_trend=daily_trend,
            )

            if signal and signal != "WAIT":
                trade = self._enter_trade(
                    instrument=instrument,
                    trade_type=signal,
                    entry_price=current_row['Close'],
                    entry_time=current_time,
                    atr=atr,
                    bar_index=i,
                )
                if trade:
                    self.trades.append(trade)
                    self.open_trades.append(trade)

        # Close any remaining open trades at the last price
        if self.open_trades:
            last_price = data.iloc[-1]['Close']
            last_time = data.index[-1]
            for trade in self.open_trades:
                trade.close(last_price, last_time, reason="CLOSE")

        # Calculate data span for annualized metrics
        data_span_days = (data.index[-1] - data.index[0]).total_seconds() / 86400
        results = self._calculate_statistics(data_span_days=data_span_days)
        logger.info(f"Backtest complete: {len(self.trades)} trades, Final balance: ${self.balance:.2f}")

        return results

    def _generate_signal(self, rsi: float, price: float, instrument: str,
                         ema: float = None, macd_data: dict = None,
                         divergence: str = "none",
                         regime: str = "neutral",
                         daily_trend: str = "neutral") -> str:
        """
        Generate trading signal using multi-indicator confluence.

        Signal modes:
        1. Trend pullback: RSI pulls back in a trending market (EMA filter)
        2. RSI extreme: without trend filter (fallback)
        3. Divergence: RSI divergence detected

        Filters:
        - Regime: high_volatility blocks all; ranging blocks Mode 1
        - MTF: daily trend must not oppose the signal direction
        """
        # High volatility: skip all trading
        if regime == "high_volatility":
            return "WAIT"

        divergence_buy = divergence == "bullish"
        divergence_sell = divergence == "bearish"

        in_uptrend = True
        in_downtrend = True
        if self.use_trend_filter and ema is not None:
            in_uptrend = price > ema
            in_downtrend = price < ema

        # MACD momentum confirmation
        macd_ok_buy = True
        macd_ok_sell = True
        if self.use_macd_filter and macd_data is not None:
            macd_ok_buy = (macd_data["histogram"] > 0 or
                           macd_data["histogram"] > macd_data["prev_histogram"])
            macd_ok_sell = (macd_data["histogram"] < 0 or
                            macd_data["histogram"] < macd_data["prev_histogram"])

        PULLBACK_BUY_THRESHOLD = 45
        PULLBACK_SELL_THRESHOLD = 55

        # Mode 1: Trend pullback — only in trending or neutral regimes
        if self.use_trend_filter and ema is not None and regime != "ranging":
            if in_uptrend and rsi < PULLBACK_BUY_THRESHOLD and macd_ok_buy:
                if daily_trend != "bearish":
                    return "BUY"
            if in_downtrend and rsi > PULLBACK_SELL_THRESHOLD and macd_ok_sell:
                if daily_trend != "bullish":
                    return "SELL"

        # Mode 2: RSI extreme without trend filter
        if not self.use_trend_filter:
            if rsi < self.rsi_oversold and macd_ok_buy:
                if daily_trend != "bearish":
                    return "BUY"
            if rsi > self.rsi_overbought and macd_ok_sell:
                if daily_trend != "bullish":
                    return "SELL"

        # Mode 3: RSI divergence (works in all non-volatile regimes)
        if self.use_divergence:
            if divergence_buy and macd_ok_buy:
                if daily_trend != "bearish":
                    return "BUY"
            if divergence_sell and macd_ok_sell:
                if daily_trend != "bullish":
                    return "SELL"

        return "WAIT"

    def _get_daily_trend(self, data: pd.DataFrame, current_index: int) -> str:
        """
        Resample H4 data to Daily and check EMA trend direction.
        Returns "bullish", "bearish", or "neutral".
        """
        history = data.iloc[:current_index + 1]

        # Resample to daily OHLC
        daily = history.resample('D').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
        }).dropna()

        if len(daily) < self.mtf_ema_period:
            return "neutral"

        daily_ema = calculate_ema(daily, length=self.mtf_ema_period)
        if daily_ema is None:
            return "neutral"

        current_daily_close = daily['Close'].iloc[-1]

        if current_daily_close > daily_ema:
            return "bullish"
        elif current_daily_close < daily_ema:
            return "bearish"
        return "neutral"

    def _enter_trade(self, instrument: str, trade_type: str, entry_price: float,
                     entry_time: datetime, atr: float = None,
                     bar_index: int = 0) -> Trade:
        """Enter a new trade with ATR-based risk management."""
        try:
            levels = calculate_trade_levels(
                entry_price=entry_price,
                trade_type=trade_type,
                instrument=instrument,
                risk_percentage=self.risk_percentage,
                reward_ratio=self.reward_ratio,
                account_balance=self.balance,
                atr=atr,
                atr_sl_multiplier=self.atr_sl_multiplier,
            )

            trade = Trade(
                instrument=instrument,
                trade_type=trade_type,
                entry_price=entry_price,
                stop_loss=levels['stop_loss'],
                take_profit=levels['take_profit'],
                entry_time=entry_time,
                position_size=self.balance * (self.risk_percentage / 100),
                atr_at_entry=atr if atr else 0.0,
                entry_bar_index=bar_index,
            )

            atr_str = f"{atr:.5f}" if atr else "N/A"
            logger.debug(
                f"Entered {trade_type} at {entry_price} "
                f"(SL: {levels['stop_loss']}, TP: {levels['take_profit']}, "
                f"ATR: {atr_str})"
            )
            return trade

        except Exception as e:
            logger.error(f"Failed to enter trade: {e}")
            return None

    def _calculate_statistics(self, data_span_days: float = 365) -> Dict:
        """Calculate backtest statistics."""
        if not self.trades:
            return {
                'initial_balance': self.initial_balance,
                'final_balance': self.balance,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_return': 0.0,
                'total_return_pct': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'exit_reasons': {},
                'trades': []
            }

        winning_trades = [t for t in self.trades if t.status == "WIN"]
        losing_trades = [t for t in self.trades if t.status == "LOSS"]

        total_return = self.balance - self.initial_balance
        total_return_pct = (total_return / self.initial_balance) * 100

        win_rate = (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0

        avg_win = sum(t.profit_loss_pct for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.profit_loss_pct for t in losing_trades) / len(losing_trades) if losing_trades else 0

        total_wins = sum(t.profit_loss_pct for t in winning_trades)
        total_losses = abs(sum(t.profit_loss_pct for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # Calculate max drawdown
        balance_curve = [self.initial_balance]
        current_balance = self.initial_balance
        for trade in self.trades:
            current_balance += (trade.profit_loss_pct / 100) * current_balance
            balance_curve.append(current_balance)

        peak = balance_curve[0]
        max_drawdown = 0
        for balance in balance_curve:
            if balance > peak:
                peak = balance
            drawdown = ((peak - balance) / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Annualized Sharpe ratio
        returns = [t.profit_loss_pct for t in self.trades]
        avg_return = sum(returns) / len(returns) if returns else 0
        std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0
        per_trade_sharpe = (avg_return / std_dev) if std_dev > 0 else 0

        # Annualize: multiply by sqrt(trades_per_year)
        data_span_years = max(data_span_days / 365.25, 0.1)
        trades_per_year = len(self.trades) / data_span_years if data_span_years > 0 else len(self.trades)
        sharpe_ratio = per_trade_sharpe * (trades_per_year ** 0.5) if trades_per_year > 0 else 0

        # Exit reason breakdown
        exit_reasons = {}
        for trade in self.trades:
            reason = trade.exit_reason or "UNKNOWN"
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'exit_reasons': exit_reasons,
            'trades': [t.to_dict() for t in self.trades]
        }
