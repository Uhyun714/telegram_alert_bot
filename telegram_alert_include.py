import time
import ccxt
import pandas as pd
import ta
import requests
from datetime import datetime

# ====== 1. 텔레그램 설정 ======
TOKEN = ''
CHAT_ID = ''

def send_telegram_alert(message):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {'chat_id': CHAT_ID, 'text': message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")

# ====== 2. 바이낸스 설정 ======
exchange = ccxt.binance()
symbol = 'BTC/USDT'
timeframe = '15m'
limit = 100

# ====== 3. 데이터 수집 함수 ======
def fetch_data():
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# ====== 4. 전략 조건 계산 함수 ======
def check_trade_signal(df):
    df['ema21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['ema55'] = ta.trend.ema_indicator(df['close'], window=55)
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

    df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
    df['range'] = df['high'] - df['low']

    last = df.iloc[-1]

    long_entry = (
        (last['close'] < last['open']) and
        (last['lower_wick'] / last['range'] > 0.2) and
        (last['rsi'] < 50) and
        (last['ema21'] > last['ema55'])
    )

    short_entry = (
        (last['close'] > last['open']) and
        (last['upper_wick'] / last['range'] > 0.2) and
        (last['rsi'] > 50) and
        (last['ema21'] < last['ema55'])
    )

    if long_entry:
        return 'long', last['close']
    elif short_entry:
        return 'short', last['close']
    else:
        return None, None

# ====== 5. 실시간 감시 루프 ======
last_signal_time = None
checked_candle = None

print("📡 실시간 전략 감시 시작...")

while True:
    try:
        df = fetch_data()
        latest_time = df.index[-1]

        # 새로운 캔들일 때만 체크
        if checked_candle == latest_time:
            time.sleep(10)
            continue

        checked_candle = latest_time
        signal, price = check_trade_signal(df)

        if signal:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            direction = "📈 LONG" if signal == 'long' else "📉 SHORT"
            alert_msg = f"""
{direction} 진입 조건 발생!
🕒 {timestamp}
💰 가격: {price:.2f} USDT
📊 코인: {symbol}
"""
            send_telegram_alert(alert_msg.strip())
            print(f"🔔 {direction} 알림 전송됨: {price:.2f} USDT")

        else:
            print(f"{datetime.now().strftime('%H:%M:%S')} - 조건 없음")

        time.sleep(60)  # 1분마다 확인 (15분봉 주기 감안)

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        time.sleep(60)