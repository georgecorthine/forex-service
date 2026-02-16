"""
Risk Management utilities for position sizing and trade calculations.
"""
import logging

logger = logging.getLogger("forex_service")

# Risk management configuration
DEFAULT_RISK_PERCENTAGE = 1.0  # Risk 1% of account per trade
DEFAULT_REWARD_RATIO = 2.0  # 2:1 reward-to-risk ratio
MIN_RISK_PERCENTAGE = 0.1
MAX_RISK_PERCENTAGE = 5.0


def calculate_pip_value(instrument: str, lot_size: float = 1.0) -> float:
    """
    Calculate the pip value for a given instrument.

    Args:
        instrument: Trading pair (e.g., "EUR_USD")
        lot_size: Position size in lots (default: 1.0 = 100,000 units)

    Returns:
        Pip value in account currency (assuming USD account)
    """
    # For most pairs, 1 pip = 0.0001
    # For JPY pairs, 1 pip = 0.01
    if "JPY" in instrument:
        # For JPY pairs: pip value = (0.01 * lot_size * 100,000) / exchange_rate
        # Simplified: ~$9.09 per pip for 1 standard lot (assuming USD account)
        return 9.09 * lot_size
    else:
        # For other pairs: pip value = (0.0001 * lot_size * 100,000)
        # = $10 per pip for 1 standard lot
        return 10.0 * lot_size


def calculate_stop_loss_pips(entry_price: float, stop_loss: float, instrument: str) -> float:
    """
    Calculate the stop loss distance in pips.

    Args:
        entry_price: Entry price
        stop_loss: Stop loss price
        instrument: Trading pair

    Returns:
        Stop loss distance in pips
    """
    if "JPY" in instrument:
        # For JPY pairs, 1 pip = 0.01
        return abs(entry_price - stop_loss) * 100
    else:
        # For other pairs, 1 pip = 0.0001
        return abs(entry_price - stop_loss) * 10000


def calculate_position_size(
    account_balance: float,
    risk_percentage: float,
    entry_price: float,
    stop_loss: float,
    instrument: str
) -> dict:
    """
    Calculate position size based on risk management rules.

    Args:
        account_balance: Current account balance in USD
        risk_percentage: Percentage of account to risk per trade (e.g., 1.0 for 1%)
        entry_price: Entry price for the trade
        stop_loss: Stop loss price
        instrument: Trading pair (e.g., "EUR_USD")

    Returns:
        Dictionary with position sizing details
    """
    # Validate inputs
    if risk_percentage < MIN_RISK_PERCENTAGE or risk_percentage > MAX_RISK_PERCENTAGE:
        logger.warning(f"Risk percentage {risk_percentage}% is outside recommended range ({MIN_RISK_PERCENTAGE}%-{MAX_RISK_PERCENTAGE}%)")
        risk_percentage = max(MIN_RISK_PERCENTAGE, min(MAX_RISK_PERCENTAGE, risk_percentage))

    if account_balance <= 0:
        raise ValueError("Account balance must be positive")

    if entry_price <= 0 or stop_loss <= 0:
        raise ValueError("Entry price and stop loss must be positive")

    # Calculate risk amount in USD
    risk_amount = account_balance * (risk_percentage / 100)

    # Calculate stop loss in pips
    sl_pips = calculate_stop_loss_pips(entry_price, stop_loss, instrument)

    if sl_pips == 0:
        raise ValueError("Stop loss must be different from entry price")

    # Calculate pip value for 1 standard lot
    pip_value = calculate_pip_value(instrument, lot_size=1.0)

    # Calculate position size in lots
    # Position size = Risk amount / (Stop loss in pips * Pip value)
    position_size_lots = risk_amount / (sl_pips * pip_value)

    # Round to 2 decimal places (standard for forex)
    position_size_lots = round(position_size_lots, 2)

    # Calculate position size in units (1 lot = 100,000 units)
    position_size_units = position_size_lots * 100000

    return {
        "position_size_lots": position_size_lots,
        "position_size_units": int(position_size_units),
        "risk_amount_usd": round(risk_amount, 2),
        "stop_loss_pips": round(sl_pips, 2),
        "pip_value": round(pip_value, 2)
    }


def calculate_trade_levels(
    entry_price: float,
    trade_type: str,
    instrument: str,
    risk_percentage: float = DEFAULT_RISK_PERCENTAGE,
    reward_ratio: float = DEFAULT_REWARD_RATIO,
    account_balance: float = 10000.0  # Default demo account balance
) -> dict:
    """
    Calculate stop loss and take profit levels based on risk management rules.

    Args:
        entry_price: Entry price
        trade_type: "BUY" or "SELL"
        instrument: Trading pair
        risk_percentage: Percentage of account to risk (default: 1.0%)
        reward_ratio: Reward-to-risk ratio (default: 2.0)
        account_balance: Account balance in USD

    Returns:
        Dictionary with trade levels and position sizing
    """
    precision = 3 if "JPY" in instrument else 5

    # Calculate stop loss (0.5% default)
    if trade_type == "BUY":
        stop_loss = round(entry_price * 0.995, precision)  # 0.5% below entry
        take_profit = round(entry_price * (1 + (0.005 * reward_ratio)), precision)
    elif trade_type == "SELL":
        stop_loss = round(entry_price * 1.005, precision)  # 0.5% above entry
        take_profit = round(entry_price * (1 - (0.005 * reward_ratio)), precision)
    else:
        raise ValueError("Trade type must be 'BUY' or 'SELL'")

    # Calculate position sizing
    try:
        position_info = calculate_position_size(
            account_balance=account_balance,
            risk_percentage=risk_percentage,
            entry_price=entry_price,
            stop_loss=stop_loss,
            instrument=instrument
        )
    except Exception as e:
        logger.error(f"Position sizing calculation failed: {e}")
        position_info = {
            "position_size_lots": 0.01,  # Minimum position size
            "position_size_units": 1000,
            "risk_amount_usd": 0.0,
            "stop_loss_pips": 0.0,
            "pip_value": 0.0
        }

    return {
        "entry": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "position_size_lots": position_info["position_size_lots"],
        "position_size_units": position_info["position_size_units"],
        "risk_amount_usd": position_info["risk_amount_usd"],
        "stop_loss_pips": position_info["stop_loss_pips"],
        "reward_ratio": reward_ratio
    }
