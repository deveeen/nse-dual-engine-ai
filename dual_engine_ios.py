#!/usr/bin/env python3
"""
========================================================================================
  📱 DUAL-ENGINE NSE AI FOR IPHONE 13 (iOS Edition for a-Shell / Pyto)
  --------------------------------------------------------------------------------------
  Run directly on your iPhone 13 terminal app:
    python dual_engine_ios.py HAL
    python dual_engine_ios.py NEWGEN
========================================================================================
"""

import sys
import ssl
import json
import urllib.request
import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime

# Bypass SSL on mobile network
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def calc_atr(df, period=14):
    h_l = df['High'] - df['Low']
    h_pc = (df['High'] - df['Close'].shift(1)).abs()
    l_pc = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def run_iphone_analysis(symbol: str):
    clean_sym = symbol.strip().upper().replace(".NS", "")
    ticker_str = f"{clean_sym}.NS"
    
    print("\n" + "="*65)
    print(f"  🏛️ DUAL-ENGINE NSE AI ORDER SLIP: {clean_sym}")
    print(f"  Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("="*65)
    
    try:
        t = yf.Ticker(ticker_str)
        df_d = t.history(period="1y", interval="1d", auto_adjust=True)
        df_w = t.history(period="3y", interval="1wk", auto_adjust=True)
        df_m = t.history(period="10y", interval="1mo", auto_adjust=True)
        
        if len(df_d) < 30:
            print(f"❌ Insufficient price history for {clean_sym}")
            return
            
        cur_price = float(df_d['Close'].iloc[-1])
        atr_14 = float(calc_atr(df_d).iloc[-1]) if len(df_d) >= 15 else (cur_price * 0.02)
        rsi_d = float(calc_rsi(df_d['Close'], 14).iloc[-1])
        rsi_w = float(calc_rsi(df_w['Close'], 14).iloc[-1]) if len(df_w) >= 15 else 50.0
        rsi_m = float(calc_rsi(df_m['Close'], 14).iloc[-1]) if len(df_m) >= 15 else 50.0
        
        sma20_w = float(df_w['Close'].rolling(20).mean().iloc[-1]) if len(df_w) >= 20 else np.nan
        ath = float(df_m['High'].cummax().iloc[-1]) if len(df_m) > 0 else float(df_d['High'].max())
        pct_ath = ((cur_price - ath) / ath) * 100
        
        c0 = df_w.iloc[-1]
        c1 = df_w.iloc[-2]
        rng_w = float(c0['High']) - float(c0['Low'])
        body_w = abs(float(c0['Close']) - float(c0['Open']))
        is_green_w = float(c0['Close']) >= float(c0['Open'])
        lower_wick_w = min(float(c0['Open']), float(c0['Close'])) - float(c0['Low'])
        upper_wick_w = float(c0['High']) - max(float(c0['Open']), float(c0['Close']))
        
        vol_ratio_w = float(c0['Volume']) / float(df_w['Volume'].rolling(10).mean().iloc[-1] + 1e-9)
        
        w_pattern = "Range Bound Base"
        w_bias = "NEUTRAL"
        if lower_wick_w >= 1.8 * body_w and upper_wick_w <= 0.35 * rng_w:
            w_pattern = "Hammer / Bullish Pin Bar"
            w_bias = "BULLISH"
        elif (not (float(c1['Close']) >= float(c1['Open']))) and is_green_w and (float(c0['Close']) >= float(c1['Open']) * 0.995):
            w_pattern = "Bullish Engulfing"
            w_bias = "BULLISH"
        elif upper_wick_w >= 1.8 * body_w and lower_wick_w <= 0.35 * rng_w:
            w_pattern = "Shooting Star (Top Rejection)"
            w_bias = "BEARISH"
        elif (not is_green_w) and cur_price < sma20_w:
            w_pattern = "Bearish Trend Cascade"
            w_bias = "BEARISH"
        elif is_green_w and cur_price > sma20_w:
            w_pattern = "Bullish Continuation"
            w_bias = "BULLISH"

        info = t.info
        pe_fwd = info.get('forwardPE', info.get('trailingPE', 'N/A'))
        opm = info.get('operatingMargins', np.nan)
        npm = info.get('profitMargins', np.nan)
        tot_cash = info.get('totalCash', 0) / 1e7 if info.get('totalCash') else 0
        tot_debt = info.get('totalDebt', 0) / 1e7 if info.get('totalDebt') else 0
        net_cash = tot_cash - tot_debt
        
        # Action & Horizon Parameters
        order_action = "BUY"
        order_type = "CNC (Delivery / Swing)"
        order_validity = "GTT (Good Till Triggered — 1 Year)"
        time_horizon = "2 to 8 Weeks (Positional Swing)"
        
        if (npm and npm < 0) or clean_sym in ['OLAELEC', 'BATAINDIA', 'CLEAN']:
            verdict = "TIER 6: ❌ Dead-Capital Exit (Liquidate Immediately)"
            order_action = "SELL / EXIT"
            order_type = "CNC (Sell Delivery)"
            order_validity = "IMMEDIATE (Market / Limit)"
            time_horizon = "Immediate Execution"
        elif clean_sym == 'KPITTECH':
            verdict = "TIER 4: ⏸️ Frozen (Hold 1.75%; DO NOT avg until weekly hammer)"
            order_action = "HOLD / NO FRESH BUY"
            order_type = "CNC (Hold Existing)"
            order_validity = "WAIT & WATCH (No Trade)"
            time_horizon = "Monitor Weekly Close"
        elif clean_sym == 'GREENPANEL':
            verdict = "TIER 5: 🛰️ Cyclical Satellite (Cap at 2.5% max)"
            order_action = "BUY (Satellite Tranche)"
            order_type = "CNC (Delivery / Turnaround)"
            order_validity = "GTT (365 Days)"
            time_horizon = "3 to 12 Months (Cyclical Recovery)"
        elif (w_bias == "BULLISH" or cur_price > sma20_w) and (isinstance(pe_fwd, (int, float)) and pe_fwd < 35):
            verdict = "TIER 1: 🟢 Triple-Confirmed High-Conviction Buy"
            order_action = "BUY (Tranche 1 - Momentum)"
            order_type = "CNC (Delivery / Swing)"
            order_validity = "GTT (365 Days)"
            time_horizon = "4 to 12 Weeks (Breakout Wave)"
        elif (rsi_m < 35 or rsi_w < 35):
            verdict = "TIER 2: 🟢 Deep-Value Reversal (33/33/33 Tranches)"
            order_action = "BUY (Tranche 1 - 33% Allocation)"
            order_type = "CNC (Delivery / Positional)"
            order_validity = "GTT (365 Days)"
            time_horizon = "3 to 9 Months (Mean-Reversion)"
        else:
            verdict = "TIER 3: 🟡 Core Portfolio Anchor (Hold & Compound)"
            order_action = "HOLD / ACCUMULATE ON DIPS"
            order_type = "CNC (Long-Term Investment)"
            order_validity = "SIP / GTT on 50W SMA Retest"
            time_horizon = "1 to 3+ Years (Secular Compounding)"

        trig_entry = cur_price * 1.005 if "BUY" in order_action else cur_price
        limit_buy = trig_entry * 1.002
        sl_price = cur_price - (1.5 * atr_14) if "BUY" in order_action else cur_price + (1.5 * atr_14)
        risk_pct = abs((cur_price - sl_price) / cur_price) * 100
        t0_scalp = cur_price + (0.75 * abs(cur_price - sl_price)) if "BUY" in order_action else cur_price - (0.75 * abs(cur_price - sl_price))
        t1_swing = cur_price + (1.5 * abs(cur_price - sl_price)) if "BUY" in order_action else cur_price - (1.5 * abs(cur_price - sl_price))
        t2_runner = cur_price + (2.5 * abs(cur_price - sl_price)) if "BUY" in order_action else cur_price - (2.5 * abs(cur_price - sl_price))
        
        print(f"📊 Market Price: ₹{cur_price:,.2f} ({pct_ath:.1f}% from ATH) | ATR: ₹{atr_14:.2f}")
        print(f"🕯️ Structure   : {w_pattern} (Vol: {vol_ratio_w:.2f}x) | 1W RSI: {rsi_w:.1f} | 1M RSI: {rsi_m:.1f}")
        print(f"🏢 Fundamentals: P/E: {pe_fwd} | Net Cash: ₹{net_cash:,.0f} Cr")
        print("\n" + "-"*65)
        print(f"🎯 VERDICT     : {verdict}")
        print(f"📌 ACTION      : [{order_action}] | PRODUCT: [{order_type}]")
        print(f"⏳ VALIDITY    : [{order_validity}]")
        print(f"⏱️ TIME HORIZON: [{time_horizon}]")
        print("-"*65)
        print(f"⚡ GTT TRIGGER : ₹{trig_entry:,.2f}  (Place Stop-Limit order)")
        print(f"💵 LIMIT PRICE : ₹{limit_buy:,.2f}  (+0.2% fill buffer)")
        print(f"🛡️ STOP LOSS   : ₹{sl_price:,.2f}  (1.5x ATR | Risk: -{risk_pct:.2f}%)")
        print(f"🎯 TARGET 0    : ₹{t0_scalp:,.2f}  [INTRADAY SCALP -> Trail SL to Cost]")
        print(f"🎯 TARGET 1    : ₹{t1_swing:,.2f}  [SWING 2-6 WKS -> Book 50% & Trail]")
        print(f"🎯 TARGET 2    : ₹{t2_runner:,.2f}  [RUNNER -> Full Measured Move]")
        print("="*65 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_iphone_analysis(sys.argv[1])
    else:
        sym = input("Enter Stock Ticker (e.g. HAL, NEWGEN, HDFCBANK): ").strip()
        if sym:
            run_iphone_analysis(sym)
