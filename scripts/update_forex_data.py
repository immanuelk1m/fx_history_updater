import json
import os
import yfinance as yf
from datetime import datetime
import time
from typing import Dict, Any, Optional, Tuple
import codecs

def load_base_rates() -> Dict[str, float]:
    """base_rates.json 파일에서 통화 기본 환율 정보를 로드합니다."""
    base_rates_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 'example', 'base_rates.json')
    
    with open(base_rates_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['base_rates']

def get_ticker_data(symbol: str, retries: int = 3, delay: int = 2) -> Optional[yf.Ticker]:
    """지정된 재시도 횟수만큼 티커 데이터를 가져오려고 시도합니다."""
    for attempt in range(retries):
        try:
            ticker = yf.Ticker(symbol)
            # 유효성 검사를 위해 기본 정보 가져오기
            info = ticker.info
            if info:
                return ticker
        except Exception as e:
            print(f"Attempt {attempt + 1}/{retries} failed for {symbol}: {str(e)}")
            if attempt < retries - 1:
                time.sleep(delay)
    return None

def calculate_cross_rate(base_currency: str, quote_currency: str) -> Optional[Tuple[float, float, yf.Ticker]]:
    """USD를 통한 크로스 환율을 계산합니다."""
    if base_currency == "USD":
        symbol = f"{quote_currency}USD=X"
        ticker = get_ticker_data(symbol)
        if ticker:
            hist = ticker.history(period="150d")
            if not hist.empty:
                return 1 / hist['Close'].iloc[-1], 1 / hist['Close'].iloc[-2], ticker
    elif quote_currency == "USD":
        symbol = f"{base_currency}USD=X"
        ticker = get_ticker_data(symbol)
        if ticker:
            hist = ticker.history(period="150d")
            if not hist.empty:
                return hist['Close'].iloc[-1], hist['Close'].iloc[-2], ticker
    else:
        # Base/USD와 Quote/USD를 가져와서 크로스 환율 계산
        base_usd = f"{base_currency}USD=X"
        quote_usd = f"{quote_currency}USD=X"
        
        base_ticker = get_ticker_data(base_usd)
        quote_ticker = get_ticker_data(quote_usd)
        
        if base_ticker and quote_ticker:
            base_hist = base_ticker.history(period="150d")
            quote_hist = quote_ticker.history(period="150d")
            
            if not base_hist.empty and not quote_hist.empty:
                base_rate = base_hist['Close'].iloc[-1]
                base_rate_prev = base_hist['Close'].iloc[-2]
                quote_rate = quote_hist['Close'].iloc[-1]
                quote_rate_prev = quote_hist['Close'].iloc[-2]
                
                cross_rate = base_rate / quote_rate
                cross_rate_prev = base_rate_prev / quote_rate_prev
                return cross_rate, cross_rate_prev, base_ticker
    
    return None

def get_forex_data(symbol: str) -> Dict[str, Any]:
    """yfinance를 사용하여 통화 데이터를 가져옵니다."""
    try:
        # 심볼 파싱 (USD/KRW -> USD, KRW)
        base_currency, quote_currency = symbol.split('/')
        
        # 직접 환율 시도
        direct_symbol = f"{base_currency}{quote_currency}=X"
        ticker = get_ticker_data(direct_symbol)
        hist = None
        
        if ticker:
            hist = ticker.history(period="150d")
        
        # 직접 환율이 실패하면 크로스 환율 시도
        if hist is None or hist.empty:
            print(f"직접 환율 데이터를 찾을 수 없어 크로스 환율을 시도합니다: {symbol}")
            cross_rate_result = calculate_cross_rate(base_currency, quote_currency)
            
            if cross_rate_result:
                last_close, prev_close, ticker = cross_rate_result
                change_percent = ((last_close - prev_close) / prev_close) * 100
                
                # 크로스 환율로 히스토리 데이터 다시 계산
                hist = ticker.history(period="150d")
            else:
                raise ValueError(f"크로스 환율 계산도 실패했습니다: {symbol}")
        else:
            last_close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change_percent = ((last_close - prev_close) / prev_close) * 100
        
        # 기술적 지표 계산
        ma5 = hist['Close'].rolling(window=min(5, len(hist))).mean().iloc[-1]
        ma20 = hist['Close'].rolling(window=min(20, len(hist))).mean().iloc[-1]
        ma60 = hist['Close'].rolling(window=min(60, len(hist))).mean().iloc[-1]
        
        # 변동성
        vol_window = min(14, len(hist))
        volatility = hist['Close'].rolling(window=vol_window).std().iloc[-1]
        
        # RSI 계산
        rsi_window = min(14, len(hist) - 1)
        if rsi_window > 0:
            delta = hist['Close'].diff().dropna()
            gain = delta.where(delta > 0, 0).rolling(window=rsi_window).mean().dropna()
            loss = -delta.where(delta < 0, 0).rolling(window=rsi_window).mean().dropna()
            
            if not loss.empty and not gain.empty and loss.iloc[-1] != 0:
                rs = gain.iloc[-1] / loss.iloc[-1]
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 50
        else:
            rsi = 50
        
        # MACD
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
    
    with codecs.open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"데이터가 저장되었습니다: {file_path}")

def main():
    base_rates = load_base_rates()
    
    for symbol in base_rates.keys():
        print(f"Processing {symbol}...")
        data = get_forex_data(symbol)
        
        if data:
            save_forex_data(symbol, data)
        
        time.sleep(1)

if __name__ == "__main__":
    main()