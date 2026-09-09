import os
import time
import threading
import requests
import pandas as pd
import numpy as np
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Crypto SMC Scanner Bot is Running Live 24/7! 🚀"

@app.route('/test-telegram')
def test_telegram():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    
    if not token or not chat_id:
        return "❌ خطأ: متغيرات البيئة غير موجودة."

    message = "🧪 *اختبار ناجح!*\nبوت فحص SMC يعمل بكفاءة تامة 🚀"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return "✅ تم إرسال رسالة الاختبار بنجاح!"
        else:
            return f"❌ خطأ من تيليجرام: {response.text}"
    except Exception as e:
        return f"❌ خطأ في الاتصال: {e}"

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

# دالة احتساب شروط الـ SMC (كسر القمة الأخيرة + تدفق السيولة والـ VWAP)
def check_smc_long(df):
    if df is None or len(df) < 20:
        return False, 0, 0, 0

    # مؤشر VWAP
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    
    # متوسط الحركة الأسي EMA 9
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()

    # تحديد القمة الأخيرة لآخر 10 شمعات (باستثناء الشمعة الحالية) لتأكيد كسر الهيكل (MSB)
    recent_high = df['high'].iloc[-11:-1].max()
    
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    close_price = last_row['close']
    vwap_val = last_row['VWAP']
    ema_val = last_row['EMA_9']
    
    # شروط الـ SMC Long الصارمة:
    # 1. السعر أغلق أعلى من قمة الشمعات السابقة (كسر هيكل صاعد / MSB)
    is_break_structure = close_price > recent_high
    
    # 2. السعر فوق الـ VWAP وفوق الـ EMA 9 (تأكيد الاتجاه)
    is_above_vwap = close_price > vwap_val
    is_above_ema = close_price > ema_val
    
    # 3. شمعة خضراء قوية (الإغلاق أعلى من الافتتاح)
    is_bullish_candle = close_price > last_row['open']

    if is_break_structure and is_above_vwap and is_above_ema and is_bullish_candle:
        return True, close_price, vwap_val, ema_val

    return False, 0, 0, 0

def send_telegram_message(message):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# فحص الـ 200 عملة بحثاً عن فرص الـ SMC Long الحقيقية
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
        print(f"--- Scanning {len(symbols)} coins for strict SMC Long ---")
        for symbol in symbols:
            df = fetch_binance_klines(symbol)
            is_match, close_price, vwap_val, ema_val = check_smc_long(df)
            
            if is_match:
                message = (
                    f"🟢 *تنبيه SMC Long مؤكد!*\n\n"
                    f"• العملة: `{symbol}`\n"
                    f"• السعر الحالي: `{close_price}`\n"
                    f"• مؤشر VWAP: `{vwap_val:.4f}`\n"
                    f"• مؤشر EMA 9: `{ema_val:.4f}`\n"
                    f"• الحالة: `تم رصد كسر هيكل صاعد (MSB) وعزم إيجابي 🚀`"
                )
                print(message)
                send_telegram_message(message)
                
            time.sleep(1.5)
        time.sleep(300) # إعادة الفحص الكامل لكل العملات كل 5 دقائق

def run_scanner_thread():
    thread = threading.Thread(target=scan_market, daemon=True)
    thread.start()

run_scanner_thread()
