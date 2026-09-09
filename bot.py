import os
import time
import threading
import requests
import pandas as pd
import pandas_ta as ta
from flask import Flask

# إعداد خادم ويب مصغر لبقاء التطبيق نشطاً 24/7 على السحابة (Render)
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and scanning the market 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# بيانات بوت تليجرام الخاصة بك (تم ضبطها مسبقاً)
TELEGRAM_TOKEN = "8993002560:AAE8F8YPcNadjM5h2nZBoXk_EJUJqLxhwXA"
CHAT_ID = "54823841"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_all_binance_symbols():
    url = "https://api.binance.com/api/v3/exchangeInfo"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [s['symbol'] for s in data['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
    except Exception:
        pass
    return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

def fetch_binance_klines(symbol, interval, limit=150):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            raw_data = response.json()
            df = pd.DataFrame(raw_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'not', 'tbba', 'tbqa', 'ignore'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            return df
    except Exception:
        return None
    return None

def check_conditions(df_15m, df_1h=None, swing_length=5):
    if len(df_15m) < 60:
        return None, 0, 0, 0

    df_15m['ATR'] = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'], length=14)
    df_15m['RSI'] = ta.rsi(df_15m['close'], length=14)
    df_15m['VolMA'] = ta.sma(df_15m['volume'], length=20)

    prev = df_15m.iloc[-2]
    rsi_bull_ok = prev['RSI'] < 65
    rsi_bear_ok = prev['RSI'] > 35
    vol_ok = prev['volume'] > (prev['VolMA'] * 1.1)

    body_size = abs(prev['close'] - prev['open'])
    atr_val = prev['ATR'] if not pd.isna(prev['ATR']) else prev['close'] * 0.015
    bull_disp = (prev['close'] > prev['open']) and (body_size >= atr_val * 1.3)
    bear_disp = (prev['close'] < prev['open']) and (body_size >= atr_val * 1.3)

    rolling_high = df_15m['high'].rolling(window=swing_length).max()
    rolling_low = df_15m['low'].rolling(window=swing_length).min()
    
    bos_bull = prev['close'] > rolling_high.iloc[-2]
    bos_bear = prev['close'] < rolling_low.iloc[-2]

    ob_low, ob_top = prev['low'], prev['high']
    for i in range(len(df_15m)-5, len(df_15m)-15, -1):
        if df_15m.iloc[i]['close'] < df_15m.iloc[i]['open']:
            ob_low = df_15m.iloc[i]['low']
            ob_top = df_15m.iloc[i]['high']
            break

    htf_long, htf_short = True, True
    if df_1h is not None and len(df_1h) > 50:
        htf_ema = ta.ema(df_1h['close'], length=200).iloc[-2]
        htf_close = df_1h['close'].iloc[-2]
        htf_long = htf_close > htf_ema
        htf_short = htf_close < htf_ema

    if bos_bull and vol_ok and htf_long and bull_disp and rsi_bull_ok:
        sl = round(ob_low - (atr_val * 0.2), 4)
        risk = prev['close'] - sl
        tp = round(prev['close'] + (risk * 1.5), 4)
        return "🚀 دخول شراء (SMC Long)", round(prev['close'], 4), tp, sl

    elif bos_bear and vol_ok and htf_short and bear_disp and rsi_bear_ok:
        sl = round(ob_top + (atr_val * 0.2), 4)
        risk = sl - prev['close']
        tp = round(prev['close'] - (risk * 1.5), 4)
        return "🔻 دخول بيع (SMC Short)", round(prev['close'], 4), tp, sl

    return None, 0, 0, 0

def market_scanner_loop():
    sent_signals = set() # لمنع تكرار الإرسال لنفس الشمعة
    while True:
        try:
            symbols = get_all_binance_symbols()
            for symbol in symbols:
                df_15m = fetch_binance_klines(symbol, interval="15m")
                df_1h = fetch_binance_klines(symbol, interval="60m")
                
                if df_15m is not None:
                    signal, price, tp, sl = check_conditions(df_15m, df_1h)
                    timestamp = df_15m.iloc[-2]['timestamp']
                    signal_id = f"{symbol}_{timestamp}_{signal}"
                    
                    if signal and signal_id not in sent_signals:
                        msg = (
                            f"🚨 **تنبيه إشارة فنية جديدة!**\n\n"
                            f"📌 العملة: `{symbol}`\n"
                            f"📊 الإشارة: **{signal}**\n"
                            f"💵 سعر الإغلاق: `{price}`\n"
                            f"🎯 الهدف (TP): `{tp}`\n"
                            f"🛑 وقف الخسارة (SL): `{sl}`\n"
                            f"⏱️ الفريم: `15 دقيقة`"
                        )
                        send_telegram(msg)
                        sent_signals.add(signal_id)
                        if len(sent_signals) > 500:
                            sent_signals.clear()
                            
                time.sleep(1) # فاصل زمني لتجنب حظر الاتصال بمنصة باينانس
            
            # الانتظار لمدة 5 دقائق قبل إعادة فحص السوق بالكامل
            time.sleep(300)
        except Exception as e:
            print(f"Error in loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    # تشغيل الماسح في الخلفية 24/7
    t = threading.Thread(target=market_scanner_loop)
    t.daemon = True
    t.start()
    
    # تشغيل سيرفر الويب المصغر
    run_flask()
 
