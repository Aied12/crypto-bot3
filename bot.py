import os
import time
import threading
import requests
import pandas as pd
from flask import Flask

app = Flask(__name__)

# إعدادات تيليجرام (يمكنك وضعها مباشرة أو عبر متغيرات البيئة في Render)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "ضع_توكن_البوت_هنا")
CHAT_ID = os.environ.get("CHAT_ID", "ضع_رقم_الشات_هنا")

def send_telegram_message(message):
    if "ضع_توكن" in TELEGRAM_TOKEN:
        print("Telegram Token not configured.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

@app.route("/")
def home():
    return "SMC Crypto Bot is Running Live & Active! 🚀"

def fetch_binance_klines(symbol="BTCUSDT", interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if isinstance(data, list):
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
    return None

def calculate_indicators(df):
    # حساب المتوسط المتحرك الأسي EMA 9 بديل لـ pandas_ta
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    
    # حساب الـ VWAP بديل لـ pandas_ta
    v = df['volume']
    p = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP'] = (p * v).cumsum() / v.cumsum()
    return df

def scan_market():
    # قائمة العملات التي يتم فحصها
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    print("--- Starting Market Scan ---")
    
    for symbol in symbols:
        df = fetch_binance_klines(symbol)
        if df is not None and not df.empty:
            df = calculate_indicators(df)
            last_row = df.iloc[-1]
            
            # مثال على إرسال تنبيه إذا تحققت شروط بسيطة
            message = (
                f"🚨 **تنبيه حركة السوق ({symbol})**\n"
                f"• السعر الحالي: `{last_row['close']}`\n"
                f"• قيمة الـ VWAP: `{last_row['VWAP']:.2f}`\n"
                f"• مؤشر EMA 9: `{last_row['EMA_9']:.2f}`"
            )
            print(message)
            # يمكنك تفعيل السطر التالي لاحقاً لإرسال التنبيهات تلقائياً لتيليجرام
            # send_telegram_message(message)
            
        time.sleep(1)

def background_scanner():
    while True:
        try:
            scan_market()
        except Exception as e:
            print(f"Scanner error: {e}")
        # فترة الانتظار بين كل عملية فحص (مثلاً كل 5 دقائق = 300 ثانية)
        time.sleep(300)

if __name__ == "__main__":
    # تشغيل الماسح الضوئي في خيط خلفي (Background Thread) ليعمل بالتوازي مع خادم الويب
    scanner_thread = threading.Thread(target=background_scanner, daemon=True)
    scanner_thread.start()
    
    # تشغيل خادم Flask بالمنفذ المطلوب لموقع Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
