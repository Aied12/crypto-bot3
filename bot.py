import os
import time
import threading
import requests
import pandas as pd
import numpy as np
from flask import Flask

app = Flask(__name__)

# الصفحة الرئيسية
@app.route('/')
def home():
    return "Crypto Bot is Running Live 24/7! 🚀"

# مسار اختبار التيليجرام الفوري
@app.route('/test-telegram')
def test_telegram():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    
    if not token or not chat_id:
        return "❌ خطأ: متغيرات البيئة الخاصة بتيليجرام غير موجودة."

    message = "🧪 *اختبار ناجح!*\nبوت تداول الكريبتو يعمل بنجاح ومبتصل بتيليجرام 🚀"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return "✅ تم إرسال الرسالة إلى تيليجرام بنجاح! افحص تطبيق تيليجرام."
        else:
            return f"❌ خطأ من تيليجرام: {response.text}"
    except Exception as e:
        return f"❌ حدث خطأ في الاتصال: {e}"

# جلب البيانات من بينانس
def fetch_binance_klines(symbol, interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=5)
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
    except Exception:
        pass
    return None

# حساب المؤشرات الفنية
def calculate_indicators(df):
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    return df

# إرسال رسائل التنبيه
def send_telegram_message(message):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# فحص السوق والتنبيه عند تحقق الشروط القوية
def scan_market():
    symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "SUIUSDT",
        "SHIBUSDT", "NEARUSDT", "APTUSDT", "UNIUSDT", "ICPUSDT", "RENDERUSDT", "FETUSDT", "INJUSDT", "STXUSDT", "IMXUSDT",
        "TIAUSDT", "ARBUSDT", "OPUSDT", "POLUSDT", "ATOMUSDT", "ETCUSDT", "LTCUSDT", "BCHUSDT", "KASUSDT", "HBARUSDT",
        "GRTUSDT", "RUNEUSDT", "SEIUSDT", "SAGAUSDT", "OMUSDT", "PENDLEUSDT", "WIFUSDT", "PEPEUSDT", "FLOKIUSDT", "BONKUSDT",
        "JUPUSDT", "PYTHUSDT", "STRKUSDT", "MANTAUSDT", "ALTUSDT", "PORTALUSDT", "AXLUSDT", "ETHFIUSDT", "ENAUSDT", "BBUSDT",
        "NOTUSDT", "IOUSDT", "ZKUSDT", "ZROUSDT", "BLUMUSDT", "DOGSUSDT", "CATIUSDT", "HMSTRUSDT", "EIGENUSDT", "SCRUSDT",
        "APEUSDT", "MANAUSDT", "SANDUSDT", "AXSUSDT", "GALAUSDT", "CHZUSDT", "ENJUSDT", "FLOWUSDT", "FTMUSDT", "ALGOUSDT",
        "VETUSDT", "THETAUSDT", "EGLDUSDT", "XTZUSDT", "EOSUSDT", "SANDUSDT", "KAVAUSDT", "CRVUSDT", "SNXUSDT", "COMPUSDT",
        "MKRUSDT", "AAVEUSDT", "CAKEUSDT", "SUSHIUSDT", "1INCHUSDT", "ZRXUSDT", "BATUSDT", "ZILUSDT", "IOSTUSDT", "ONTUSDT",
        "QTUMUSDT", "ICXUSDT", "NEOUSDT", "DASHUSDT", "ZECUSDT", "XEMUSDT", "WAVESUSDT", "LRCUSDT", "SNXUSDT", "YFIUSDT",
        "UMAUSDT", "BALUSDT", "RSRUSDT", "OCEANUSDT", "RENUSDT", "KNCUSDT", "STORJUSDT", "ANTUSDT", "CRVUSDT", "SANDUSDT",
        "LUNAUSDT", "LUNCUSDT", "USTCUSDT", "SHIBUSDT", "DOGEUSDT", "TRXUSDT", "XLMUSDT", "XRPUSDT", "EOSUSDT", "XTZUSDT",
        "ATOMUSDT", "VETUSDT", "THETAUSDT", "ALGOUSDT", "FILUSDT", "TRBUSDT", "RLCUSDT", "NEIROUSDT", "TURBOUSDT", "COWUSDT",
        "PNUTUSDT", "ACTUSDT", "GOATUSDT", "MOODENGUSDT", "HIPPOUSDT", "CHILLGUYUSDT", "USUALUSDT", "THEUSDT", "PENGUUSDT",
        "VIRTUALUSDT", "AI16ZUSDT", "FARTCOINUSDT", "SPXUSDT", "MELANIAUSDT", "TRUMPUSDT", "BOMEUSDT", "MEUSDT", "SONICUSDT",
        "BERAUSDT", "IPUSDT", "KAIAUSDT", "SPLUSDT", "PUFFERUSDT", "SCRTUSDT", "MBOXUSDT", "STGUSDT", "RDNTUSDT", "GMXUSDT",
        "JOEUSDT", "PERPUSDT", "SPELLUSDT", "MAGICUSDT", "SSVUSDT", "LDOUSDT", "FXSUSDT", "LQTYUSDT", "AGIXUSDT", "OCEANUSDT",
        "NMRUSDT", "BANDUSDT", "API3USDT", "C98USDT", "HOOKUSDT", "HIGHUSDT", "IDUSDT", "EDUUSDT", "CYBERUSDT", "MAVUSDT",
        "ARKMUSDT", "NFPUSDT", "XAIUSDT", "PORTALUSDT", "PIXELUSDT", "AEVOUSDT", "BOMEUSDT", "ENAUSDT", "SAGAUSDT", "OMUSDT"
    ]
    
    symbols = list(dict.fromkeys(symbols))
    
    while True:
        print(f"--- Starting Filtered Market Scan for {len(symbols)} coins ---")
        for symbol in symbols:
            df = fetch_binance_klines(symbol)
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                last_row = df.iloc[-1]
                prev_row = df.iloc[-2] # الشمعة السابقة لفحص التقاطعات
                
                close_price = last_row['close']
                ema_val = last_row['EMA_9']
                vwap_val = last_row['VWAP']
                
                # حساب الشروط الإيجابية (عدد الشروط المتحققة)
                conditions_met = 0
                
                # الشرط 1: السعر أعلى من EMA 9
                if close_price > ema_val:
                    conditions_met += 1
                    
                # الشرط 2: السعر أعلى من VWAP
                if close_price > vwap_val:
                    conditions_met += 1
                    
                # الشرط 3: EMA 9 أعلى من VWAP (اتجاه صعودي للمتوسطات)
                if ema_val > vwap_val:
                    conditions_met += 1
                    
                # الشرط 4: تقاطع إيجابي حدث في هذه الشمعة (السعر عبر للأعلى فوق EMA 9)
                if prev_row['close'] <= prev_row['EMA_9'] and close_price > ema_val:
                    conditions_met += 1

                # إذا تحقق 3 شروط أو أكثر (تستطيع جعلها 4 شروط إذا أردت دقة أعلى)
                if conditions_met >= 3:
                    message = (
                        f"🚨 *فرصة إيجابية قوية ({symbol})*\n"
                        f"• الشروط المتحققة: `{conditions_met}/4`\n"
                        f"• السعر الحالي: `{close_price}`\n"
                        f"• قيمة الـ VWAP: `{vwap_val:.4f}`\n"
                        f"• مؤشر EMA 9: `{ema_val:.4f}`"
                    )
                    print(message)
                    send_telegram_message(message)
                
            time.sleep(1.5)
        time.sleep(300)

# تشغيل الفحص في الخلفية
def run_scanner_thread():
    thread = threading.Thread(target=scan_market, daemon=True)
    thread.start()

run_scanner_thread()
