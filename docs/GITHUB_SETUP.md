# GitHub 저장소 설정 가이드

## 📋 요구사항

- GitHub 계정
- Git 설치 ([다운로드](https://git-scm.com/downloads))

## 🚀 단계별 설정

### 1단계: GitHub 저장소 생성

1. [GitHub](https://github.com) 접속 후 로그인
2. 우측 상단 `+` 버튼 클릭 → `New repository`
3. 저장소 설정:
   - **Repository name**: `xrp-auto-trading`
   - **Public/Private**: 선택 (개인용은 Private 추천)
   - **"Initialize this repository"** ❌ 체크 해제 (초기화 없이 빈 저장소 생성)
   - `Create repository` 클릭

### 2단계: 프로젝트 초기화

#### Windows 사용자
```bash
# 명령 프롬프트(CMD) 또는 PowerShell에서 실행

# 1. 프로젝트 디렉토리로 이동
cd D:\Vibe\Auto_trade00

# 2. Git 초기화
git init

# 3. 모든 파일 스테이징
git add .

# 4. 첫 커밋
git commit -m "Initial commit: XRP auto-trading system with Larry Williams strategy"

# 5. 원격 저장소 추가
git remote add origin https://github.com/kinsu128-art/xrp-auto-trading.git

# 6. main 브랜치 생성
git branch -M main

# 7. 푸시 (GitHub 로그인이 필요할 수 있음)
git push -u origin main
```

#### Linux/Mac 사용자
```bash
# 터미널에서 실행

# 1. 프로젝트 디렉토리로 이동
cd /path/to/Auto_trade00

# 2. Git 초기화
git init

# 3. 모든 파일 스테이징
git add .

# 4. 첫 커밋
git commit -m "Initial commit: XRP auto-trading system with Larry Williams strategy"

# 5. 원격 저장소 추가
git remote add origin https://github.com/kinsu128-art/xrp-auto-trading.git

# 6. main 브랜치 생성
git branch -M main

# 7. 푸시
git push -u origin main
```

### 3단계: 스크립트 사용

Windows 사용자는 생성된 배치 파일을 사용할 수 있습니다:

```bash
# git_push.bat 파일 실행
git_push.bat
```

### 4단계: 확인

푸시 후 [GitHub 저장소](https://github.com/kinsu128-art/xrp-auto-trading)에서 파일들이 정상적으로 업로드되었는지 확인하세요.

---

## ⚠️ GitHub 인증

### HTTPS 사용 시 (기본)
푸시할 때 GitHub 사용자명과 비밀번호(또는 Personal Access Token)를 입력해야 합니다.

```bash
Username: 'your-github-username'
Password: 'your-personal-access-token'  # 비밀번호 대신 PAT 사용 권장
```

### Personal Access Token (PAT) 생성

1. GitHub 로그인 → 우측 상단 프로필 아이콘 → Settings
2. 좌측 메뉴 → **Developer settings**
3. **Personal access tokens** → **Tokens (classic)**
4. **Generate new token (classic)** 클릭
5. 설정:
   - Note: `XRP Auto Trading Bot`
   - Expiration: `No expiration` 또는 기간 선택
   - Scopes: `repo` 체크
6. `Generate token` 클릭
7. 생성된 토큰을 **복사** (다시 볼 수 없으므로 반드시 복사!)

### PAT를 사용하여 푸시

```bash
# HTTPS URL에 PAT 포함
git push https://YOUR_TOKEN@github.com/kinsu128-art/xrp-auto-trading.git
```

---

## 🔐 보안 팁

### `.gitignore` 확인

다음 파일들이 `.gitignore`에 포함되어 있는지 확인:
- `.env` (API 키 포함)
- `venv/` (가상 환경)
- `*.log` (로그 파일)
- `data/candles.db` (데이터베이스)
- `__pycache__/` (Python 캐시)

### `.env` 파일이 커밋되지 않도록

```bash
# .env가 이미 스테이징된 경우
git rm --cached .env
git commit -m "Remove .env from tracking"
git push
```

---

## 🐛 문제 해결

### 오류: "fatal: remote origin already exists"

```bash
git remote remove origin
git remote add origin https://github.com/kinsu128-art/xrp-auto-trading.git
```

### 오류: "Authentication failed"

```bash
# GitHub 자격 증명을 재설정
git credential-manager-core erase
```

### 오류: "Updates were rejected"

```bash
# 원격 저장소의 변경사항 가져오기
git pull origin main --rebase
# 다시 푸시
git push -u origin main
```

---

## 📊 푸시 후 작업

### 1. Issues 탭 설정

- [Bug] 버그 리포트
- [Feature] 기능 요청
- [Enhancement] 개선 제안
- [Question] 질문

### 2. README 확인

저장소 메인 페이지에서 README가 잘 보이는지 확인하세요.

### 3. Actions 설정 (선택사항)

CI/CD 파이프라인을 설정하려면 `.github/workflows/` 디렉토리에 워크플로우 파일을 추가하세요.

---

## 🎯 다음 단계

푸시가 완료되면 다음을 수행하세요:

1. ✅ 저장소에서 모든 파일이 보이는지 확인
2. ✅ README가 잘 렌더링되는지 확인
3. ✅ `.env` 파일이 저장소에 포함되지 않았는지 확인
4. ✅ 다른 컴퓨터에서 `git clone` 테스트
5. ✅ Issues 탭에서 이슈 템플릿 설정 (선택사항)

---

**문서 버전**: 1.0  
**작성일**: 2026-02-14  
**작성자**: Sisyphus AI Agent
