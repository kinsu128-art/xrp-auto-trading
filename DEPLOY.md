# 배포 가이드

## 📋 배포 체크리스트

### 사전 체크

- [ ] 설정 파일 확인 (`.env`)
- [ ] API 키 유효성 확인
- [ ] 텔레그램 봇 연동 확인
- [ ] 데이터베이스 생성 확인
- [ ] 로그 디렉토리 생성 확인
- [ ] 의존성 설치 완료

### 기능 체크

- [ ] 데이터 수집 기능 테스트
- [ ] 백테스트 기능 테스트
- [ ] 전략 로직 테스트
- [ ] 텔레그램 알림 테스트

### 보안 체크

- [ ] `.env` 파일이 Git에 커밋되지 않음
- [ ] API 키가 암호화되어 저장됨
- [ ] 민감한 정보가 로그에 포함되지 않음
- [ ] 방화벽 설정 확인

### 리스크 관리

- [ ] 소액으로 실전 테스트 수행
- [ ] 손절가 기능 확인
- [ ] 리스크 한도 설정
- [ ] 정기적인 상태 모니터링 계획

---

## 🚀 배포 절차

### 1. 개발 환경 → 테스트 환경

```bash
# 1. Git 저장소에 푸시
git add .
git commit -m "Release v1.0.0"
git push origin main

# 2. 테스트 서버에서 클론
git clone https://github.com/your-repo/xrp-auto-trading.git
cd xrp-auto-trading

# 3. 환경 설정
python -m venv venv
source venv/bin/activate  # 또는 venv\Scripts\activate (Windows)
pip install -r requirements.txt

# 4. 설정 파일 복사 및 수정
cp .env.example .env
# .env 파일 편집

# 5. 데이터 수집 테스트
python main.py --mode collect --days 30

# 6. 백테스트 실행
python main.py --mode backtest --days 30
```

### 2. 테스트 환경 → 운영 환경

```bash
# 1. 최신 코드 가져오기
git pull origin main

# 2. 의존성 업데이트
pip install -r requirements.txt --upgrade

# 3. 소액 실전 테스트 (1주일)
python main.py --mode live

# 4. 모니터링
- 로그 확인: tail -f logs/app.log
- 텔레그램 알림 확인
- 잔고 확인
```

### 3. 롤백 절차

문제 발생 시 즉시 롤백:

```bash
# 1. 이전 버전으로 복원
git checkout tags/v1.0.0  # 또는 이전 커밋

# 2. 의존성 복원
pip install -r requirements.txt

# 3. 서비스 재시작
# (systemd 사용 시)
sudo systemctl restart xrp-trading-bot
```

---

## 📊 모니터링

### 시스템 모니터링

```bash
# CPU 사용량
top
htop

# 메모리 사용량
free -h

# 디스크 사용량
df -h

# 프로세스 상태
ps aux | grep python
```

### 로그 모니터링

```bash
# 실시간 로그 확인
tail -f logs/app.log

# 에러 로그만 확인
tail -f logs/error.log

# 최근 100줄 확인
tail -n 100 logs/app.log

# 특정 패턴 검색
grep "ERROR" logs/app.log
grep "매수" logs/app.log
```

### 텔레그램 모니터링

```bash
# 텔레그램 봇이 메시지를 수신하는지 확인
curl https://api.telegram.org/bot<TOKEN>/getUpdates
```

---

## 🔧 유지보수

### 정기 작업

| 주기 | 작업 | 설명 |
|------|------|------|
| 매일 | 로그 확인 | 에러 및 비정상 동작 확인 |
| 매일 | 거래 내역 확인 | 예기치 못한 거래 확인 |
| 주간 | 데이터 백업 | 데이터베이스 백업 |
| 주간 | 성과 분석 | 수익률 및 승률 분석 |
| 월간 | 파라미터 최적화 | 전략 파라미터 검토 |
| 월간 | API 키 교체 | 보안을 위한 키 교체 |

### 데이터 백업

```bash
# 1. 데이터베이스 백업
cp data/candles.db backup/candles_$(date +%Y%m%d).db

# 2. 로그 백업
tar -czf backup/logs_$(date +%Y%m%d).tar.gz logs/

# 3. 설정 백업
cp .env backup/.env_$(date +%Y%m%d)

# 4. 오래된 백업 삭제 (30일 이상)
find backup/ -name "*.db" -mtime +30 -delete
find backup/ -name "*.tar.gz" -mtime +30 -delete
```

---

## 🚨 문제 해결

### 일반적인 문제

#### 1. API 연결 실패

```bash
# 해결 방법
1. API 키 확인
2. 인터넷 연결 확인
3. 방화벽 설정 확인
4. API 엔드포인트 변경 확인
```

#### 2. 데이터베이스 잠금

```bash
# 해결 방법
1. 프로세스 중지
2. 잠금 파일 삭제
3. 데이터베이스 복구
```

#### 3. 메모리 부족

```bash
# 해결 방법
1. 데이터 양 제한
2. 로그 회전 설정
3. 메모리 최적화
```

---

## 📈 성능 최적화

### 데이터 수집 최적화

```python
# 캔들 데이터 배치 수집
def fetch_candles_batch(self, start_date, end_date, batch_size=100):
    """배치 단위로 데이터 수집"""
    candles = []
    current_date = start_date

    while current_date < end_date:
        batch = self.api.get_candlestick(
            count=min(batch_size, 100)
        )
        candles.extend(batch)
        current_date += timedelta(days=30)

    return candles
```

### 로깅 최적화

```python
# 로그 레벨 조정
LOG_LEVEL = "WARNING"  # 개발 외에는 WARNING 이상
```

---

## 🔐 보안

### 보안 체크리스트

- [ ] `.env` 파일을 `.gitignore`에 추가
- [ ] API 키를 코드에 하드코딩하지 않음
- [ ] 민감한 정보를 로그에 기록하지 않음
- [ ] HTTPS만 사용
- [ ] 정기적인 보안 업데이트
- [ ] 2단계 인증 사용
- [ ] IP 화이트리스트 설정

### 암호화

```python
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

def encrypt_api_key(api_key, password):
    """API 키 암호화"""
    salt = get_random_bytes(16)
    key = PBKDF2(password.encode(), salt, dkLen=32)
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(api_key.encode())
    return salt + cipher.nonce + tag + ciphertext
```

---

## 📞 지원

### 문제 신고

문제가 발생하면 다음 정보를 수집하세요:

1. 에러 로그 (`logs/error.log`)
2. 시스템 정보 (OS, Python 버전)
3. 재현 단계
4. 스크린샷

### 연락처

- 이슈 트래커: https://github.com/your-repo/xrp-auto-trading/issues
- 이메일: your-email@example.com

---

**문서 버전**: 1.0
**작성일**: 2026-02-14
**작성자**: Sisyphus AI Agent
