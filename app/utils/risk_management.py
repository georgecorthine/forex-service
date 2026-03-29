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

# ATR-based stop loss configuration
DEFAULT_ATR_SL_MULTIPLIER = 1.5  # SL = 1.5 * ATR
DEFAULT_ATR_TP_MULTIPLIER = 3.0  # TP = 3.0 * ATR (2:1 R:R)
FALLBACK_SL_PERCENTAGE = 0.005  # 0.5% fallback if ATR unavailable


def calculate_pip_value(instrument: str, lot_size: float = 1.0) -> float:
    """
    Calculate the pip value for a given instrument.
    """
    if "JPY" in instrument:
        return 9.09 * lot_size
    else:
        return 10.0 * lot_size


def calculate_stop_loss_pips(entry_price: float, stop_loss: float, instrument: str) -> float:
    """
    Calculate the stop loss distance in pips.
    """
    if "JPY" in instrument:
        return abs(entry_price - stop_loss) * 100
    else:
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
    """
    if risk_percentage < MIN_RISK_PERCENTAGE or risk_percentage > MAX_RISK_PERCENTAGE:
        logger.warning(f"Risk percentage {risk_percentage}% is outside recommended range ({MIN_RISK_PERCENTAGE}%-{MAX_RISK_PERCENTAGE}%)")
        risk_percentage = max(MIN_RISK_PERCENTAGE, min(MAX_RISK_PERCENTAGE, risk_percentage))

    if account_balance <= 0:
        raise ValueError("Account balance must be positive")

    if entry_price <= 0 or stop_loss <= 0:
        raise ValueError("Entry price and stop loss must be positive")

    risk_amount = account_balance * (risk_percentage / 100)
    sl_pips = calculate_stop_loss_pips(entry_price, stop_loss, instrument)

    if sl_pips == 0:
        raise ValueError("Stop loss must be different from entry price")

    pip_value = calculate_pip_value(instrument, lot_size=1.0)
    position_size_lots = risk_amount / (sl_pips * pip_value)
    position_size_lots = round(position_size_lots, 2)
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
    account_balance: float = 10000.0,
    atr: float = None,
    atr_sl_multiplier: float = DEFAULT_ATR_SL_MULTIPLIER,
) -> dict:
    """
    Calculate stop loss and take profit levels.

    When ATR is provided, uses ATR-based dynamic stops.
    Otherwise falls back to fixed percentage stops.
    """
    precision = 3 if "JPY" in instrument else 5

    if atr is not None and atr > 0:
        # ATR-based dynamic stops
        sl_distance = atr * atr_sl_multiplier
        tp_distance = sl_distance * reward_ratio

        if trade_type == "BUY":
            stop_loss = round(entry_price - sl_distance, precision)
            take_profit = round(entry_price + tp_distance, precision)
        elif trade_type == "SELL":
            stop_loss = round(entry_price + sl_distance, precision)
            take_profit = round(entry_price - tp_distance, precision)
        else:
            raise ValueError("Trade type must be 'BUY' or 'SELL'")
    else:
        # Fallback: fixed percentage stops
        if trade_type == "BUY":
            stop_loss = round(entry_price * (1 - FALLBACK_SL_PERCENTAGE), precision)
            take_profit = round(entry_price * (1 + FALLBACK_SL_PERCENTAGE * reward_ratio), precision)
        elif trade_type == "SELL":
            stop_loss = round(entry_price * (1 + FALLBACK_SL_PERCENTAGE), precision)
            take_profit = round(entry_price * (1 - FALLBACK_SL_PERCENTAGE * reward_ratio), precision)
        else:
            raise ValueError("Trade type must be 'BUY' or 'SELL'")

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
            "position_size_lots": 0.01,
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
        "reward_ratio": reward_ratio,
        "atr_based": atr is not None and atr > 0
    }
