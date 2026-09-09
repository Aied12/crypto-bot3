import os
import time
import threading
import requests
import pandas as pd
import numpy as np
from flask import Flask

# تعريف متغير الفلاسك الأساسي لكي يتعرف عليه Gunicorn
app = Flask(__name__)

@app.route('/')
def home():
    return "Crypto Bot is Running Live 24/7! 🚀"

# جلب بيانات الشموع من بينانس
def fetch_binance_klines(symbol="BTCUSDT", interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
    return None

# حساب مؤشرات VWAP و EMA 9
def calculate_indicators(df):
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    return df

# إرسال التنبيهات عبر التيليجرام
def send_telegram_message(message):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    
    if not token or not chat_id:
        print("Telegram credentials missing in environment variables!")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"Failed to send telegram message: {response.text}")
    except Exception as e:
        print(f"Telegram error: {e}")

# دالة فحص السوق الدورية
def scan_market():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    while True:
        print("--- Starting Market Scan ---")
        for symbol in symbols:
            df = fetch_binance_klines(symbol)
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                last_row = df.iloc[-1]
                
                message = (
                    f"🚨 *تنبيه حركة السوق ({symbol})*\n"
                    f"• السعر الحالي: `{last_row['close']}`\n"
                    f"• قيمة الـ VWAP: `{last_row['VWAP']:.2f}`\n"
                    f"• مؤشر EMA 9: `{last_row['EMA_9']:.2f}`"
                )
                print(message)
                send_telegram_message(message)
                
            time.sleep(2)
        time.sleep(900)

# تشغيل الفحص في خلفية السيرفر
def run_scanner_thread():
    thread = threading.Thread(target=scan_market, daemon=True)
    thread.start()

# تشغيل الثريد عند بدء السيرفر
run_scanner_thread()
