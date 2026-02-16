"""
Backtesting Engine for RSI + News Sentiment Strategy
"""
import pandas as pd
import logging
from typing import List, Dict, Tuple
from datetime import datetime
from utils.indicators import calculate_rsi
from utils.risk_management import calculate_trade_levels

logger = logging.getLogger("backtest")


class Trade:
    """Represents a single trade in the backtest."""
    def __init__(self, instrument: str, trade_type: str, entry_price: float,
                 stop_loss: float, take_profit: float, entry_time: datetime,
                 position_size: float = 1.0):
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

    def close(self, exit_price: float, exit_time: datetime):
        """Close the trade and calculate profit/loss."""
        self.exit_price = exit_price
        self.exit_time = exit_time

        if self.type == "BUY":
            self.profit_loss_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:  # SELL
            self.profit_loss_pct = ((self.entry_price - exit_price) / self.entry_price) * 100

        self.profit_loss = self.profit_loss_pct * self.position_size
        self.status = "WIN" if self.profit_loss > 0 else "LOSS"

    def check_exit(self, current_high: float, current_low: float, current_time: datetime) -> bool:
        """Check if stop loss or take profit was hit."""
        if self.type == "BUY":
            if current_low <= self.stop_loss:
                self.close(self.stop_loss, current_time)
                return True
            elif current_high >= self.take_profit:
                self.close(self.take_profit, current_time)
                return True
        else:  # SELL
            if current_high >= self.stop_loss:
                self.close(self.stop_loss, current_time)
                return True
            elif current_low <= self.take_profit:
                self.close(self.take_profit, current_time)
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
            'duration_hours': (self.exit_time - self.entry_time).total_seconds() / 3600 if self.exit_time else None
        }


class BacktestEngine:
    """Engine for backtesting RSI + News Sentiment strategy."""

    def __init__(self,
                 initial_balance: float = 10000.0,
                 risk_percentage: float = 1.0,
                 reward_ratio: float = 2.0,
                 rsi_period: int = 14,
                 rsi_overbought: int = 70,
                 rsi_oversold: int = 30,
                 max_concurrent_trades: int = 1):
        """
        Initialize the backtest engine.

        Args:
            initial_balance: Starting account balance
            risk_percentage: Risk per trade as percentage of balance
            reward_ratio: Reward-to-risk ratio
            rsi_period: RSI calculation period
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
            max_concurrent_trades: Maximum number of concurrent open trades
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.risk_percentage = risk_percentage
        self.reward_ratio = reward_ratio
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.max_concurrent_trades = max_concurrent_trades

        self.trades: List[Trade] = []
        self.open_trades: List[Trade] = []

    def run(self, data: pd.DataFrame, instrument: str = "EUR_USD") -> Dict:
        """
        Run backtest on historical data.

        Args:
            data: DataFrame with columns: Open, High, Low, Close, Volume
            instrument: Trading pair name

        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest for {instrument} with {len(data)} candles")

        # Reset state
        self.balance = self.initial_balance
        self.trades = []
        self.open_trades = []

        # Calculate RSI for all data
        data = data.copy()

        for i in range(self.rsi_period + 1, len(data)):
            current_time = data.index[i]
            current_row = data.iloc[i]

            # Check if any open trades hit SL or TP
            for trade in self.open_trades[:]:
                if trade.check_exit(current_row['High'], current_row['Low'], current_time):
                    self.open_trades.remove(trade)
                    # Update balance
                    self.balance += (trade.profit_loss_pct / 100) * self.balance

            # Only enter new trades if we have room
            if len(self.open_trades) >= self.max_concurrent_trades:
                continue

            # Calculate RSI up to current point
            history = data.iloc[:i+1]
            rsi = calculate_rsi(history, length=self.rsi_period)

            # Generate signal
            signal = self._generate_signal(rsi, current_row['Close'], instrument)

            if signal and signal != "WAIT":
                # Enter trade
                trade = self._enter_trade(
                    instrument=instrument,
                    trade_type=signal,
                    entry_price=current_row['Close'],
                    entry_time=current_time
                )
                if trade:
                    self.trades.append(trade)
                    self.open_trades.append(trade)

        # Close any remaining open trades at the last price
        if self.open_trades:
            last_price = data.iloc[-1]['Close']
            last_time = data.index[-1]
            for trade in self.open_trades:
                trade.close(last_price, last_time)

        # Calculate statistics
        results = self._calculate_statistics()
        logger.info(f"Backtest complete: {len(self.trades)} trades, Final balance: ${self.balance:.2f}")

        return results

    def _generate_signal(self, rsi: float, price: float, instrument: str) -> str:
        """
        Generate trading signal based on RSI.

        Note: In actual strategy, this also uses news sentiment.
        For backtesting, we use only RSI as news historical data is not available.
        """
        if rsi > self.rsi_overbought:
            return "SELL"
        elif rsi < self.rsi_oversold:
            return "BUY"
        return "WAIT"

    def _enter_trade(self, instrument: str, trade_type: str, entry_price: float,
                     entry_time: datetime) -> Trade:
        """Enter a new trade with risk management."""
        try:
            # Calculate trade levels
            levels = calculate_trade_levels(
                entry_price=entry_price,
                trade_type=trade_type,
                instrument=instrument,
                risk_percentage=self.risk_percentage,
                reward_ratio=self.reward_ratio,
                account_balance=self.balance
            )

            trade = Trade(
                instrument=instrument,
                trade_type=trade_type,
                entry_price=entry_price,
                stop_loss=levels['stop_loss'],
                take_profit=levels['take_profit'],
                entry_time=entry_time,
                position_size=self.balance * (self.risk_percentage / 100)
            )

            logger.debug(f"Entered {trade_type} trade at {entry_price} (SL: {levels['stop_loss']}, TP: {levels['take_profit']})")
            return trade

        except Exception as e:
            logger.error(f"Failed to enter trade: {e}")
            return None

    def _calculate_statistics(self) -> Dict:
        """Calculate backtest statistics."""
        if not self.trades:
            return {
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

        # Simple Sharpe ratio approximation (returns / std dev)
        returns = [t.profit_loss_pct for t in self.trades]
        avg_return = sum(returns) / len(returns) if returns else 0
        std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0
        sharpe_ratio = (avg_return / std_dev) if std_dev > 0 else 0

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
            'trades': [t.to_dict() for t in self.trades]
        }
