import json
import os
import yfinance as yf
from datetime import datetime
import time
from typing import Dict, Any
import codecs

def load_base_rates() -> Dict[str, float]:
    """base_rates.json 파일에서 통화 기본 환율 정보를 로드합니다."""
    base_rates_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 'example', 'base_rates.json')
    
    with open(base_rates_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['base_rates']

def get_forex_data(symbol: str) -> Dict[str, Any]:
    """yfinance를 사용하여 통화 데이터를 가져옵니다."""
    # 심볼 형식을 yfinance 형식으로 변환 (USD/KRW -> USDKRW=X)
    yf_symbol = symbol.replace('/', '') + '=X'
    
    try:
        ticker = yf.Ticker(yf_symbol)
        
        # 히스토리 데이터 가져오기
        hist = ticker.history(period="150d")
        
        if hist.empty:
            raise ValueError(f"No data found for {symbol}")
        
        # 최신 데이터 가져오기 (안전하게 가져오기)
        if len(hist) > 1:
            last_close = hist['Close'].iloc[-1]
            
            # 마지막 값과 그 전 값 확인
            if len(hist) > 1:
                prev_close = hist['Close'].iloc[-2]
                change_percent = ((last_close - prev_close) / prev_close) * 100
            else:
                change_percent = 0.0
            
            # 기술적 지표 계산 (충분한 데이터가 있을 경우)
            # - 단순 이동평균 (Simple Moving Average)
            ma5 = hist['Close'].rolling(window=min(5, len(hist))).mean().iloc[-1]
            ma20 = hist['Close'].rolling(window=min(20, len(hist))).mean().iloc[-1]
            ma60 = hist['Close'].rolling(window=min(60, len(hist))).mean().iloc[-1]
            
            # - 변동성 (Volatility): 최근 14일 종가의 표준편차
            vol_window = min(14, len(hist))
            volatility = hist['Close'].rolling(window=vol_window).std().iloc[-1]
            
            # - RSI (Relative Strength Index) 계산
            rsi_window = min(14, len(hist) - 1)
            if rsi_window > 0:
                delta = hist['Close'].diff().dropna()
                gain = delta.where(delta > 0, 0).rolling(window=rsi_window).mean().dropna()
                loss = -delta.where(delta < 0, 0).rolling(window=rsi_window).mean().dropna()
                
                if not loss.empty and not gain.empty and loss.iloc[-1] != 0:
                    rs = gain.iloc[-1] / loss.iloc[-1]
                    rsi = 100 - (100 / (1 + rs))
                else:
                    rsi = 50  # 기본값
            else:
                rsi = 50  # 기본값
            
            # - MACD (Moving Average Convergence Divergence)
            if len(hist) >= 26:
                ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
                ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
                macd = (ema12 - ema26).iloc[-1]
            else:
                macd = 0.0
            
            # 추세 신호 결정
            # 단기 신호 (RSI + 단기 이동평균선 기반)
            if rsi > 70 and ma5 > ma20:
                signal_short = "큰 하락 가능"
            elif rsi < 30 and ma5 < ma20:
                signal_short = "큰 상승 가능 "
            elif ma5 > ma20:
                signal_short = "하락 가능"
            elif ma5 < ma20:
                signal_short = "상승 가능"
            else:
                signal_short = "횡보"
            
            # 장기 신호 (MACD + 장기 이동평균선 기반)
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
                
            # 결과 데이터 구성
            data = {
                "symbol": symbol,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "lastValue": round(float(last_close), 2),
                "changePercent": round(float(change_percent), 2),
                "signal_short": signal_short,
                "signal_long": signal_long
            }
            
            return data
        else:
            raise ValueError(f"지정된 기간에 대한 충분한 데이터가 없습니다: {symbol}")
    
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        # 오류 발생 시 기본값 반환
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
    # 데이터를 저장할 디렉토리 확인
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    # 파일 이름 생성 (예: USD_KRW.json)
    filename = symbol.replace('/', '_') + '.json'
    file_path = os.path.join(output_dir, filename)
    
    # 데이터 저장 (UTF-8 명시)
    with codecs.open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"데이터가 저장되었습니다: {file_path}")

def main():
    # 기본 환율 정보 로드
    base_rates = load_base_rates()
    
    # 각 통화쌍에 대해 데이터 수집 및 저장
    for symbol in base_rates.keys():
        print(f"Processing {symbol}...")
        data = get_forex_data(symbol)
        
        if data:
            save_forex_data(symbol, data)
        
        # API 호출 제한을 피하기 위한 잠시 대기
        time.sleep(1)

if __name__ == "__main__":
    main()