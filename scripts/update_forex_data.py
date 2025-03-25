import json
import os
import yfinance as yf
from datetime import datetime
import time
from typing import Dict, Any, Optional
import codecs
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session():
    """재시도 로직이 포함된 요청 세션을 생성합니다."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def load_base_rates() -> Dict[str, float]:
    """base_rates.json 파일에서 통화 기본 환율 정보를 로드합니다."""
    base_rates_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 'example', 'base_rates.json')
    
    with open(base_rates_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['base_rates']

def get_forex_data(symbol: str, session: requests.Session) -> Dict[str, Any]:
    """환율 데이터를 가져옵니다."""
    try:
        # 심볼 형식을 yfinance 형식으로 변환
        yf_symbol = symbol.replace('/', '') + '=X'
        
        print(f"Fetching data for {symbol} ({yf_symbol})")
        
        # yfinance Ticker 객체 생성 시 세션 전달
        ticker = yf.Ticker(yf_symbol, session=session)
        
        # 히스토리 데이터 가져오기 (여러 번 시도)
        for attempt in range(3):
            try:
                hist = ticker.history(period="150d")
                if not hist.empty and len(hist) > 1:
                    break
                print(f"Attempt {attempt + 1}: No data received, retrying...")
                time.sleep(2)
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < 2:  # 마지막 시도가 아니면 계속
                    time.sleep(2)
                    continue
                raise
        
        if hist.empty or len(hist) <= 1:
            raise ValueError(f"No sufficient data available for {symbol}")
        
        # 데이터 계산
        last_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        change_percent = ((last_close - prev_close) / prev_close) * 100
        
        # 기술적 지표 계산
        ma5 = hist['Close'].rolling(window=min(5, len(hist))).mean().iloc[-1]
        ma20 = hist['Close'].rolling(window=min(20, len(hist))).mean().iloc[-1]
        ma60 = hist['Close'].rolling(window=min(60, len(hist))).mean().iloc[-1]
        
        # RSI 계산
        delta = hist['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs.iloc[-1])) if loss.iloc[-1] != 0 else 50
        
        # MACD 계산
        if len(hist) >= 26:
            ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
            ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
            macd = (ema12 - ema26).iloc[-1]
        else:
            macd = 0.0
        
        # 신호 결정
        if rsi > 70 and ma5 > ma20:
            signal_short = "큰 하락 가능"
        elif rsi < 30 and ma5 < ma20:
            signal_short = "큰 상승 가능"
        elif ma5 > ma20:
            signal_short = "하락 가능"
        elif ma5 < ma20:
            signal_short = "상승 가능"
        else:
            signal_short = "횡보"
        
        if macd > 0 and ma20 > ma60:
            signal_long = "강한 상승 가능"
        elif macd < 0 and ma20 < ma60:
            signal_long = "강한 하락 가능"
        elif macd > 0:
            signal_long = "상승 가능"
        elif macd < 0:
            signal_long = "하락 가능"
        else:
            signal_long = "횡보"
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "lastValue": round(float(last_close), 2),
            "changePercent": round(float(change_percent), 2),
            "signal_short": signal_short,
            "signal_long": signal_long
        }
    
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "lastValue": 0.0,
            "changePercent": 0.0,
            "signal_short": "데이터 없음",
            "signal_long": "데이터 없음"
        }

def save_forex_data(symbol: str, data: Dict[str, Any]) -> None:
    """통화 데이터를 JSON 파일로 저장합니다."""
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    filename = symbol.replace('/', '_') + '.json'
    file_path = os.path.join(output_dir, filename)
    
    with codecs.open(file_path, 'w', encoding='utf-8-sig') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"데이터가 저장되었습니다: {file_path}")

def main():
    # 재시도 로직이 포함된 세션 생성
    session = create_session()
    
    # 기본 환율 정보 로드
    base_rates = load_base_rates()
    
    # 각 통화쌍에 대해 데이터 수집 및 저장
    for symbol in base_rates.keys():
        print(f"\nProcessing {symbol}...")
        data = get_forex_data(symbol, session)
        
        if data:
            save_forex_data(symbol, data)
        
        # API 호출 제한을 피하기 위한 잠시 대기
        time.sleep(2)

if __name__ == "__main__":
    main()