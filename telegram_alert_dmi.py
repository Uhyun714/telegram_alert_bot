import os
import time
import signal
import requests
import pandas as pd
import ccxt
import ta
from datetime import datetime

# === 환경변수에서 정보 불러오기 ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

# === Binance API 연결 ===
binance = ccxt.binance({
    'apiKey': BINANCE_API_KEY,
    'secret': BINANCE_API_SECRET,
    'enableRateLimit': True
})

# === 텔레그램 메시지 전송 함수 ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"[텔레그램 전송 실패] {e}")

# === 데이터 가져오기 (5분봉 기준) ===
def fetch_data(symbol, timeframe='5m', limit=100):
    ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# === 분석 함수 (DMI 교차 + EMA 크로스) ===
def analyze(df):
    dmi = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14)
    plus_di = dmi.adx_pos()
    minus_di = dmi.adx_neg()
    ema20 = df['close'].ewm(span=20).mean()
    ema40 = df['close'].ewm(span=40).mean()

    last_time = df['timestamp'].iloc[-1].strftime('%Y-%m-%d %H:%M')
    last_price = df['close'].iloc[-1]

    signal = None

    # DMI 교차 진입 조건
    if plus_di.iloc[-2] < minus_di.iloc[-2] and plus_di.iloc[-1] > minus_di.iloc[-1]:
        signal = f"[{last_time}] 📈 롱 진입 (DMI 교차)\n가격: {last_price:.2f}"
    elif plus_di.iloc[-2] > minus_di.iloc[-2] and plus_di.iloc[-1] < minus_di.iloc[-1]:
        signal = f"[{last_time}] 📉 숏 진입 (DMI 교차)\n가격: {last_price:.2f}"

    # EMA 교차 시각화
    elif ema20.iloc[-2] < ema40.iloc[-2] and ema20.iloc[-1] > ema40.iloc[-1]:
        signal = f"[{last_time}] 📘 EMA 골든크로스\n가격: {last_price:.2f}"
    elif ema20.iloc[-2] > ema40.iloc[-2] and ema20.iloc[-1] < ema40.iloc[-1]:
        signal = f"[{last_time}] 📕 EMA 데드크로스\n가격: {last_price:.2f}"

    return signal

# === 중복 방지 딕셔너리 ===
sent_signals = {}

# === 코인별 감시 ===
def check_and_alert(symbol):
    df = fetch_data(symbol)
    signal = analyze(df)
    if signal and sent_signals.get(symbol) != signal:
        send_telegram_message(f"{symbol}\n{signal}")
        sent_signals[symbol] = signal

# === 종료 감지 함수 ===
def handle_exit(signum, frame):
    print("시그널 감지됨:", signum)
    send_telegram_message("🛑 감시 종료됨 (스크립트 종료)")
    exit(0)

signal.signal(signal.SIGINT, handle_exit)   # Ctrl + C
signal.signal(signal.SIGTERM, handle_exit)  # kill 명령어 등

# === 메인 루프 ===
if __name__ == "__main__":
    try:
        send_telegram_message("✅ 감시 시작됨 (5분봉 기준)")
        print("[감시 시작] 실시간 분석을 시작합니다.")
        last_heartbeat = time.time()

        while True:
            for symbol in ["BTC/USDT", "ETH/USDT"]:
                check_and_alert(symbol)

            # 1시간마다 감시 중 알림
            if time.time() - last_heartbeat > 3600:
                send_telegram_message("🔄 감시 중... (1시간 경과)")
                last_heartbeat = time.time()

            time.sleep(60)

    except Exception as e:
        send_telegram_message(f"⚠️ 오류 발생: {e}")
        print(f"[오류] {e}")
send_telegram_message("🚀 [테스트] 텔레그램 알림이 정상 발생했습니다!")

