import json
import os
import yfinance as yf
from datetime import datetime
import time
from typing import Dict, Any, Optional, Tuple
import codecs
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import numpy as np

def create_session() -> requests.Session:
    """재시도 로직과 적절한 헤더가 포함된 요청 세션을 생성합니다."""
    session = requests.Session()
    
    # 재시도 설정
    retry = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # 브라우저와 유사한 헤더 설정
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    })
    
    try:
        # Yahoo Finance 쿠키 획득
        session.get('https://fc.yahoo.com/')
        
        # Crumb 획득 시도
        crumb_response = session.get('https://query2.finance.yahoo.com/v1/test/getcrumb')
        if crumb_response.status_code == 200:
            session.headers.update({'X-Yahoo-Api-Crumb': crumb_response.text})
    except Exception as e:
        print(f"Warning: Failed to get Yahoo Finance crumb: {str(e)}")
    
    return session

def load_base_rates() -> Dict[str, float]:
    """base_rates.json 파일에서 통화 기본 환율 정보를 로드합니다."""
    base_rates_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 'example', 'base_rates.json')
    
    with open(base_rates_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['base_rates']

def get_ticker_data(symbol: str, session: requests.Session) -> Optional[Tuple[pd.DataFrame, Any]]:
    """지정된 심볼에 대한 티커 데이터를 가져옵니다."""
    for attempt in range(3):
        try:
            print(f"Fetching {symbol} (attempt {attempt + 1}/3)")
            ticker = yf.Ticker(symbol, session=session)
            hist = ticker.history(period="150d")
            
            if not hist.empty and len(hist) > 1:
                return hist, ticker
            
            print(f"No data available for {symbol} on attempt {attempt + 1}")
            time.sleep(2)
            
        except Exception as e:
            print(f"Error on attempt {attempt + 1} for {symbol}: {str(e)}")
            if attempt < 2:
                time.sleep(2)
    
    return None

def calculate_cross_rate(base_currency: str, quote_currency: str, session: requests.Session) -> Optional[pd.DataFrame]:
    """USD를 통한 크로스 환율을 계산합니다."""
    try:
        print(f"Calculating cross rate for {base_currency}/{quote_currency} via USD")
        
        # Base/USD 환율 조회
        base_usd_symbol = f"{base_currency}USD=X"
        base_usd_result = get_ticker_data(base_usd_symbol, session)
        
        if not base_usd_result:
            # USD/Base 시도
            base_usd_symbol = f"USD{base_currency}=X"
            base_usd_result = get_ticker_data(base_usd_symbol, session)
            if base_usd_result:
                base_hist, _ = base_usd_result
                base_hist['Close'] = 1 / base_hist['Close']
            else:
                print(f"Failed to get {base_currency}/USD rate")
                return None
        else:
            base_hist, _ = base_usd_result
        
        # USD/Quote 환율 조회
        usd_quote_symbol = f"USD{quote_currency}=X"
        usd_quote_result = get_ticker_data(usd_quote_symbol, session)
        
        if not usd_quote_result:
            # Quote/USD 시도
            usd_quote_symbol = f"{quote_currency}USD=X"
            usd_quote_result = get_ticker_data(usd_quote_symbol, session)
            if usd_quote_result:
                quote_hist, _ = usd_quote_result
                quote_hist['Close'] = 1 / quote_hist['Close']
            else:
                print(f"Failed to get USD/{quote_currency} rate")
                return None
        else:
            quote_hist, _ = usd_quote_result
        
        # 크로스 환율 계산
        cross_rates = pd.DataFrame()
        cross_rates['Close'] = base_hist['Close'] * quote_hist['Close']
        
        return cross_rates
    
    except Exception as e:
        print(f"Error calculating cross rate: {str(e)}")
        return None

def calculate_signals(hist: pd.DataFrame) -> Dict[str, str]:
    """기술적 지표를 계산하고 신호를 생성합니다."""
    try:
        # 이동평균 계산
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
            "signal_short": signal_short,
            "signal_long": signal_long
        }
    except Exception as e:
        print(f"Error calculating signals: {str(e)}")
        return {
            "signal_short": "신호 계산 실패",
            "signal_long": "신호 계산 실패"
        }

def get_forex_data(symbol: str, session: requests.Session) -> Dict[str, Any]:
    """환율 데이터를 가져옵니다."""
    try:
        base_currency, quote_currency = symbol.split('/')
        
        # 직접 환율 시도
        direct_symbol = f"{base_currency}{quote_currency}=X"
        print(f"\nTrying direct rate for {symbol} ({direct_symbol})")
        
        ticker_result = get_ticker_data(direct_symbol, session)
        hist = None
        
        if ticker_result:
            hist, _ = ticker_result
        else:
            # 크로스 환율 시도
            print(f"Direct rate failed for {symbol}, trying cross rate calculation")
            hist = calculate_cross_rate(base_currency, quote_currency, session)
        
        if hist is not None and not hist.empty and len(hist) > 1:
            last_close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change_percent = ((last_close - prev_close) / prev_close) * 100
            
            # 기술적 지표 및 신호 계산
            signals = calculate_signals(hist)
            
            return {
                "symbol": symbol,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "lastValue": round(float(last_close), 2),
                "changePercent": round(float(change_percent), 2),
                "signal_short": signals["signal_short"],
                "signal_long": signals["signal_long"]
            }
        else:
            raise ValueError(f"No data available for {symbol}")
        
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
    # 세션 생성
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