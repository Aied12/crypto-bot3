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
    return "Crypto SMC Strategy Bot is Running Live 24/7! 🚀"

@app.route('/test-telegram')
def test_telegram():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    
    if not token or not chat_id:
        return "❌ خطأ: متغيرات البيئة غير موجودة."

    message = "🧪 *اختبار ناجح!*\nبوت استراتيجية SMC المتكامل يعمل بكفاءة تامة 🚀"
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

# جلب البيانات من بينانس (فريم الساعة 1h)
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

# حساب مؤشرات الاستراتيجية بدقة مطابقة لـ Pine Script
def calculate_strategy_indicators(df):
    if df is None or len(df) < 50:
        return None

    # ATR (14)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = true_range.rolling(window=14).mean()

    # RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Volume MA (20) & Multiplier
    df['Vol_MA'] = df['volume'].rolling(window=20).mean()

    # Swing Highs & Lows (Length = 5)
    df['pHi'] = df['high'][(df['high'] == df['high'].rolling(11, center=True).max())]
    df['pLo'] = df['low'][(df['low'] == df['low'].rolling(11, center=True).min())]

    return df

# محرك فحص الشروط وإعطاء سعر الدخول ووقف الخسارة
def check_smc_setup(df):
    if df is None or len(df) < 30:
        return False, 0, 0, 0

    last_row = df.iloc[-1]
    close_price = last_row['close']
    atr = last_row['ATR']
    rsi = last_row['RSI']

    # 1. فلتر الـ RSI (الوضع الصاعد: أقل من 65)
    if not (rsi < 65):
        return False, 0, 0, 0

    # 2. فلتر حجم التداول (Volume Filter > Vol_MA * 1.1)
    if last_row['volume'] <= (last_row['Vol_MA'] * 1.1):
        return False, 0, 0, 0

    # 3. فحص كسر الهيكل (BOS) بناءً على آخر قمة سوينغ
    # البحث عن آخر قمة في آخر 20 شمعة
    recent_highs = df['high'].iloc[-25:-2]
    last_swing_high = recent_highs.max()

    # شرط كسر القمة بإغلاق السعر فوقها
    bos_bullish = close_price > last_swing_high

    # 4. تصفية السيولة (Liquidity Sweep: السعر كسر قاع سابق ثم صعد)
    recent_low = df['low'].iloc[-25:-2].min()
    liquidity_sweep = last_row['low'] < recent_low and close_price > recent_low

    if bos_bullish and liquidity_sweep:
        # البحث عن شمعة الطلب (Order Block) السلبية الأخيرة ضمن آخر 10 شمعات
        ob_bottom = close_price
        for i in range(1, 11):
            if df['close'].iloc[-i] < df['open'].iloc[-i]:
                ob_bottom = df['low'].iloc[-i]
                break
        
        # حساب وقف الخسارة تماماً مثل الكود: قاع منطقة الطلب مطروحاً منه (0.2 * ATR)
        sl_price = ob_bottom - (atr * 0.2)
        entry_price = close_price
        
        return True, entry_price, sl_price, ob_bottom

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

# فحص الـ 200 عملة آلياً 24/7
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
        print(f"--- Scanning {len(symbols)} coins for strategy execution ---")
        for symbol in symbols:
            df = fetch_binance_klines(symbol)
            df = calculate_strategy_indicators(df)
            is_match, entry, sl, ob = check_smc_setup(df)
            
            if is_match:
                # حساب الهدف بناءً على نسبة المخاطرة للعائد (RR = 1.5)
                risk = entry - sl
                tp = entry + (risk * 1.5)
                
                message = (
                    f"🟢 *إشارة دخول صفقة شراء (SMC Long)*\n\n"
                    f"• العملة: `{symbol}`\n"
                    f"• سعر الدخول: `{entry:.4f}`\n"
                    f"• وقف الخسارة (SL): `{sl:.4f}`\n"
                    f"• الهدف المقترح (TP): `{tp:.4f}`\n"
                    f"• الحالة: `تحقق كسر الهيكل وتأكيد منطقة الطلب 🚀`"
                )
                print(message)
                send_telegram_message(message)
                
            time.sleep(1.5)
        time.sleep(300) # إعادة الفحص الكامل كل 5 دقائق

def run_scanner_thread():
    thread = threading.Thread(target=scan_market, daemon=True)
    thread.start()

run_scanner_thread()
