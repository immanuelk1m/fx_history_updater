# 통화 히스토리 데이터 자동 업데이트

이 저장소는 base_rates.json에 정의된 각 통화쌍에 대해 오늘 기준으로 150일치 일별 종가 환율 데이터를 수집하고 2시간마다 자동으로 업데이트하는 GitHub Actions 워크플로우를 포함하고 있습니다.

## 기능

- yfinance를 사용하여 최근 150일치의 일별 종가 환율 데이터 수집
- 각 통화쌍별로 별도의 JSON 파일에 히스토리 데이터 저장
- GitHub Actions를 통한 2시간 주기 자동 업데이트
- 모든 변경사항 자동 커밋 및 푸시

## 데이터 형식

각 통화쌍별 히스토리 JSON 파일은 다음과 같은 형식으로 저장됩니다:

```json
{
  "currency_pair": "USD/KRW",
  "lastUpdated": "2025-03-25T12:30:00.000Z",
  "rates": [
    {
      "currency_pair": "USD/KRW",
      "rate": 1348.67,
      "timestamp": "2024-10-27T00:00:00.000Z"
    },
    {
      "currency_pair": "USD/KRW",
      "rate": 1347.95,
      "timestamp": "2024-10-28T00:00:00.000Z"
    },
    ...
  ]
}
```

## 설정 방법

1. 이 저장소를 포크하거나 클론합니다.
2. `example/base_rates.json` 파일을 수정하여 원하는 통화 쌍을 추가/제거할 수 있습니다.
3. GitHub Actions는 자동으로 활성화되어 2시간마다 데이터를 업데이트합니다.
4. 수동으로 업데이트를 실행하려면 Actions 탭에서 워크플로우를 수동으로 실행할 수 있습니다.

## 사용된 기술

- Python
- yfinance 라이브러리
- GitHub Actions
- JSON 데이터 포맷