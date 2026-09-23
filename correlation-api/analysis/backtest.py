import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple

def generate_zscore_signals(
    spread: pd.Series,
    window: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.0
) -> Tuple[pd.Series, pd.Series]:
    """
    Generate walk-forward signals from a spread using rolling z-score.
    
    Returns:
        Tuple of (signals, zscore)
    """
    mean = spread.rolling(window=window).mean()
    std = spread.rolling(window=window).std()
    
    # Avoid division by zero
    std = std.where(std >= 1e-12, np.nan)
    std = std.ffill().fillna(1e-6)
    
    zscore = (spread - mean) / std
    
    signals = pd.Series(0, index=spread.index)
    current_pos = 0
    
    for i in range(len(spread)):
        z = zscore.iloc[i]
        if pd.isna(z):
            signals.iloc[i] = 0
            continue
            
        if current_pos == 0:
            if z <= -entry_z:
                current_pos = 1
            elif z >= entry_z:
                current_pos = -1
        elif current_pos == 1:
            if z >= -exit_z:
                current_pos = 0
        elif current_pos == -1:
            if z <= exit_z:
                current_pos = 0
                
        signals.iloc[i] = current_pos
        
    return signals, zscore

def run_backtest(
    prices_a: pd.Series,
    prices_b: pd.Series,
    signals: pd.Series,
    hedge_ratio: float = 1.0
) -> Dict[str, Any]:
    """
    Run a walk-forward pairs trading backtest.
    
    Args:
        prices_a: pd.Series of asset A prices, indexed by Date
        prices_b: pd.Series of asset B prices, indexed by Date
        signals: pd.Series of trading signals (+1 = Long Spread, -1 = Short Spread, 0 = Flat), indexed by Date
        hedge_ratio: hedge ratio to determine the spread (spread = price_a - hedge_ratio * price_b)
        
    Returns:
        A dictionary containing backtest performance metrics:
        - equity_curve: list of dicts with {"date": str, "value": float}
        - sharpe: float (annualized Sharpe ratio)
        - max_dd: float (maximum drawdown as a positive percentage)
        - num_trades: int
        - win_rate: float
        - trade_log: list of dicts with detailed trade info
    """
    # Ensure indexes are aligned and sorted chronologically
    common_idx = prices_a.index.intersection(prices_b.index).intersection(signals.index).sort_values()
    
    p_a = prices_a.loc[common_idx]
    p_b = prices_b.loc[common_idx]
    sigs = signals.loc[common_idx]
    
    # Calculate daily price changes
    dp_a = p_a.diff().fillna(0.0)
    dp_b = p_b.diff().fillna(0.0)
    
    spread = p_a - hedge_ratio * p_b
    
    # Capital base is the gross exposure at the start of the daily holding period
    # Capital = price_a + hedge_ratio * price_b
    # Prevent division by zero
    gross_exposure = p_a + hedge_ratio * p_b
    gross_exposure = gross_exposure.replace(0.0, np.nan).ffill().fillna(1.0)
    
    # Position held during day t is decided by signal at day t-1
    held_positions = sigs.shift(1).fillna(0.0)
    
    # Daily P&L of holding 1 unit of spread
    # Long spread (+1) means long A, short B. Short spread (-1) means short A, long B.
    daily_spread_diff = dp_a - hedge_ratio * dp_b
    daily_dollar_pnl = held_positions * daily_spread_diff
    
    # Daily percentage return relative to gross exposure of the previous day
    prev_exposure = gross_exposure.shift(1).fillna(
        gross_exposure.iloc[0] if len(gross_exposure) else 1.0)
    daily_returns = daily_dollar_pnl / prev_exposure
    
    # Calculate cumulative returns (equity curve)
    cumulative_returns = (1.0 + daily_returns).cumprod().sub(1.0)
    
    # Construct equity curve series
    equity_curve = []
    for date_val, val in cumulative_returns.items():
        date_str = str(date_val.date()) if hasattr(date_val, "date") else str(date_val)
        equity_curve.append({
            "date": date_str,
            "value": float(val)
        })
        
    # Calculate Sharpe Ratio (annualized, assuming risk-free rate of 0)
    mean_ret = daily_returns.mean()
    std_ret = daily_returns.std(ddof=1)
    if std_ret > 1e-6:
        sharpe = float(np.sqrt(252) * (mean_ret / std_ret))
    else:
        sharpe = 0.0
        
    # Calculate Maximum Drawdown
    # peak-to-trough drop (as a fraction of equity (positive))
    equity = 1.0 + cumulative_returns
    running_max = equity.cummax()
    drawdown = 1.0 - (equity / running_max)
    max_dd = float(drawdown.max())
    
    trade_log = []
    current_pos = 0
    entry_idx = -1
    
    n = len(sigs)
    for i in range(n):
        sig = int(sigs.iloc[i])
        
        # Position transition
        if sig != current_pos:
            # If we were in a position, close it
            if current_pos != 0:
                exit_idx = i

                ent_date = sigs.index[entry_idx]
                ex_date = sigs.index[exit_idx]
                
                ent_price_a = float(p_a.iloc[entry_idx])
                ent_price_b = float(p_b.iloc[entry_idx])
                ex_price_a = float(p_a.iloc[exit_idx])
                ex_price_b = float(p_b.iloc[exit_idx])
                
                ent_spread = float(spread.iloc[entry_idx])
                ex_spread = float(spread.iloc[exit_idx])
                
                ent_exposure = ent_price_a + hedge_ratio * ent_price_b
                if ent_exposure == 0:
                    ent_exposure = 1.0
                    
                # Long spread P&L: spread_exit - spread_entry
                # Short spread P&L: spread_entry - spread_exit
                pnl_val = (ex_spread - ent_spread) if current_pos == 1 else (ent_spread - ex_spread)
                pnl_pct = pnl_val / ent_exposure
                
                trade_log.append({
                    "type": "LONG" if current_pos == 1 else "SHORT",
                    "entry_date": str(ent_date.date()) if hasattr(ent_date, "date") else str(ent_date),
                    "exit_date": str(ex_date.date()) if hasattr(ex_date, "date") else str(ex_date),
                    "entry_price_a": ent_price_a,
                    "entry_price_b": ent_price_b,
                    "exit_price_a": ex_price_a,
                    "exit_price_b": ex_price_b,
                    "entry_spread": ent_spread,
                    "exit_spread": ex_spread,
                    "pnl_val": float(pnl_val),
                    "pnl_pct": float(pnl_pct),
                    "holding_period": int(exit_idx - entry_idx)
                })
                
            # If new position is non-zero, open it
            if sig != 0:
                entry_idx = i
            current_pos = sig
            
    # Handle open trade at the end of the series
    if current_pos != 0 and n > 0:
        exit_idx = n - 1
        ent_date = sigs.index[entry_idx]
        ex_date = sigs.index[exit_idx]
        
        ent_price_a = float(p_a.iloc[entry_idx])
        ent_price_b = float(p_b.iloc[entry_idx])
        ex_price_a = float(p_a.iloc[exit_idx])
        ex_price_b = float(p_b.iloc[exit_idx])
        
        ent_spread = float(spread.iloc[entry_idx])
        ex_spread = float(spread.iloc[exit_idx])
        
        ent_exposure = ent_price_a + hedge_ratio * ent_price_b
        if ent_exposure == 0:
            ent_exposure = 1.0
            
        pnl_val = (ex_spread - ent_spread) if current_pos == 1 else (ent_spread - ex_spread)
        pnl_pct = pnl_val / ent_exposure
        
        trade_log.append({
            "type": "LONG" if current_pos == 1 else "SHORT",
            "entry_date": str(ent_date.date()) if hasattr(ent_date, "date") else str(ent_date),
            "exit_date": str(ex_date.date()) if hasattr(ex_date, "date") else str(ex_date),
            "entry_price_a": ent_price_a,
            "entry_price_b": ent_price_b,
            "exit_price_a": ex_price_a,
            "exit_price_b": ex_price_b,
            "entry_spread": ent_spread,
            "exit_spread": ex_spread,
            "pnl_val": float(pnl_val),
            "pnl_pct": float(pnl_pct),
            "holding_period": int(exit_idx - entry_idx)
        })
        
    num_trades = len(trade_log)
    if num_trades > 0:
        profitable_trades = sum(1 for t in trade_log if t["pnl_val"] > 0)
        win_rate = float(profitable_trades / num_trades)
    else:
        win_rate = 0.0
        
    return {
        "equity_curve": equity_curve,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "num_trades": num_trades,
        "win_rate": win_rate,
        "trade_log": trade_log
    }
