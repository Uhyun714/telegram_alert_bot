import ccxt
import pandas as pd
import numpy as np
import ta
import matplotlib.pyplot as plt

# 1. 바이낸스 15분봉 데이터 불러오기
exchange = ccxt.binance()
symbol = 'BTC/USDT'
timeframe = '15m'
limit = 1000

ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)
df['date'] = df.index.date

# 2. 지표 계산
df['ema21'] = ta.trend.ema_indicator(df['close'], window=21)
df['ema55'] = ta.trend.ema_indicator(df['close'], window=55)
df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

# 3. 캔들 특성 계산
df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
df['range'] = df['high'] - df['low']

# 4. 진입 조건 완화
df['long_entry'] = (
    (df['close'] < df['open']) &
    (df['lower_wick'] / df['range'] > 0.2) &
    (df['rsi'] < 50) &
    (df['ema21'] > df['ema55'])
)

df['short_entry'] = (
    (df['close'] > df['open']) &
    (df['upper_wick'] / df['range'] > 0.2) &
    (df['rsi'] > 50) &
    (df['ema21'] < df['ema55'])
)

# 5. 익절/손절 조건
df['future_close'] = df['close'].shift(-1)
df['long_tp'] = df['close'] * 1.012
df['long_sl'] = df['close'] * 0.991
df['short_tp'] = df['close'] * 0.988
df['short_sl'] = df['close'] * 1.009

# 6. 하루 수익률이 1% 넘으면 그날 이후 매매 금지
daily_returns = {}
filtered_trades = []

for idx, row in df.iterrows():
    date = row['date']
    if date not in daily_returns:
        daily_returns[date] = 0

    if daily_returns[date] >= 1:
        continue

    # 수익률 계산
    if row['long_entry']:
        entry = row['close']
        exit_price = row['future_close']
        if pd.isna(exit_price): continue
        pnl = (
            (row['long_tp'] - entry) / entry * 100
            if exit_price >= row['long_tp']
            else (row['long_sl'] - entry) / entry * 100
            if exit_price <= row['long_sl']
            else (exit_price - entry) / entry * 100
        )
    elif row['short_entry']:
        entry = row['close']
        exit_price = row['future_close']
        if pd.isna(exit_price): continue
        pnl = (
            (entry - row['short_tp']) / entry * 100
            if exit_price <= row['short_tp']
            else (entry - row['short_sl']) / entry * 100
            if exit_price >= row['short_sl']
            else (entry - exit_price) / entry * 100
        )
    else:
        continue

    daily_returns[date] += pnl
    filtered_trades.append({'date': date, 'pnl': pnl, 'timestamp': idx})

# 7. 누적 수익 계산
filtered_df = pd.DataFrame(filtered_trades)
filtered_df.sort_values(by='timestamp', inplace=True)
filtered_df['cumulative_return'] = (1 + filtered_df['pnl'] / 100).cumprod() * 100

# 8. 시각화: 자산곡선
plt.figure(figsize=(12, 5))
plt.plot(filtered_df['timestamp'], filtered_df['cumulative_return'], label='Cumulative Return', linewidth=2)
plt.title('자산 곡선 (누적 수익률)')
plt.xlabel('Date')
plt.ylabel('Equity (초기자산=100)')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# 9. 시각화: 수익률 분포
plt.figure(figsize=(8, 5))
plt.hist(filtered_df['pnl'], bins=20, edgecolor='black', alpha=0.7)
plt.axvline(filtered_df['pnl'].mean(), color='red', linestyle='--', label=f"평균 수익률: {filtered_df['pnl'].mean():.2f}%")
plt.title('수익률 분포 히스토그램')
plt.xlabel('수익률 (%)')
plt.ylabel('거래 수')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# 10. 콘솔 출력 요약
print("📊 전략 요약")
print(f"총 거래 수: {len(filtered_df)}")
print(f"평균 수익률: {filtered_df['pnl'].mean():.2f}%")
print(f"누적 수익률: {filtered_df['pnl'].sum():.2f}%")
print(f"승률: {(filtered_df['pnl'] > 0).mean() * 100:.1f}%")