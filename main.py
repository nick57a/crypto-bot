import os
import time
import threading
import ccxt
import pandas as pd
import pandas_ta as ta
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "AI Trading Bot Is Running 24/7!"

# ⬇️ ဒီနေရာမှာ အစ်ကို့ရဲ့ Token နဲ့ Chat ID ကို ပြောင်းထည့်ပေးပါ ⬇️
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "@YOUR_CHANNEL_USERNAME"
# ⬆️ အပေါ်က နေရာလေးကို ပြောင်းရန် ⬆️

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Error:", e)

def fetch_data(symbol, timeframe):
    exchange = ccxt.binance()
    bars = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    df.ta.rsi(length=14, append=True)
    df.ta.macd(append=True)
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.ema(length=200, append=True)
    
    return df.iloc[-1]

def calculate_confidence(symbol):
    data_15m = fetch_data(symbol, "15m")
    data_1h = fetch_data(symbol, "1h")
    
    long_score = 0
    short_score = 0
    
    if data_15m['RSI_14'] < 35: long_score += 25
    if data_15m['RSI_14'] > 65: short_score += 25
        
    if data_15m['close'] <= data_15m['BBL_20_2.0']: long_score += 25
    if data_15m['close'] >= data_15m['BBU_20_2.0']: short_score += 25
        
    if data_15m['close'] > data_15m['EMA_200'] and data_15m['EMA_20'] > data_15m['EMA_50']: long_score += 25
    if data_15m['close'] < data_15m['EMA_200'] and data_15m['EMA_20'] < data_15m['EMA_50']: short_score += 25
        
    if data_1h['close'] > data_1h['EMA_50']: long_score += 25
    if data_1h['close'] < data_1h['EMA_50']: short_score += 25

    if long_score >= 70: return "LONG", long_score, data_15m
    elif short_score >= 70: return "SHORT", short_score, data_15m
    else: return "NO_POSITION", max(long_score, short_score), data_15m

def bot_loop():
    print("Bot Loop Started...")
    symbol = "BTC/USDT"
    while True:
        try:
            direction, score, data = calculate_confidence(symbol)
            current_price = data['close']
            
            if direction != "NO_POSITION":
                entry = current_price
                if direction == "LONG":
                    tp = entry * 1.02
                    sl = entry * 0.99
                else:
                    tp = entry * 0.98
                    sl = entry * 1.01
                
                msg = f"🚀 **AI HIGH CONFIDENCE SIGNAL** 🚀\n\n🪙 **Asset:** {symbol}\n📊 **Direction:** {direction}\n🎯 **Confidence:** {score}%\n💵 **Entry Price:** ${entry:,.2f}\n🎯 **Take Profit (TP):** ${tp:,.2f}\n🛑 **Stop Loss (SL):** ${sl:,.2f}\n📉 **Current RSI:** {data['RSI_14']:.2f}"
                send_telegram_message(msg)
            else:
                msg = f"⏱ **Market Update (10 Mins)**\n\n🪙 **Asset:** {symbol}\n⚠️ **Status:** ပြည့်စုံသော အချက်ပြချက် မရှိသေးပါ (No Position)\n📊 **Highest Confidence:** {score}%\n💵 **Current Price:** ${current_price:,.2f}\n💡 *မှတ်ချက်: စနစ်မှ 70% အထက်ကိုသာ Signal ထုတ်ပေးပါသည်။*"
                send_telegram_message(msg)
        except Exception as e:
            print("Loop Error:", e)
        time.sleep(600)

if __name__ == "__main__":
    threading.Thread(target=bot_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
