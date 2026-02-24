# 서버 배포 및 운영 가이드
# Server Deployment & Operations Guide

---

## 📋 서버 배포 환경 선택

### 1️⃣ 배포 환경 선택

| 환경 | 특징 | 추천 용도 |
|------|------|----------|
| **로컬 PC** | 편리함, 제어 직접 접근 가능 | 테스트 및 소액 운영 |
| **VPS (Windows Server)** | 24시간 가동, 원격 접근 | 본격 운영 |
| **Cloud (Azure/AWS)** | 고가용성, 백업 자동화, 관리 용이 | 대규모 서비스 |
| **Docker** | 이식성, 관리 용이 | 컨테이너 배포 |

---

## 🖥 Windows VPS 배포 (권장)

### 단계 1: VPS 구매

**추천 VPS 제공업:**
- AWS (Amazon EC2)
- Azure
- Naver Cloud / KT Cloud
- Alibaba Cloud

**최소 사양:**
- CPU: 2코어 이상
- RAM: 4GB 이상
- OS: Windows Server 2019/2022
- 저장소: 20GB SSD

---

### 단계 2: VPS 설정

#### 2.1 원격 데스크톱 (RDP) 연결
1. VPS 공인 IP, 사용자명, 비밀번호로 RDP 연결
2. Windows Server 초기 설정 완료

#### 2.2 시스템 업데이트
```powershell
# 1. Windows Update 실행
sconfig

# 2. 필수 소프트웨어 설치
# - Python 3.9+ (https://www.python.org/downloads/)
# - Git (https://git-scm.com/downloads)

# 3. 시스템 재부팅
```

---

### 단계 3: 프로젝트 배포

#### 3.1 프로젝트 복사
```powershell
# 1. 원격 데스크톱으로 프로젝트 파일 복사
# 로컬 PC의 D:\Vibe\Auto_trade00 폴더 전체 복사

# 2. C:\XRP-AutoTrading 디렉토리에 붙여넣기
# C:\XRP-AutoTrading\Auto_trade00 (프로젝트 내용물)
```

#### 3.2 가상 환경 설정
```powershell
# 1. 프로젝트 디렉토리로 이동
cd C:\XRP-AutoTrading\Auto_trade00

# 2. 가상 환경 생성
python -m venv venv
venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. .env 파일 생성
copy .env.example .env

# 5. .env 파일 편집 (메모장으로 열어서 편집)
notepad .env

# 6. API 키, 텔레그램 토큰, Chat ID 입력
```

#### 3.3 백업 폴더 생성
```powershell
# 1. 백업 디렉토리 생성
New-Item -ItemType Directory -Path "C:\XRP-AutoTrading\Backup" -Force

# 2. 로그 백업 폴더
New-Item -ItemType Directory -Path "C:\XRP-AutoTrading\Backup\Logs" -Force

# 3. 데이터 백업 폴더
New-Item -ItemType Directory -Path "C:\XRP-AutoTrading\Backup\Data" -Force
```

---

### 단계 4: Windows 서비스로 등록 (권장)

#### 4.1 NSSM (Non-Sucking Service Manager) 다운로드

```powershell
# 1. NSSM 다운로드
# https://nssm.cc/download

# 2. NSSM 설치 (관리자 권한 필요)
# nssm-2.24.zip 다운로드 후 압축

# 3. nssm.exe를 경로에 복사
# C:\Windows\System32\

# 4. CMD (관리자)에서 실행
nssm install XRPTradingBot "C:\Python39\python.exe" "C:\XRP-AutoTrading\Auto_trade00\main.py" --mode live

# 5. 서비스 설정
nssm set XRPTradingBot AppDirectory C:\XRP-AutoTrading\Auto_trade00
nssm set XRPTradingBot AppEnvironmentExtra "PYTHONUNBUFFERED=1"
nssm set XRPTradingBot AppStdout C:\XRP-AutoTrading\Auto_trade00\logs\stdout.log
nssm set XRPTradingBot AppStderr C:\XRP-AutoTrading\Auto_trade00\logs\stderr.log
nssm set XRPTradingBot AppRotateFiles 1
nssm set XRPTradingBot AppRotateSeconds 86400  # 24시간마다 로그 회전

# 6. 서비스 시작
nssm start XRPTradingBot

# 7. 서비스 상태 확인
nssm status XRPTradingBot
```

#### 4.2 서비스 관리 명령어
```powershell
# 서비스 시작
nssm start XRPTradingBot

# 서비스 중지
nssm stop XRP TradingBot

# 서비스 재시작
nssm restart XRPTradingBot

# 서비스 상태 확인
nssm status XRPTradingBot

# 서비스 삭제
nssm remove XRPTradingBot confirm
```

---

## 🖥 로컬 PC에서 실행 (테스트용)

### 설정

```powershell
# 1. 프로젝트 폴더로 이동
cd D:\Vibe\Auto_trade00

# 2. 가상 환경 활성화
.\venv\Scripts\activate

# 3. .env 설정 확인
notepad .env

# 4. 데이터 수집 (최초 1회)
python main.py --mode collect --days 365

# 5. 백테스트 실행 (테스트)
python main.py --mode backtest --days 365

# 6. 실전 모드 실행 (주의!)
python main.py --mode live
```

---

## 🖥 실전 운영 체크리스트

### 시스템 준비
- [ ] Python 3.9+ 설치 완료
- [ ] 가상 환경 생성 및 활성화 완료
- [ ] 의존성 설치 완료
- [ ] `.env` 파일 설정 완료
  - [ ] 빗썸 API 키 입력 완료
  - [ ] 빗썸 API 시크릿 입력 완료
  - [ ] 텔레그램 봇 토큰 입력 완료
  - [ ] 텔레그램 Chat ID 확인 완료

### API 연결
- [ ] 빗썸 API 키 발급 완료
- [ ] API 연결 테스트 완료
- [ ] 캔들 데이터 수집 테스트 완료

### 텔레그램
- [ ] 봇 생성 완료 (@BotFather)
- [ ] 봇 토큰 획득 완료
- [ ] Chat ID 획득 완료
- [ ] 봇에 메시지 테스트 완료

### 데이터
- [ ] 1년치 데이터 수집 완료
- [ ] 백테스트 완료 (승률 60% 이상)
- [ ] 백테스트 연간 수익률 20% 이상
- [ ] 백테스트 최대 손실률 10% 이하

### 리스크 관리
- [ ] 소액으로 실전 테스트 완료 (10,000원 ~ 50,000원)
- [ ] 손절가 정책 설정 완료
- [ ] 전체 자산의 1~2%만 거래로 제한
- [ ] 거래 수수 제한 설정 완료

### 모니터링
- [ ] 로그 모니터링 시스템 구축
- [ ] 거래 내역 모니터링
- [ ] API 요청 모니터링
- [ ] 시스템 상태 모니터링

---

## 🖥 운영 모니터링

### 1. 시스템 모니터링

#### 1.1 자원 사용량 확인

```powershell
# CPU 사용량
Get-Process python | Select-Object Name, CPU, WorkingSet, Id | Format-Table

# 메모리 사용량
Get-Process python | Select-Object Name, PM, Id | Format-Table

# 디스크 사용량
Get-PSDrive C | Select-Object Used, Free, @{Name="사용률 (%)"; Expression=[math]::round($_.Used / $_.Size * 100, 2)}}
```

#### 1.2 디스크 공간 확인

```powershell
# 프로젝트 폴더 크기 확인
$size = (Get-ChildItem -Path "C:\XRP-AutoTrading\Auto_trade00" -Recurse | 
    Measure-Object -Property Length -Sum).Sum / 1GB
Write-Host "프로젝트 크기: $([math]::Round($size, 2)) GB"

# 데이터베이스 크기 확인
$fileSize = (Get-Item "C:\XRP-Auto_Trading\data\candles.db").Length / 1MB
Write-Host "데이터베이스 크기: $fileSize MB"
```

---

### 2. 로그 모니터링

#### 2.1 실시간 로그 확인

```powershell
# 최신 로그 100줄 확인 (실시간)
Get-Content "C:\XRP-AutoTrading\Auto_trade00\logs\app.log" -Tail 100 -Wait

# 에러 로그 확인 (실시간)
Get-Content "C:\XRP-Auto_Trading\Auto_trade00\logs\error.log" -Tail 20 -Wait
```

#### 2.2 로그 분석

```powershell
# 오늘의 매수/매도 횟수
(Get-Content "C:\XRP-AutoTrading\Auto_trade00\logs\app.log" | Select-String "매수|매도").Count

# 오류 발생 횟수
(Get-Content "C:\XRP-AutoTrading\Auto_trade00\logs\error.log" | Select-String "ERROR").Count
```

---

### 3. 성과 모니터링

#### 3.1 거래 내역 확인

```powershell
# logs/app.log에서 오늘의 거래 내역 추출
$logContent = Get-Content "C:\XRP-AutoTrading\Auto_trade00\logs\app.log"
$trades = $logContent | Select-String "📥|📤" -Context 0, 20

Write-Host "오늘 거래 횟수: $($trades.Count)"
```

#### 3.2 성과 지표 계산

```powershell
# 리포트 폴더에서 최신 백테스트 결과 확인
$latestReport = Get-ChildItem "C:\XRP-AutoTrading\Auto_trade00\reports\" -File | 
    Sort-Object LastWriteTime -Descending | Select-Object -First 1

Write-Host "최신 백테스트 보고서:"
Write-Host $latestReport.FullName

# 브라우저에서 열기
Start-Process $latestReport.FullName
```

---

## 🖥 백업 및 복구

### 1. 정기 백업

#### 1.1 자동 백업 스크립트 (PowerShell)

```powershell
# backup.ps1
# 저장 경로 설정
$projectPath = "C:\XRP-AutoTrading\Auto_trade00"
$backupPath = "C:\XRP-AutoTrading\Backup"
$daysToKeep = 30  # 30일치만 보관

# 백업 폴더 확인
if (-not (Test-Path $backupPath)) {
    New-Item -ItemType Directory -Path $backupPath -Force
}

# 날짜 형식
$dateStamp = Get-Date -Format "yyyyMMdd_HHmmss"

# 데이터베이스 백업
$dbPath = "$projectPath\data\candles.db"
$dbBackupPath = "$backupPath\Data\candles_$dateStamp.db"
Copy-Item $dbPath -Destination $dbBackupPath -Force

# 로그 백업
$logPath = "$projectPath\logs"
$logBackupPath = "$backupPath\Logs\logs_$dateStamp.zip"
Compress-Archive -Path $logBackupPath -DestinationPath $logPath -Force

# 설정 파일 백업
$envPath = "$projectPath\.env"
$envBackupPath = "$backupPath\Config\.env_$dateStamp"
Copy-Item $envPath -Destination $envBackupPath -Force

Write-Host "백업 완료: $dateStamp"

# 30일 이상 된 백업 삭제
$cutoffDate = (Get-Date).AddDays(-$daysToKeep)

Get-ChildItem -Path $backupPath\* -File | Where-Object {
    $_.LastWriteTime -lt $cutoffDate
} | ForEach-Object {
    Remove-Item $_.FullName
}

Write-Job -Name "AutoBackup" -TriggerName "Daily" -ScriptBlock {
    $scriptPath = "C:\XRP-AutoTrading\Scripts\backup.ps1"
    & $scriptPath
} -ScheduledJobOption DeleteTriggers
```

#### 1.2 백업 스크립트 (Windows 태스크 스케줄러)

```xml
<!-- backup.xml -->
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/03/multitasking">
  <Principals>
    <Principal id="SYSTEM">
      <LogonType>InteractiveToken</LogonType>
    <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principles>
  <Settings>
    <MultipleInstancesPolicy>StopExisting</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries>
    <StopOnIdleEnd>true</StopOnIdleEnd>
    <IdleDuration>PT10M</IdleDuration>
  <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
  </Settings>
  <Actions Context="SYSTEM">
    <Task>
      <Triggers>
        <CalendarTrigger>
          <StartBoundary>2026-01-01T03:00:00</StartBoundary>
          <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
          <Enabled>true</Enabled>
          <ScheduleByWeek>
            <DaysOfWeek>
              <Monday />
              <Tuesday />
              <Wednesday />
              <Thursday />
              <Friday />
              <Saturday />
              <Sunday />
            </DaysOfweek>
            <Hours>
              <Hour>3</Hour>
            </Hours>
          </ScheduleByWeek>
        </CalendarTrigger>
      </Triggers>
      <Actions>
        <Exec>
          <Command>powershell.exe</Command>
          <Arguments>-File C:\XRP-AutoTrading\Scripts\backup.ps1</Arguments>
          <WorkingDirectory>C:\XRP-AutoTrading</WorkingDirectory>
        </Exec>
      </Actions>
    </Task>
  </Actions>
</Context>
</Task>
```

#### 1.3 텔레그램 봇 알림 (백업 완료 시)

```powershell
# backup_notification.ps1
# 백업 완료 후 텔레그램 알림 전송

# .env 설정에서 토큰과 Chat ID 로드
$envPath = "C:\XRP-AutoTrading\Auto_trade00\.env"
$envContent = Get-Content $envPath

$botToken = ($envContent | Select-String "TELEGRAM_BOT_TOKEN=" | ForEach-Object {
    ($_ -split 'TELEGRAM_BOT_TOKEN="')[1].Split('"')[0]
})

$chatId = ($envContent | Select-String "TELEGRAM_CHAT_ID=" | ForEach-Object {
    ($_ -split 'TELEGRAM_CHAT_ID="')[1].Split('"')[0]
})

# 백업 완료 메시지
$message = "✅ 자동 백업 완료`n`n날짜: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n`n백업 항목:`n• 데이터베이스: candles_$dateStamp.db`n• 로그: logs_$dateStamp.zip`n• 설정: .env_$dateStamp"

# 텔레그램 메시지 전송
$url = "https://api.telegram.org/bot$botToken/sendMessage"

$body = @{
    chat_id = $chatId
    text = $message
    parse_mode = "Markdown"
}

Invoke-RestMethod -Uri $url -Method Post -Body ($body | ConvertTo-Json)
```

### 2. 복구 절차

#### 2.1 시스템 복구

```powershell
# 1. 서비스 중지
nssm stop XRPTradingBot

# 2. 최신 백업으로 복구
$latestDbBackup = Get-ChildItem "C:\XRP-AutoTrading\Backup\Data\*.db" | 
    Sort-Object LastWriteTime -Descending | Select-Object -First 1

Copy-Item $latestDbBackup.FullName -Destination "C:\XRP-AutoTrading\Auto_trade00\data\candles.db" -Force

# 3. 로그 복구 (필요 시)
$latestLogBackup = Get-ChildItem "C:\XRP-AutoTrading\Backup\Logs\*.zip" | 
    Sort-Object LastWriteTime -Descending | Select-Object -First 1

Expand-Archive -Path $latestLogBackup.FullName -DestinationPath "C:\XRP-AutoTrading\Auto_trade00\logs\" -Force

# 4. 서비스 재시작
nssm start XRPTradingBot

Write-Host "복구 완료"
```

---

## 🖥 문제 해결

### 일반적인 문제

#### 1. API 연결 실패

```powershell
# 해결 방법
# 1. API 키 확인
# Get-Content C:\XRP-AutoTrading\Auto_trade00\.env | Select-String "BITHUMB_API_KEY="
# 키를 ***** 로 마스킹하여 로그에서 노출 방지

# 2. 인터넷 연결 확인
Test-Connection -ComputerName api.bithumb.com -Port 443

# 3. 방화벽 설정 확인
# Windows Firewall: 인바운드 규칙 확인
# VPS 보안그룹: 방화벽 허용
```

#### 2. 데이터베이스 잠금

```powershell
# 해결 방법
# 1. 프로세스 중지
nssm stop XRPTradingBot

# 2. 잠금 파일 삭제
Remove-Item "C:\XRP-AutoTrading\Auto_trade00\data\candles.db.lck" -Force

# 3. 서비스 재시작
nssm start XRPTradingBot
```

#### 3. 메모리 부족

```powershell
# 해결 방법
# 1. 데이터 수집 기간 단축
python main.py --mode collect --days 30

# 2. 로그 레벨 조정
# .env 파일: LOG_LEVEL=WARNING

# 3. 주기 재시작
nssm restart XRPTradingBot
```

---

## 🖥 보안

### 보안 체크리스트

- [ ] `.env` 파일을 `.gitignore`에 추가 (GitHub 푸시 제외)
- [ ] API 키를 코드에 하드코딩하지 않음
- [ ] 민감한 정보를 로그에 기록하지 않음
- [ ] HTTPS만 사용
- [ ] 정기적인 보안 업데이트
- [ ] 2단계 인증 사용 (권장)

### 암호화

```python
# config.py의 API 키 암호화 예시
import os
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

def get_api_key():
    """암호화된 API 키 반환"""
    encrypted_key = os.getenv("ENCRYPTED_API_KEY")
    password = os.getenv("ENCRYPTION_PASSWORD")

    # 키 파싱
    salt = encrypted_key[:16]
    ciphertext = encrypted_key[16:]  # nonce + tag + ciphertext

    # 키 복호화
    key = PBKDF2(password.encode(), salt.encode(), dkLen=32)
    cipher = AES.new(key, AES.MODE_GCM)
    nonce = ciphertext[:12]
    tag = ciphertext[12:28]
    real_ciphertext = ciphertext[28:]

    # 복호화
    plaintext = cipher.decrypt_and_verify(nonce, real_ciphertext, tag)

    return plaintext.decode()
```

---

## 🖥 성능 최적화

### 데이터 수집 최적화

```python
# 캔들 데이터 배치 단위 수집
def fetch_candles_batch(self, start_date, end_date, batch_size=100):
    """배치 단위로 데이터 수집"""
    candles = []
    current_date = start_date

    while current_date < end_date:
        batch = self.api.get_candlestick(
            order_currency="XRP",
            payment_currency="KRW",
            chart_intervals="6h",
            count=min(batch_size, 100)
        )
        candles.extend(batch)
        current_date += timedelta(days=30)

    return candles
```

### 로깅 최적화

```python
# 로그 레벨 조정
# .env 파일: LOG_LEVEL="WARNING"  # 개발 외에는 WARNING 이상
```

---

## 🖥 주요 연�처

### 기술 지원

| 문제 유형 | 연�처 |
|------------|----------|
| 빗썸 API 문제 | [빗썸 고객센터](https://www.bithumb.com/customercenter/notice) |
| 텔레그램 문제 | [텔레그램 FAQ](https://telegram.org/faq) |
| Windows 서비스 문제 | [NSSM 포럼](https://nssm.cc/forums/) |

### 비상 연�시 (긴급)

- [빗썸 API 장애 시]: [빗썸 기술 지원](https://www.bithumb.com/customercenter/notice)
- [잔고 발생 시]: 24시간 내에 사용자에게 알림

---

## 🖥 배포 체크리스트

### 사전 체크

- [ ] `.env` 설정 파일 확인
- [ ] API 키 유효성 확인
- [ ] 텔레그램 봇 연동 확인
- [ ] 데이터베이스 생성 확인
- [ ] 로그 디렉토리 생성 확인
- [ ] 의존성 설치 완료
- [ ] 백테스트 완료 (승률 60% 이상)

### 기능 체크

- [ ] 데이터 수집 기능 테스트
- [ ] 백테스트 기능 테스트
- [ ] 전략 로직 테스트
- [ ] 텔레그램 알림 테스트

### 보안 체크

- [ ] `.env` 파일이 Git에 커밋되지 않았는지 확인
- [ ] API 키가 암호화되어 저장되었는지 확인
- [ ] 민감한 정보가 로그에 포함되지 않았는지 확인
- [ ] 방화벽 설정 확인

---

## 🖥 롤백 절차

문제 발생 시 즉시 롤백:

```powershell
# 1. 이전 버전으로 복원
git checkout tags/v1.0.0

# 또는
git checkout HEAD~1

# 2. 의존성 복원
pip install -r requirements.txt

# 3. 서비스 재시작
nssm restart XRPTradingBot
```

---

## 🖥 업데이트

### 정기 작업

| 주기 | 작업 | 설명 |
|------|------|------|
| 매일 | 로그 확인 | 에러 및 비정상 동작 확인 |
| 매일 | 거래 내역 확인 | 예상치 못한 거래 확인 |
| 주간 | 데이터 백업 | 데이터베이스 백업 |
| 주간 | 성과 분석 | 수익률 및 승률 분석 |
| 월간 | 파라미터 최적화 | 전략 파라미터 검토 |
| 월간 | API 키 교체 | 보안을 위한 키 교체 |

### 데이터 백업

```powershell
# 1. 데이터베이스 백업
Copy-Item "C:\XRP-AutoTrading\Auto_trade00\data\candles.db" -Destination "C:\XRP-AutoTrading\Backup\candles_$(Get-Date -Format 'yyyyMMdd').db"

# 2. 로그 백업
Compress-Archive -Path "C:\XRP-AutoTrading\Backup\logs_$(Get-Date -Format 'yyyyMMdd').tar.gz" -DestinationPath "C:\XRP-AutoTrading\Auto_trade00\logs\" -Force

# 3. 설정 백업
Copy-Item "C:\XRP-AutoTrading\Auto_trade00\.env" -Destination "C:\XRP-AutoTrading\Backup\.env_$(Get-Date -Format 'yyyyMMdd')"

# 4. 오래된 백업 삭제 (30일 이상)
Get-ChildItem "C:\XRP-AutoTrading\Backup\*.db" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-30)
} | ForEach-Object {
    Remove-Item $_.FullName
}
```

---

## 📊 모니터링 대시보드

### 시스템 상태 모니터링

```powershell
# 시스템 모니터링 스크립트
# monitor.ps1

# 1. 서비스 상태
$serviceStatus = nssm status XRPTradingBot

# 2. 최신 로그 확인 (최근 50줄)
$recentLogs = Get-Content "C:\XRP-AutoTrading\Auto_trade00\logs\app.log" -Tail 50

# 3. 디스크 사용량
$diskUsage = Get-PSDrive C | Select-Object Used, Free, @{Name="사용률 (%)"; Expression=[math]::round($_.Used / $_.Size * 100, 2)}

# 4. 메모리 사용량
$memoryUsage = Get-Process python | Select-Object WorkingSet, Id

# 결과 출력
Write-Host "=== 시스템 상태 ==="
Write-Host "서비스 상태: $serviceStatus"
Write-Host "디스크 사용률: $($diskUsage.'사용률 (%)')%"
Write-Host "메모리 사용량: $($memoryUsage.WorkingSet / 1MB) MB"
Write-Host ""
Write-Host "최근 로그 (최근 20줄):"
$recentLogs | Select-Object -Last 20
```

---

## 📞 지원

### 문제 신고

버그 리포트나 기능 요청은 다음 정보를 포함하여 신고해주세요:

1. 문제 유형 (버그 / 기능 요청 / 질문)
2. 재현 단계
3. 사용 환경 (OS, Python 버전, 배포 환경)
4. 에러 로그 (`logs/error.log`)
5. 스�린샷

### 연�처

- 이슈 트래커: https://github.com/kinsu128-art/xrp-auto-trading/issues
- 이메일: (이메일 주소)

---

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## ⚠️ 면책 조항

이 소프트웨어는 "있는 그대로" 제공되며, 명시적 또는 묵시적인 어떠한 보증도 하지 않습니다. 이 소프트웨어의 사용으로 인해 발생하는 어떠한 손실에 대해서도 책임지지 않습니다. 암호화폐 거래는 높은 리스크가 있으며, 투자 전에 신중히 검토하시기 바랍니다.

---

## 🙏 감사의 말

- [래리 윌리엄스](https://www.larrywilliams.com/) - 돌파 전략 개발
- [빗썸](https://www.bithumb.com/) - 거래소 API 제공
- [텔레그램](https://telegram.org/) - 알림 서비스 제공
- [NSSM](https://nssm.cc/) - Windows 서비스 관리

---

**문서 버전**: 1.0  
**작성일**: 2026-02-14  
**작성자**: Sisyphus AI Agent
