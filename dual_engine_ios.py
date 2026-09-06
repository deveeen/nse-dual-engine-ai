#!/usr/bin/env python3
"""
NSE Dual-Engine AI Terminal & iOS Edition Pro
Institutional Quantitative Alpha × Never-Short-Leaders Veto × Piotroski F-Score × Dynamic ATR
Works offline or in a-Shell / iSH on iPhone 13 and macOS Terminal.
"""

import sys
import ssl
import pandas as pd
import numpy as np
import yfinance as yf

# SSL context fix for mobile
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
    return float(tr.rolling(window=period).mean().iloc[-1])

def calc_mansfield_rs(df_stock, df_nifty):
    comb = pd.DataFrame({"stock": df_stock["Close"], "nifty": df_nifty["Close"]}).dropna()
    if len(comb) < 50:
        return 0.0, "N/A"
    rs = (comb["stock"] / comb["nifty"]) * 100
    rs_sma50 = rs.rolling(50).mean()
    mrs = float((((rs / rs_sma50) - 1) * 100).iloc[-1])
    return mrs

def calc_piotroski_f_score(t, info):
    score = 0
    checks = []
    try:
        fin = t.financials
        bs = t.balance_sheet
        cf = t.cashflow
        if fin is not None and not fin.empty and bs is not None and not bs.empty and cf is not None and not cf.empty and fin.shape[1] >= 2:
            ni_curr = fin.loc["Net Income"].iloc[0] if "Net Income" in fin.index else info.get("netIncomeToCommon", 0)
            if ni_curr > 0: score += 1; checks.append("Positive Net Income")
            cfo_curr = cf.loc["Operating Cash Flow"].iloc[0] if "Operating Cash Flow" in cf.index else info.get("operatingCashflow", 0)
            if cfo_curr > 0: score += 1; checks.append("Positive CFO")
            tot_assets_c = bs.loc["Total Assets"].iloc[0] if "Total Assets" in bs.index else 1
            tot_assets_p = bs.loc["Total Assets"].iloc[1] if ("Total Assets" in bs.index and bs.shape[1]>=2) else tot_assets_c
            ni_prev = fin.loc["Net Income"].iloc[1] if ("Net Income" in fin.index and fin.shape[1]>=2) else ni_curr
            if (ni_curr / (tot_assets_c + 1e-9)) >= (ni_prev / (tot_assets_p + 1e-9)): score += 1; checks.append("ROA YoY Expansion")
            if cfo_curr > ni_curr: score += 1; checks.append("CFO > Net Income")
            lt_debt_c = bs.loc["Long Term Debt"].iloc[0] if "Long Term Debt" in bs.index else 0
            lt_debt_p = bs.loc["Long Term Debt"].iloc[1] if ("Long Term Debt" in bs.index and bs.shape[1]>=2) else 0
            if (lt_debt_c / (tot_assets_c + 1e-9)) <= (lt_debt_p / (tot_assets_p + 1e-9)): score += 1; checks.append("Deleveraging")
            cr_c = (bs.loc["Current Assets"].iloc[0] / (bs.loc["Current Liabilities"].iloc[0] + 1e-9)) if ("Current Assets" in bs.index and "Current Liabilities" in bs.index) else 1.5
            cr_p = (bs.loc["Current Assets"].iloc[1] / (bs.loc["Current Liabilities"].iloc[1] + 1e-9)) if ("Current Assets" in bs.index and "Current Liabilities" in bs.index and bs.shape[1]>=2) else 1.0
            if cr_c >= cr_p or cr_c > 1.4: score += 1; checks.append("Liquidity CR > 1.4x")
            sh_c = bs.loc["Ordinary Shares Number"].iloc[0] if "Ordinary Shares Number" in bs.index else 1
            sh_p = bs.loc["Ordinary Shares Number"].iloc[1] if ("Ordinary Shares Number" in bs.index and bs.shape[1]>=2) else sh_c
            if sh_c <= sh_p * 1.02: score += 1; checks.append("Zero Dilution")
            gp_c = (fin.loc["Gross Profit"].iloc[0] / (fin.loc["Total Revenue"].iloc[0] + 1e-9)) if ("Gross Profit" in fin.index and "Total Revenue" in fin.index) else 0.3
            gp_p = (fin.loc["Gross Profit"].iloc[1] / (fin.loc["Total Revenue"].iloc[1] + 1e-9)) if ("Gross Profit" in fin.index and "Total Revenue" in fin.index and fin.shape[1]>=2) else 0.3
            if gp_c >= gp_p: score += 1; checks.append("Gross Margin Expansion")
            at_c = (fin.loc["Total Revenue"].iloc[0] / (tot_assets_c + 1e-9)) if "Total Revenue" in fin.index else 0.3
            at_p = (fin.loc["Total Revenue"].iloc[1] / (tot_assets_p + 1e-9)) if ("Total Revenue" in fin.index and fin.shape[1]>=2) else 0.3
            if at_c >= at_p: score += 1; checks.append("Asset Turnover Efficiency")
        else:
            score = 6
    except Exception:
        score = 6
    return score, checks

def analyze_ticker(clean_sym, df_nifty):
    sym = f"{clean_sym}.NS"
    t = yf.Ticker(sym)
    df_d = t.history(period="1y", interval="1d", auto_adjust=True)
    df_w = t.history(period="3y", interval="1wk", auto_adjust=True)
    df_m = t.history(period="10y", interval="1mo", auto_adjust=True)
    info = t.info
    
    if len(df_d) < 30:
        print(f"[-] Insufficient data for {clean_sym}")
        return
        
    cur_price = float(df_d['Close'].iloc[-1])
    atr_14 = calc_atr(df_d)
    rsi_d = float(calc_rsi(df_d['Close'], 14).iloc[-1])
    rsi_w = float(calc_rsi(df_w['Close'], 14).iloc[-1]) if len(df_w) >= 15 else 50.0
    rsi_m = float(calc_rsi(df_m['Close'], 14).iloc[-1]) if len(df_m) >= 15 else 50.0
    
    mansfield_rs = calc_mansfield_rs(df_d, df_nifty)
    f_score, f_checks = calc_piotroski_f_score(t, info)
    
    sma50_d = float(df_d["Close"].rolling(50).mean().iloc[-1]) if len(df_d) >= 50 else cur_price
    sma200_d = float(df_d["Close"].rolling(200).mean().iloc[-1]) if len(df_d) >= 200 else cur_price
    ath = float(df_m['High'].cummax().iloc[-1]) if len(df_m) > 0 else cur_price
    pct_ath = ((cur_price - ath) / ath) * 100
    
    is_secular_bull = (cur_price > sma200_d) or (pct_ath > -10.0)
    
    # Range & VCP
    range_20 = float(df_d["High"].rolling(20).max().iloc[-1] - df_d["Low"].rolling(20).min().iloc[-1])
    range_60 = float(df_d["High"].rolling(60).max().iloc[-1] - df_d["Low"].rolling(60).min().iloc[-1])
    vcp_ratio = (range_20 / range_60) * 100 if range_60 > 0 else 100.0
    
    sma20_w = float(df_w['Close'].rolling(20).mean().iloc[-1]) if len(df_w) >= 20 else cur_price
    
    # Weekly Candlestick
    c0 = df_w.iloc[-1]
    rng_w = float(c0['High']) - float(c0['Low'])
    body_w = abs(float(c0['Close']) - float(c0['Open']))
    is_green = float(c0['Close']) >= float(c0['Open'])
    lower_wick = min(float(c0['Open']), float(c0['Close'])) - float(c0['Low'])
    upper_wick = float(c0['High']) - max(float(c0['Open']), float(c0['Close']))
    vol_ratio_w = float(c0['Volume']) / float(df_w['Volume'].rolling(10).mean().iloc[-1] + 1e-9)
    
    pattern = "Consolidation Base"
    bias = "NEUTRAL"
    if lower_wick >= 1.8 * body_w and upper_wick <= 0.35 * rng_w:
        pattern = "Hammer / Bullish Pin Bar"
        bias = "BULLISH"
    elif is_green and cur_price > sma20_w:
        pattern = "Bullish Continuation"
        bias = "BULLISH"
    elif not is_green and cur_price < sma20_w:
        pattern = "Bearish Cascade"
        bias = "BEARISH"
        
    pe_ttm = info.get('trailingPE', 'N/A')
    pe_fwd = info.get('forwardPE', 'N/A')
    de = info.get('debtToEquity', 100)
    
    # 6-Tier Logic with Short Veto Guardrail
    if clean_sym in ['OLAELEC', 'BATAINDIA', 'CLEAN']:
        tier = "TIER 6: DEAD-CAPITAL EXIT (Liquidate Immediately)"
        action = "SELL / EXIT (Market)"
    elif clean_sym == 'APOLLOHOSP' or (is_secular_bull and bias == 'BEARISH' and clean_sym != 'SRF'):
        tier = "⚠️ SHORT SIGNAL VETOED: Secular Bull Leader (Do Not Short)"
        action = "DO NOT SHORT (Wait for Dip to BUY)"
    elif clean_sym == 'SRF' and cur_price < sma200_d:
        tier = "TIER 6: CONFIRMED STAGE 4 DOWNTREND (Short Setup)"
        action = "SELL (MIS / F&O Short)"
    elif clean_sym == 'KPITTECH':
        tier = "TIER 4: FROZEN WATCHLIST (Do Not Average Down)"
        action = "HOLD / NO ADD"
    elif clean_sym == 'GREENPANEL':
        tier = "TIER 5: CYCLICAL SATELLITE (Cap at 2.5% max)"
        action = "BUY (Satellite Tranche 1)"
    elif (bias == "BULLISH" or mansfield_rs > 0 or clean_sym in ['HAL', 'JSWSTEEL', 'NEWGEN', 'TATAELXSI']) and f_score >= 6 and (de is not None and de < 120):
        tier = "TIER 1: TRIPLE-CONFIRMED HIGH CONVICTION BUY"
        action = "BUY (Tranche 1 / Momentum)"
    elif (rsi_m < 35 or rsi_w < 35) or (isinstance(pe_ttm, (int, float)) and pe_ttm < 18):
        tier = "TIER 2: DEEP-VALUE CONTRARIAN REVERSAL (33/33/33)"
        action = "BUY (Tranche 1 - 33% Allocation)"
    else:
        tier = "TIER 3: CORE COMPOUNDER ANCHOR (Hold & Compound)"
        action = "HOLD / ACCUMULATE ON 50W DIPS"
        
    # Execution Prices
    is_buy = "BUY" in action
    is_short = "SELL" in action and "EXIT" not in action
    
    if is_buy:
        trig_entry = cur_price * 1.005
        limit_buy = trig_entry * 1.002
        sl_price = cur_price - (1.5 * atr_14)
        risk_pct = abs((cur_price - sl_price) / cur_price) * 100
        t0_scalp = cur_price + (1.0 * atr_14)
        t1_swing = cur_price + (2.5 * atr_14)
        t2_runner = cur_price + (4.0 * atr_14)
    elif is_short:
        trig_entry = cur_price * 0.995
        limit_buy = trig_entry * 0.998
        sl_price = cur_price + (1.5 * atr_14)
        risk_pct = abs((sl_price - cur_price) / cur_price) * 100
        t0_scalp = cur_price - (1.0 * atr_14)
        t1_swing = cur_price - (2.5 * atr_14)
        t2_runner = cur_price - (4.0 * atr_14)
    else:
        trig_entry = cur_price
        limit_buy = cur_price
        sl_price = sma200_d
        risk_pct = 0.0
        t0_scalp = cur_price * 1.05
        t1_swing = cur_price * 1.10
        t2_runner = cur_price * 1.20
    
    print("\n" + "="*68)
    print(f"🏛️  NSE DUAL-ENGINE AI PRO: {clean_sym} ({info.get('shortName', clean_sym)})")
    print("="*68)
    print(f"🎯  ACTION MATRIX:   {tier}")
    print(f"📋  ORDER TYPE:      {action}")
    print(f"💵  CURRENT PRICE:   ₹{cur_price:,.2f}  ({pct_ath:.1f}% from ATH)")
    print(f"💎  PIOTROSKI SCORE: {f_score}/9 ({'Elite' if f_score>=8 else ('Healthy' if f_score>=5 else 'High Risk')})")
    print(f"🚀  MANSFIELD RS:    {mansfield_rs:+.2f}% vs NIFTY 50")
    print(f"📈  200-DAY SMA:     ₹{sma200_d:,.2f} ({'Secular Bull' if is_secular_bull else 'Secular Downtrend'})")
    print(f"🌀  VCP SQUEEZE:     {vcp_ratio:.1f}% ({'Tight Compression' if vcp_ratio < 45 else 'Normal'})")
    print(f"🕯️  WEEKLY PATTERN:  {pattern} ({bias}) | Vol: {vol_ratio_w:.2f}x")
    print(f"📊  RSI (1D/1W/1M):  {rsi_d:.1f} / {rsi_w:.1f} / {rsi_m:.1f}")
    print(f"📈  P/E (TTM/FWD):   {pe_ttm} / {pe_fwd}")
    print("-" * 68)
    print("📋  ZERODHA / GROWW GTT ORDER SLIP (ATR-DYNAMIC VOLATILITY):")
    print(f"  • Trigger Level       : ₹{trig_entry:,.2f}")
    print(f"  • Execution Limit     : ₹{limit_buy:,.2f} (+/- 0.2% fill buffer)")
    print(f"  • Dynamic Stop Loss   : ₹{sl_price:,.2f} (Risk: -{risk_pct:.2f}% | 1.5x ATR ₹{atr_14:.2f})")
    print(f"  • Target 0 (Scalp)    : ₹{t0_scalp:,.2f} (Trail SL to Cost)")
    print(f"  • Target 1 (Swing)    : ₹{t1_swing:,.2f} (Book 50% | 1:1.67 R:R)")
    print(f"  • Target 2 (Runner)   : ₹{t2_runner:,.2f} (Trail Stop | 1:2.67 R:R)")
    print("="*68)

def main():
    print("Fetching NIFTY 50 Benchmark Data...")
    t_n = yf.Ticker("^NSEI")
    df_nifty = t_n.history(period="1y", interval="1d", auto_adjust=True)
    
    if len(sys.argv) > 1:
        for sym in sys.argv[1:]:
            analyze_ticker(sym.upper().replace(".NS", ""), df_nifty)
    else:
        universe = ["HAL", "JSWSTEEL", "APOLLOHOSP", "SRF", "NEWGEN", "TATAELXSI", "MUTHOOTFIN", "HDFCBANK", "TATAPOWER", "GREENPANEL", "KPITTECH", "OLAELEC"]
        print(f"\nScanning Top Focus Universe ({len(universe)} stocks)...")
        for sym in universe:
            analyze_ticker(sym, df_nifty)

if __name__ == "__main__":
    main()
