import ccxt
import pandas as pd
import numpy as np
import ta

# 1. 바이낸스에서 15분봉 데이터 불러오기
exchange = ccxt.binance()
symbol = 'BTC/USDT'
timeframe = '15m'
limit = 1000

ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# 2. 지표 계산 (EMA, RSI)
df['ema21'] = ta.trend.ema_indicator(df['close'], window=21)
df['ema55'] = ta.trend.ema_indicator(df['close'], window=55)
df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

# 3. 캔들 특성 계산
df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
df['range'] = df['high'] - df['low']

# 4. 진입 조건
df['long_entry'] = (
    (df['close'] < df['open']) &
    (df['lower_wick'] / df['range'] > 0.25) &
    (df['rsi'] < 45) &
    (df['ema21'] > df['ema55'])
)

df['short_entry'] = (
    (df['close'] > df['open']) &
    (df['upper_wick'] / df['range'] > 0.25) &
    (df['rsi'] > 55) &
    (df['ema21'] < df['ema55'])
)

# 5. 익절/손절 조건
df['future_close'] = df['close'].shift(-1)
df['long_tp'] = df['close'] * 1.012
df['long_sl'] = df['close'] * 0.991
df['short_tp'] = df['close'] * 0.988
df['short_sl'] = df['close'] * 1.009

# 6. 수익률 계산
long_returns = []
short_returns = []

for idx, row in df.iterrows():
    if row['long_entry']:
        exit_price = row['future_close']
        if exit_price >= row['long_tp']:
            pnl = (row['long_tp'] - row['close']) / row['close'] * 100
        elif exit_price <= row['long_sl']:
            pnl = (row['long_sl'] - row['close']) / row['close'] * 100
        else:
            pnl = (exit_price - row['close']) / row['close'] * 100
        long_returns.append(pnl)
    elif row['short_entry']:
        exit_price = row['future_close']
        if exit_price <= row['short_tp']:
            pnl = (row['close'] - row['short_tp']) / row['close'] * 100
        elif exit_price >= row['short_sl']:
            pnl = (row['close'] - row['short_sl']) / row['close'] * 100
        else:
            pnl = (row['close'] - exit_price) / row['close'] * 100
        short_returns.append(pnl)

# 7. 결과 출력
print("📊 바이낸스 전략 백테스트 결과")
print(f"롱 진입 수: {len(long_returns)}회 | 누적 수익률: {sum(long_returns):.2f}%")
print(f"숏 진입 수: {len(short_returns)}회 | 누적 수익률: {sum(short_returns):.2f}%")
print(f"총 누적 수익률: {sum(long_returns) + sum(short_returns):.2f}%")