@echo off
REM 배포 스크립트 (Windows)

echo ========================================
echo   XRP 자동매매 시스템 배포
echo ========================================
echo.

REM 1. 의존성 설치 확인
echo [1/7] 의존성 확인 중...
pip show requests >nul 2>&1
if errorlevel 1 (
    echo 필요한 패키지가 설치되지 않았습니다.
    echo 설치를 진행합니다...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: 의존성 설치 실패
        pause
        exit /b 1
    )
) else (
    echo   모든 의존성이 설치되어 있습니다.
)
echo.

REM 2. 가상 환경 확인
echo [2/7] 가상 환경 확인 중...
if not exist "venv\Scripts\activate.bat" (
    echo 가상 환경을 생성합니다...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: 가상 환경 생성 실패
        pause
        exit /b 1
    )
    echo   가상 환경 생성 완료.
) else (
    echo   가상 환경이 이미 존재합니다.
)
echo.

REM 3. 설정 파일 확인
echo [3/7] 설정 파일 확인 중...
if not exist ".env" (
    echo .env 파일을 복사합니다...
    copy .env.example .env
    echo.
    echo   ! .env 파일을 수정해주세요 !
    echo   ! .env 파일에 API 키와 텔레그램 토큰을 입력하세요.
    echo.
    pause
) else (
    echo   .env 파일이 존재합니다.
)
echo.

REM 4. 디렉토리 생성
echo [4/7] 필수 디렉토리 생성 중...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "reports" mkdir reports
if not exist "tests" mkdir tests
echo   디렉토리 생성 완료.
echo.

REM 5. Python 버전 확인
echo [5/7] Python 버전 확인 중...
python --version
echo.

REM 6. 구문 검사
echo [6/7] Python 구문 검사 중...
python -m py_compile config.py
python -m py_compile bithumb_api.py
python -m py_compile data_collector.py
python -m py_compile data_storage.py
python -m py_compile strategy_engine.py
python -m py_compile backtester.py
python -m py_compile visualizer.py
python -m py_compile order_executor.py
python -m py_compile portfolio.py
python -m py_compile notification.py
python -m py_compile logger.py
python -m py_compile main.py
python -m py_compile utils.py
python -m py_compile exceptions.py
echo   구문 검사 완료.
echo.

REM 7. 테스트 실행 (선택)
echo [7/7] 테스트 실행 중...
echo 테스트를 실행하시겠습니까? (Y/N)
set /p run_test=
if /i "%run_test%"=="Y" (
    python -m pytest tests/ -v
    if errorlevel 1 (
        echo WARNING: 일부 테스트가 실패했습니다.
    ) else (
        echo   모든 테스트가 통과했습니다.
    )
) else (
    echo   테스트를 건너뜁니다.
)
echo.

echo ========================================
echo   배포 완료!
echo ========================================
echo.
echo 다음 명령어로 시스템을 실행할 수 있습니다:
echo.
echo   데이터 수집:
echo     python main.py --mode collect --days 365
echo.
echo   백테스트:
echo     python main.py --mode backtest --days 365
echo.
echo   실전 모드:
echo     python main.py --mode live
echo.
echo 참고: 실전 모드 실행 전에 .env 파일을 확인하세요.
echo.
pause
