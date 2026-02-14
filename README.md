# Upbit Bot

자동 변동성 돌파 전략 기반 업비트 현물 트레이딩 봇.

## 구조

```
upbit-bot/
├─ bot.py                # 메인 실행 파일 (전략 로드, 주문 루프)
├─ config.py             # 환경 변수 로딩 및 공통 설정
├─ requirements.txt      # 의존성
├─ .env.example          # 필요한 키/환경 변수 예시
├─ strategies/
│  └─ vol_breakout.py    # 변동성 돌파 전략 구현
├─ data/
│  ├─ upbit_client.py    # 업비트 REST API 래퍼 (ccxt 또는 직접 호출)
│  └─ backtest.py        # 백테스트/데이터 헬퍼
└─ notebooks/            # 실험/분석 노트북 (선택)
```

## 기본 흐름
1. `config.py`에서 API 키, 거래금액, 대상 마켓(KRW-BTC 등) 로딩
2. `data/upbit_client.py`로 시세 데이터와 주문/잔고 관리
3. `strategies/vol_breakout.py`에서 매수/매도 시그널 계산
4. `bot.py`에서 위 구성요소를 묶어 주기적으로 실행

## 준비
1. `.env.example`을 복사해 `.env` 생성 후 API 키 입력
2. `python -m venv venv && source venv/bin/activate`
3. `pip install -r requirements.txt`
4. `python bot.py --mode backtest` 등 원하는 모드 실행
