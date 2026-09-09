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
    return "Crypto SMC Bot is Running Live 24/7! 🚀"

# مسار اختبار التيليجرام الفوري
@app.route('/test-telegram')
def test_telegram():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    
    if not token or not chat_id:
        return "❌ خطأ: متغيرات البيئة الخاصة بتيليجرام غير موجودة."

    message = "🧪 *اختبار ناجح!*\nبوت تداول SMC Long يعمل بنجاح ومبتصل بتيليجرام 🚀"
    
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

# حساب المؤشرات الفنية ومنطق الـ SMC
def calculate_smc_indicators(df):
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    
    # متوسط حجم التداول لآخر 20 شمعة لاكتشاف السيولة العالية
    df['Vol_SMA20'] = df['volume'].rolling(window=20).mean()
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

# فحص السوق للبحث عن إشارات SMC Long حصراً
def scan_market():
    symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "SUIUSDT",
        "SHIBUSDT", "NEARUSDT", "APTUSDT", "UNIUSDT", "ICPUSDT", "RENDERUSDT", "FETUSDT", "INJUSDT", "STXUSDT", "IMXUSDT",
        "TIAUSDT", "ARBUSDT", "OPUSDT", "POLUSDT", "ATOMUSDT", "ETCUSDT", "LTCUSDT", "BCHUSDT", "KASUSDT", "HBARUSDT",
        "GRTUSDT", "RUNEUSDT", "SEIUSDT", "SAGAUSDT", "OMUSDT", "PENDLEUSDT", "WIFUSDT", "PEPEUSDT", "FLOKIUSDT", "BONKUSDT",
        "JUPUSDT", "PYTHUSDT", "STRKUSDT", "MANTAUSDT", "ALTUSDT", "PORTALUSDT", "AXLUSDT", "ETHFIUSDT", "ENAUSDT", "BBUSDT",
        "NOTUSDT", "IOUSDT", "ZKUSDT", "ZROUSDT", "BLUMUSDT", "DOGSUSDT", "CATIUSDT", "HMSTRUSDT", "EIGENUSDT", "SCRUSDT",
        "APEUSDT", "MANAUSDT", "SANDUSDT", "AXSUSDT", "GALAUSDT", "CHZUSDT", "ENJUSDT", "FLOWUSDT", "FTMUSDT", "ALGOUSDT",
        "VETUSDT", "THETAUSDT", "EGLDUSDT", "XTZUSDT", "EOSUSDT", "KAVAUSDT", "CRVUSDT", "SNXUSDT", "COMPUSDT", "MKRUSDT",
        "AAVEUSDT", "CAKEUSDT", "SUSHIUSDT", "1INCHUSDT", "ZRXUSDT", "BATUSDT", "ZILUSDT", "IOSTUSDT", "ONTUSDT", "QTUMUSDT",
        "ICXUSDT", "NEOUSDT", "DASHUSDT", "ZECUSDT", "XEMUSDT", "WAVESUSDT", "LRCUSDT", "YFIUSDT", "UMAUSDT", "BALUSDT",
        "RSRUSDT", "OCEANUSDT", "RENUSDT", "KNCUSDT", "STORJUSDT", "ANTUSDT", "LUNAUSDT", "LUNCUSDT", "USTCUSDT", "TRXUSDT",
        "XLMUSDT", "FILUSDT", "TRBUSDT", "RLCUSDT", "NEIROUSDT", "TURBOUSDT", "COWUSDT", "PNUTUSDT", "ACTUSDT", "GOATUSDT",
        "MOODENGUSDT", "HIPPOUSDT", "CHILLGUYUSDT", "USUALUSDT", "THEUSDT", "PENGUUSDT", "VIRTUALUSDT", "AI16ZUSDT", "FARTCOINUSDT",
        "SPXUSDT", "MELANIAUSDT", "TRUMPUSDT", "BOMEUSDT", "MEUSDT", "SONICUSDT", "BERAUSDT", "IPUSDT", "KAIAUSDT", "SPLUSDT",
        "PUFFERUSDT", "SCRTUSDT", "MBOXUSDT", "STGUSDT", "RDNTUSDT", "GMXUSDT", "JOEUSDT", "PERPUSDT", "SPELLUSDT", "MAGICUSDT",
        "SSVUSDT", "LDOUSDT", "FXSUSDT", "LQTYUSDT", "AGIXUSDT", "NMRUSDT", "BANDUSDT", "API3USDT", "C98USDT", "HOOKUSDT",
        "HIGHUSDT", "IDUSDT", "EDUUSDT", "CYBERUSDT", "MAVUSDT", "ARKMUSDT", "NFPUSDT", "XAIUSDT", "PIXELUSDT", "AEVOUSDT"
    ]
    
    symbols = list(dict.fromkeys(symbols))
    
    while True:
        print(f"--- Scanning {len(symbols)} coins for SMC Long Signals ---")
        for symbol in symbols:
            df = fetch_binance_klines(symbol)
            if df is not None and not df.empty:
                df = calculate_smc_indicators(df)
                last_row = df.iloc[-1]
                prev_row = df.iloc[-2]
                
                close_price = last_row['close']
                ema_val = last_row['EMA_9']
                vwap_val = last_row['VWAP']
                volume = last_row['volume']
                vol_sma = last_row['Vol_SMA20']
                
                # شروط إشارة SMC Long الاحترافية:
                # 1. السعر يخترق للأعلى فوق EMA 9 أو مستمر فوقه بعزم
                # 2. السعر فوق الـ VWAP (تدفق سيولة إيجابي)
                # 3. حجم تداول قوي (أعلى من المتوسط بـ 1.2 مرة على الأقل) لتأكيد الاختراق
                # 4. حدوث تقاطع صعودي للـ EMA 9 مع السعر في الشمعة الحالية أو السابقة
                
                is_price_above_vwap = close_price > vwap_val
                is_price_above_ema = close_price > ema_val
                is_volume_spike = volume > (vol_sma * 1.2) if not np.isnan(vol_sma) else True
                
                # تحقق تقاطع إيجابي (نقطة انطلاق الشراء - Long Entry)
                is_bullish_cross = (prev_row['close'] <= prev_row['EMA_9']) and (close_price > ema_val)
                
                # إطلاق التنبيه فقط إذا توافرت الشروط وبشكل خاص التقاطع مع السيولة
                if is_price_above_vwap and is_price_above_ema and (is_bullish_cross or is_volume_spike):
                    message = (
                        f"🔵 *SMC Long Signal Detected!*\n\n"
                        f"• العملة: `{symbol}`\n"
                        f"• السعر الحالي: `{close_price}`\n"
                        f"• مؤشر VWAP: `{vwap_val:.4f}`\n"
                        f"• مؤشر EMA 9: `{ema_val:.4f}`\n"
                        f"• الحالة: `تأكيد اختراق وعزم إيجابي للصعود 🚀`"
                    )
                    print(message)
                    send_telegram_message(message)
                
            time.sleep(1.5)
        time.sleep(300) # إعادة الفحص الكامل كل 5 دقائق

# تشغيل الفحص في الخلفية
def run_scanner_thread():
    thread = threading.Thread(target=scan_market, daemon=True)
    thread.start()

run_scanner_thread()
