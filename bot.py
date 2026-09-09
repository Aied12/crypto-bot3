def scan_market():
    # قائمة العملات التي يتم فحصها
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    print("--- Starting Market Scan ---")
    
    for symbol in symbols:
        df = fetch_binance_klines(symbol)
        if df is not None and not df.empty:
            df = calculate_indicators(df)
            last_row = df.iloc[-1]
            
            message = (
                f"🚨 **تنبيه حركة السوق ({symbol})**\n"
                f"• السعر الحالي: `{last_row['close']}`\n"
                f"• قيمة الـ VWAP: `{last_row['VWAP']:.2f}`\n"
                f"• مؤشر EMA 9: `{last_row['EMA_9']:.2f}`"
            )
            print(message)
            send_telegram_message(message)
            
        time.sleep(1)
