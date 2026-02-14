# Git 초기화 및 푸시 스크립트

# 1. Git 초기화
git init

# 2. .gitignore가 이미 존재하므로 건너뜀
# (이미 생성됨)

# 3. 모든 파일 스테이징
git add .

# 4. 첫 커밋
git commit -m "Initial commit: XRP auto-trading system with Larry Williams strategy

- Implemented data collection module (Bithumb API)
- Implemented Larry Williams breakthrough strategy engine
- Implemented backtester with performance metrics
- Implemented order executor with retry logic
- Implemented portfolio manager
- Implemented Telegram notification system
- Implemented visualizer for backtest results
- Implemented main controller with scheduling
- Added comprehensive documentation (README, DEPLOY)
- Added deployment script for Windows"

# 5. 원격 저장소 추가 (사용자 저장소 URL로 변경)
git remote add origin https://github.com/kinsu128-art/xrp-auto-trading.git

# 6. main 브랜치 생성
git branch -M main

# 7. 푸시
git push -u origin main
