from binance.client import Client
from dotenv import load_dotenv
import os

# 정확한 경로로 .env 불러오기
from pathlib import Path
from dotenv import load_dotenv

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# 환경변수에서 API 키 불러오기
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

# 바이낸스 클라이언트 생성
client = Client(api_key, api_secret)

# 현재 BTC 가격 가져오기
try:
    ticker = client.get_symbol_ticker(symbol="BTCUSDT")
    print("📊 Ticker 전체:", ticker)
    print("💰 현재 BTC/USDT 가격:", ticker["price"])
except Exception as e:
    print("🚨 오류 발생:", e)