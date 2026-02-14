# XRP 자동매매 시스템

래리 윌리엄스(Larry Williams) 돌파 전략을 기반으로 한 XRP 자동매매 시스템

## 📋 목차

- [특징](#-특징)
- [요구사항](#-요구사항)
- [설치](#-설치)
- [설정](#-설정)
- [사용법](#-사용법)
- [전략 설명](#-전략-설명)
- [주의사항](#-주의사항)
- [라이선스](#-라이선스)

---

## ✨ 특징

- 🤖 **자동매매**: 래리 윌리엄스 돌파 전략 기반 자동 매매
- 📊 **백테스트**: 과거 데이터로 전략 검증
- 📈 **시각화**: 차트 및 리포트 생성
- 🔔 **텔레그램 알림**: 매수/매도/에러 실시간 알림
- 🏪 **빗썸 API**: 빗썸 거래소와 연동
- 💾 **데이터 관리**: SQLite를 이용한 데이터 저장

---

## 📦 요구사항

- Python 3.9 이상
- 빗썸 계정 (API 키 필요)
- 텔레그램 봇 (봇 토큰 필요)

---

## 🚀 설치

### 1. 저장소 클론

```bash
git clone https://github.com/your-repo/xrp-auto-trading.git
cd xrp-auto-trading
```

### 2. 가상 환경 생성

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

---

## ⚙️ 설정

### 1. 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 수정하세요:

```bash
cp .env.example .env
```

`.env` 파일에 다음 항목을 입력하세요:

```env
# 빗썸 API 설정
BITHUMB_API_KEY=your_api_key_here
BITHUMB_API_SECRET=your_api_secret_here

# 텔레그램 봇 설정
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# 거래 설정
TRADING_CURRENCY=KRW
ORDER_CURRENCY=XRP

# 전략 설정
BREAKTHROUGH_RATIO=0.5
CANDLE_PERIOD=6h
NUM_CANDLES_FOR_AVG=5

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
ERROR_LOG_FILE=logs/error.log
```

### 2. 텔레그램 봇 설정

1. [@BotFather](https://t.me/botfather)와 대화하여 봇 생성
2. API 토큰 복사 후 `.env` 파일의 `TELEGRAM_BOT_TOKEN`에 입력
3. 봇에게 메시지를 보낸 후 `https://api.telegram.org/bot<TOKEN>/getUpdates`에서 `chat_id` 확인
4. `.env` 파일의 `TELEGRAM_CHAT_ID`에 입력

### 3. 빗썸 API 키 설정

1. [빗썸 Open API](https://api.bithumb.com/v1/market/ETH_BTC/orderbook)에 접속
2. API 키 및 시크릿 키 발급
3. `.env` 파일에 입력

---

## 💻 사용법

### 1. 데이터 수집

```bash
python main.py --mode collect --days 365
```

- 최소 1년치 데이터를 수집하는 것이 좋습니다.

### 2. 백테스트 실행

```bash
python main.py --mode backtest --days 365
```

- `reports/` 디렉토리에 결과가 생성됩니다:
  - `backtest_report.html`: 상세 리포트
  - `price_chart.png`: 가격 차트
  - `equity_curve.png`: 수익률 곡선
  - `drawdown.png`: 손실률 차트

### 3. 실전 모드 실행

```bash
python main.py --mode live
```

- 실전 모드에서는 실제 자산이 거래됩니다!
- 소액으로 먼저 테스트를 권장합니다.

---

## 📈 전략 설명

### 래리 윌리엄스 돌파 전략

#### 매수 조건 (3가지 모두 충족 시)

1. **돌파 기준선 돌파**
   ```
   현재봉 고가 > 시가 + (전봉 고가 - 전봉 저가) × 0.5
   ```

2. **5봉 종가 평균 상회**
   ```
   돌파 기준선 가격 > 최근 5봉 종가 평균
   ```

3. **거래량 증가**
   ```
   전봉 거래량 < 현재봉 거래량
   ```

#### 매수 가격

```
돌파 기준선 가격 = 현재봉 시가 + (전봉 고가 - 전봉 저가) × 0.5
```

#### 매도 조건

```
매수 후 다음 6시간 봉 시가에 매도
```

---

## ⚠️ 주의사항

### 보안

- `.env` 파일은 절대로 GitHub에 커밋하지 마세요!
- API 키를 안전하게 관리하세요.
- 정기적으로 API 키를 교체하세요.

### 리스크

- 암호화폐 거래는 높은 리스크가 따릅니다.
- 손실 가능성을 고려하여 소액부터 시작하세요.
- 잃을 수 있는 돈만 투자하세요.

### 성능

- 백테스트 결과가 미래 수익을 보장하지 않습니다.
- 시장 상황에 따라 실제 수익은 다를 수 있습니다.
- 백테스트 후 반드시 소액으로 테스트하세요.

---

## 📂 파일 구조

```
project/
├── .env                      # 환경 변수 (Git 제외)
├── .env.example              # 환경 변수 템플릿
├── .gitignore               # Git 무시 파일
├── README.md                # 이 파일
├── requirements.txt          # Python 패키지 목록
├── config.py                # 설정 클래스
├── main.py                  # 메인 실행 파일
├── bithumb_api.py           # 빗썸 API 클라이언트
├── data_storage.py          # 데이터 저장소
├── data_collector.py        # 데이터 수집기
├── strategy_engine.py       # 전략 엔진
├── backtester.py            # 백테스터
├── visualizer.py            # 시각화
├── order_executor.py        # 주문 실행기
├── portfolio.py             # 포트폴리오 관리
├── notification.py           # 알림 모듈
├── logger.py                # 로깅 모듈
├── logs/                    # 로그 디렉토리
├── data/                    # 데이터 저장소
│   └── candles.db          # 캔들 데이터베이스
├── reports/                 # 백테스트 리포트
│   ├── backtest_report.html
│   ├── price_chart.png
│   ├── equity_curve.png
│   └── drawdown.png
└── tests/                  # 테스트 코드
    ├── test_strategy_engine.py
    ├── test_backtester.py
    └── ...
```

---

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest tests/

# 커버리지 확인
pytest --cov=. tests/
```

---

## 📝 명령줄 옵션

```bash
python main.py --mode [MODE] [OPTIONS]

MODE:
  collect   - 데이터 수집 모드
  backtest  - 백테스트 모드
  live      - 실전 모드

OPTIONS:
  --days N  - 데이터 수집/백테스트 기간 (일)
```

---

## 🤝 기여

기여를 환영합니다! Pull Request를 제출해주세요.

1. 포크하기
2. 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 커밋하기 (`git commit -m 'Add some AmazingFeature'`)
4. 푸시하기 (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

---

## 📞 지원

버그 리포트나 기능 요청은 [이슈](https://github.com/your-repo/xrp-auto-trading/issues)를 통해 제출해주세요.

---

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## ⚖️ 면책 조항

이 소프트웨어는 "있는 그대로" 제공되며, 명시적 또는 묵시적인 어떠한 보증도 하지 않습니다. 이 소프트웨어의 사용으로 인해 발생하는 어떠한 손실에 대해서도 책임지지 않습니다. 암호화폐 거래는 높은 리스크가 있으며, 투자 전에 신중히 검토하시기 바랍니다.

---

## 🙏 감사의 말

- [래리 윌리엄스](https://www.larrywilliams.com/) - 돌파 전략 개발
- [빗썸](https://www.bithumb.com/) - 거래소 API 제공
- [텔레그램](https://telegram.org/) - 알림 서비스 제공

---

**작성자**: Sisyphus AI Agent
**버전**: 1.0.0
**최종 업데이트**: 2026-02-14
