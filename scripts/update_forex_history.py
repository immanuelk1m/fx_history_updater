import json
import os
import yfinance as yf
from datetime import datetime, timedelta
import time
from typing import Dict, Any, List
import codecs

def load_base_rates() -> Dict[str, float]:
    """base_rates.json 파일에서 통화 기본 환율 정보를 로드합니다."""
    base_rates_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 'example', 'base_rates.json')
    
    with open(base_rates_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['base_rates']

def get_forex_history(symbol: str, days: int = 150) -> Dict[str, Any]:
    """yfinance를 사용하여 통화의 일별 종가 데이터를 가져옵니다."""
    # 심볼 형식을 yfinance 형식으로 변환 (USD/KRW -> USDKRW=X)
    yf_symbol = symbol.replace('/', '') + '=X'
    
    try:
        ticker = yf.Ticker(yf_symbol)
        
        # days+10일치 데이터를 가져와서 최근 days일만 사용 (주말 및 공휴일을 고려)
        hist = ticker.history(period=f"{days+10}d")
        
        if hist.empty:
            raise ValueError(f"No data found for {symbol}")
        
        # 날짜별 종가 데이터 추출 (최근 days일만)
        daily_rates = []
        
        # 최근 데이터부터 정렬
        hist = hist.sort_index(ascending=False)
        
        # 최대 days일만 가져오기
        count = 0
        for date, row in hist.iterrows():
            if count >= days:
                break
                
            daily_rates.append({
                "currency_pair": symbol,
                "rate": round(float(row['Close']), 2),
                "timestamp": date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            })
            count += 1
        
        # 날짜 오름차순으로 다시 정렬 (오래된 날짜가 먼저)
        daily_rates.reverse()
        
        # 결과 데이터 구성
        data = {
            "currency_pair": symbol,
            "lastUpdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "rates": daily_rates
        }
        
        return data
    
    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        # 오류 발생 시 기본값 반환
        return {
            "currency_pair": symbol,
            "lastUpdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "rates": []
        }

def save_forex_history(symbol: str, data: Dict[str, Any]) -> None:
    """통화의 일별 종가 환율 데이터를 JSON 파일로 저장합니다."""
    # 데이터를 저장할 디렉토리 확인
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'history')
    os.makedirs(output_dir, exist_ok=True)
    
    # 파일 이름 생성 (예: USD_KRW_history.json)
    filename = symbol.replace('/', '_') + '_history.json'
    file_path = os.path.join(output_dir, filename)
    
    # 데이터 저장 (UTF-8 명시)
    with codecs.open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"히스토리 데이터가 저장되었습니다: {file_path}")

def main():
    # 기본 환율 정보 로드
    base_rates = load_base_rates()
    
    # 각 통화쌍에 대해 히스토리 데이터 수집 및 저장
    for symbol in base_rates.keys():
        print(f"Processing history for {symbol}...")
        history_data = get_forex_history(symbol, days=150)
        
        if history_data and history_data.get('rates'):
            save_forex_history(symbol, history_data)
            print(f"Saved {len(history_data['rates'])} days of data for {symbol}")
        else:
            print(f"No data available for {symbol}")
        
        # API 호출 제한을 피하기 위한 대기
        time.sleep(2)

if __name__ == "__main__":
    main()