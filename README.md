# XRP 자동매매 시스템

래리 윌리엄스(Larry Williams) 돌파 전략을 기반으로 한 XRP 자동매매 시스템

## 📋 목차

- [특징](#-특징)
- [요구사항](#-요구사항)
- [빠른 시작 (Docker)](#-빠른-시작-docker)
- [설정](#-설정)
- [사용법](#-사용법)
- [텔레그램 제어](#-텔레그램-제어)
- [로컬 실행 (Docker 없이)](#-로컬-실행-docker-없이)
- [전략 설명](#-전략-설명)
- [파일 구조](#-파일-구조)
- [주의사항](#-주의사항)

---

## ✨ 특징

- 🤖 **자동매매**: 래리 윌리엄스 돌파 전략 기반 자동 매매
- 🐳 **Docker 지원**: 컨테이너로 어디서든 동일하게 실행
- 📊 **백테스트**: 과거 데이터로 전략 검증
- 📈 **시각화**: 차트 및 HTML 리포트 생성
- 🔔 **텔레그램 제어**: 매수/매도/에러 알림 + 명령어로 봇 제어 (`/start`, `/stop`, `/status`, `/balance`)
- 🏪 **빗썸 API**: 빗썸 거래소와 연동 (JWT HS256 인증)
- 💾 **데이터 관리**: SQLite를 이용한 캔들 데이터 저장

---

## 📦 요구사항

- **Docker** + **Docker Compose** (권장)
- 빗썸 계정 (API 키 필요)
- 텔레그램 봇 (봇 토큰 필요)

> Docker 없이 로컬에서 실행하려면 [로컬 실행](#-로컬-실행-docker-없이) 섹션을 참조하세요.

---

## 🚀 빠른 시작 (Docker)

### 1. 저장소 클론

```bash
git clone https://github.com/kinsu128-art/xrp-auto-trading.git
cd xrp-auto-trading
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 API 키와 텔레그램 설정을 입력합니다:

```env
# 빗썸 API 설정 (필수)
BITHUMB_API_KEY=your_api_key_here
BITHUMB_API_SECRET=your_api_secret_here

# 텔레그램 봇 설정 (필수)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

### 3. 데이터 수집

실전 매매 전에 반드시 과거 데이터를 수집해야 합니다:

```bash
docker compose run --rm trading-bot --mode collect --days 365
```

### 4. 백테스트 실행

수집한 데이터로 전략을 검증합니다:

```bash
docker compose run --rm trading-bot --mode backtest --days 365
```

결과는 `reports/` 디렉토리에 생성됩니다.

### 5. 실전 모드 실행

```bash
docker compose up -d --build
```

컨테이너가 백그라운드에서 실행됩니다. 텔레그램으로 봇 상태를 확인하고 제어할 수 있습니다:

| 명령어 | 기능 |
|---|---|
| `/start` | 매매 재개 |
| `/stop` | 매매 일시중지 (봇 프로세스는 유지) |
| `/status` | 봇 상태, 포지션, 잔고, 마지막 캔들 조회 |
| `/balance` | 빗썸에서 실시간 잔고 조회 |
| `/help` | 사용 가능한 명령어 목록 |

> `/stop`은 매매만 일시중지하며 봇 프로세스와 텔레그램 수신은 유지됩니다. `/start`로 언제든 재개할 수 있습니다.

---

## ⚙️ 설정

### 환경 변수 (.env)

| 변수 | 설명 | 기본값 |
|---|---|---|
| `BITHUMB_API_KEY` | 빗썸 API 키 | (필수) |
| `BITHUMB_API_SECRET` | 빗썸 API 시크릿 | (필수) |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 | (필수) |
| `TELEGRAM_CHAT_ID` | 텔레그램 챗 ID | (필수) |
| `TRADING_CURRENCY` | 결제 통화 | `KRW` |
| `ORDER_CURRENCY` | 주문 통화 | `XRP` |
| `BREAKTHROUGH_RATIO` | 돌파 배율 | `0.5` |
| `CANDLE_PERIOD` | 캔들 주기 | `6h` |
| `NUM_CANDLES_FOR_AVG` | 평균 계산 봉 수 | `5` |
| `LOG_LEVEL` | 로그 레벨 | `INFO` |
| `LOG_RETENTION_DAYS` | 로그 보관 일수 | `7` |
| `DATABASE_PATH` | DB 파일 경로 | `data/candles.db` |
| `MAX_RETRIES` | API 재시도 횟수 | `3` |
| `RETRY_DELAY` | 재시도 간격(초) | `1` |

### 텔레그램 봇 설정

1. [@BotFather](https://t.me/botfather)와 대화하여 봇 생성
2. API 토큰 복사 → `.env`의 `TELEGRAM_BOT_TOKEN`에 입력
3. 봇에게 메시지를 보낸 후 `https://api.telegram.org/bot<TOKEN>/getUpdates`에서 `chat_id` 확인
4. `.env`의 `TELEGRAM_CHAT_ID`에 입력

### 빗썸 API 키 설정

1. [빗썸](https://www.bithumb.com/) 로그인 → API 관리에서 키 발급
2. `.env` 파일에 `BITHUMB_API_KEY`, `BITHUMB_API_SECRET` 입력

---

## 💻 사용법

### Docker Compose 명령어

```bash
# master 브랜치 최신 상태로 업데이트
git pull origin master

# 실전 모드 (백그라운드 실행)
docker compose up -d --build

# 로그 실시간 확인
docker compose logs -f trading-bot

# 데이터 수집
docker compose run --rm trading-bot --mode collect --days 365

# 백테스트
docker compose run --rm trading-bot --mode backtest --days 365

# 컨테이너 중지 (프로세스 완전 종료)
docker compose down

# 컨테이너 재시작
docker compose restart
```

> 실행 중 매매를 일시중지하려면 텔레그램에서 `/stop`을 보내세요. 컨테이너를 내릴 필요 없이 `/start`로 재개할 수 있습니다. 자세한 내용은 [텔레그램 제어](#-텔레그램-제어) 섹션을 참조하세요.

### Docker 단독 실행

```bash
# 이미지 빌드
docker build -t xrp-trading-bot .

# 데이터 수집
docker run --rm --env-file .env \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  xrp-trading-bot --mode collect --days 365

# 백테스트
docker run --rm --env-file .env \
  -v ./data:/app/data \
  -v ./reports:/app/reports \
  xrp-trading-bot --mode backtest --days 365

# 실전 모드
docker run -d --name xrp-bot --env-file .env \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  -v ./reports:/app/reports \
  --restart unless-stopped \
  xrp-trading-bot --mode live --confirm
```

### 명령줄 옵션

```
python main.py --mode [MODE] [OPTIONS]

MODE:
  collect    데이터 수집 모드
  backtest   백테스트 모드 (기본값)
  live       실전 자동매매 모드

OPTIONS:
  --days N     데이터 수집/백테스트 기간 (일, 기본 365)
  --confirm    실전 모드 확인 프롬프트 생략 (Docker 환경용)
```

### 데이터 영속성

Docker 볼륨 마운트를 통해 다음 데이터가 호스트에 유지됩니다:

| 호스트 경로 | 컨테이너 경로 | 내용 |
|---|---|---|
| `./data/` | `/app/data/` | SQLite 캔들 DB |
| `./logs/` | `/app/logs/` | 앱/에러 로그 |
| `./reports/` | `/app/reports/` | 백테스트 차트/리포트 |

### 백테스트 결과 (최근 365일 기준)

| 지표 | 결과 |
|---|---|
| 총 수익률 | **+86.73%** |
| 연간 수익률 | **+87.78%** |
| 승률 | 43.72% |
| 손익비 | 1.36 |
| 최대 손실률(MDD) | 21.18% |
| 샤프 비율 | 4.17 |
| 총 거래 횟수 | 231회 (승 101 / 패 130) |

> 초기 자본 100만 KRW, 수수료 0.25% 적용 기준

`reports/` 디렉토리에 생성되는 파일:

- `backtest_report.html` - 상세 HTML 리포트
- `price_chart.png` - 가격 차트 (매수/매도 포인트)
- `equity_curve.png` - 수익률 곡선
- `drawdown.png` - 최대 손실률 차트
- `trade_distribution.png` - 거래 분포

---

## 📱 텔레그램 제어

실전 모드에서 봇은 텔레그램 메시지를 통해 양방향 제어가 가능합니다. 봇이 시작되면 자동으로 텔레그램 폴링을 시작하여 명령어를 수신합니다.

### 명령어

| 명령어 | 기능 | 설명 |
|---|---|---|
| `/start` | 매매 재개 | 일시중지된 매매를 재개합니다 |
| `/stop` | 매매 일시중지 | 매매만 중지, 봇 프로세스와 텔레그램 수신은 유지 |
| `/status` | 상태 조회 | 실행 상태, 포지션, 잔고, 마지막 캔들 정보 |
| `/balance` | 잔고 조회 | 빗썸 API에서 실시간 KRW/XRP 잔고 조회 |
| `/help` | 도움말 | 사용 가능한 명령어 목록 |

### 동작 방식

- **폴링 방식**: Telegram Bot API `getUpdates`를 사용한 long polling (별도 데몬 스레드)
- **인증**: 설정된 `TELEGRAM_CHAT_ID`에서 온 메시지만 처리, 다른 사용자의 명령은 무시
- **`/stop` vs `docker compose down`**:
  - `/stop`: 매매만 일시중지, 봇 프로세스는 계속 실행되어 텔레그램 명령을 수신
  - `docker compose down`: 컨테이너와 봇 프로세스를 완전히 종료

---

## 🖥️ 로컬 실행 (Docker 없이)

Docker 없이 직접 실행하려면:

```bash
# 가상 환경 생성
python -m venv venv

# 활성화 (Windows)
venv\Scripts\activate

# 활성화 (Linux/Mac)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 데이터 수집
python main.py --mode collect --days 365

# 백테스트
python main.py --mode backtest --days 365

# 실전 모드
python main.py --mode live
```

요구사항: Python 3.9 이상

---

## 📈 전략 설명

### 래리 윌리엄스 돌파 전략

6시간 봉 기준으로 동작하는 단기 매매 전략입니다.

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

#### 매도 조건

매수 조건(3가지) 중 **하나라도 충족되지 않을 때** 현재봉 시가에 매도합니다.
매수 조건이 유지되는 동안은 포지션을 계속 보유합니다.

| 매도 트리거 | 설명 |
|---|---|
| 돌파 기준선 미달 | 현재봉 고가 ≤ 돌파 기준선 |
| 5봉 종가 평균 미달 | 돌파 기준선 ≤ 최근 5봉 종가 평균 |
| 거래량 감소 | 현재봉 거래량 ≤ 전봉 거래량 |

> 텔레그램 매도 알림에 **매도 사유**가 함께 전송됩니다.
> 예: `📋 매도 사유: 돌파 기준선 미달, 거래량 감소`

#### 스케줄

한국시간 기준 **00:00, 06:00, 12:00, 18:00** 에 캔들 마감 체크 및 매매 실행

---

## 📂 파일 구조

```
xrp-auto-trading/
├── Dockerfile                # Docker 이미지 정의
├── docker-compose.yml        # Docker Compose 설정
├── .dockerignore             # Docker 빌드 제외 파일
├── .env                      # 환경 변수 (Git 제외)
├── .env.example              # 환경 변수 템플릿
├── .gitignore                # Git 무시 파일
├── requirements.txt          # Python 패키지 목록
├── __init__.py               # 패키지 초기화
├── main.py                   # 메인 실행 파일 (TradingBot + 텔레그램 명령 핸들러)
├── config.py                 # 설정 관리 (환경 변수 기반)
├── bithumb_api.py            # 빗썸 API 클라이언트 (JWT HS256 인증)
├── strategy_engine.py        # 래리 윌리엄스 전략 엔진
├── order_executor.py         # 주문 실행기 (재시도 포함)
├── data_collector.py         # 캔들 데이터 수집기 (forming candle 자동 제외)
├── data_storage.py           # SQLite 데이터 저장소
├── portfolio.py              # 포트폴리오/포지션 관리
├── notification.py           # 텔레그램 알림 및 명령어 수신 (폴링)
├── backtester.py             # 백테스트 엔진
├── visualizer.py             # 차트/리포트 시각화 (헤드리스)
├── logger.py                 # 로깅 시스템
├── utils.py                  # 유틸리티 함수
├── exceptions.py             # 커스텀 예외
├── deploy.bat                # Windows 배포 스크립트
├── DEPLOY.md                 # 배포 가이드
├── data/                     # 캔들 DB (Docker 볼륨)
├── logs/                     # 로그 파일 (Docker 볼륨)
├── reports/                  # 백테스트 리포트 (Docker 볼륨)
├── docs/                     # 추가 문서
└── tests/                    # 테스트 코드
```

---

## ⚠️ 주의사항

### 보안

- `.env` 파일은 절대로 GitHub에 커밋하지 마세요
- API 키를 안전하게 관리하고 정기적으로 교체하세요
- Docker 환경에서는 `--env-file`로 환경 변수를 전달합니다

### 리스크

- 암호화폐 거래는 높은 리스크가 따릅니다
- 손실 가능성을 고려하여 소액부터 시작하세요
- 잃을 수 있는 돈만 투자하세요

### 성능

- 백테스트 결과가 미래 수익을 보장하지 않습니다
- 시장 상황에 따라 실제 수익은 다를 수 있습니다
- 백테스트 후 반드시 소액으로 테스트하세요

---

## ⚖️ 면책 조항

이 소프트웨어는 "있는 그대로" 제공되며, 명시적 또는 묵시적인 어떠한 보증도 하지 않습니다. 이 소프트웨어의 사용으로 인해 발생하는 어떠한 손실에 대해서도 책임지지 않습니다. 암호화폐 거래는 높은 리스크가 있으며, 투자 전에 신중히 검토하시기 바랍니다.

---

**버전**: 1.2.0
**최종 업데이트**: 2026-02-26

### 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| 1.2.0 | 2026-02-26 | 매도 조건 변경(매수 조건 미충족 시 매도), 매도 사유 텔레그램 알림 추가, 매도 API 오류(invalid_price_ask) 수정 |
| 1.1.0 | 2026-02-24 | 스레드 안전성, 텔레그램 안정성, 캔들 폴백 개선 |
| 1.0.0 | 2026-02-20 | 최초 릴리스 |
