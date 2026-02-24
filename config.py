"""
설정 관리 모듈
"""
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    """시스템 설정 클래스"""

    # 빗썸 API 설정
    BITHUMB_API_KEY = os.getenv("BITHUMB_API_KEY", "")
    BITHUMB_API_SECRET = os.getenv("BITHUMB_API_SECRET", "")

    # 텔레그램 봇 설정
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # 거래 설정
    TRADING_CURRENCY = os.getenv("TRADING_CURRENCY", "KRW")
    ORDER_CURRENCY = os.getenv("ORDER_CURRENCY", "XRP")

    # 전략 설정
    BREAKTHROUGH_RATIO = float(os.getenv("BREAKTHROUGH_RATIO", "0.5"))
    CANDLE_PERIOD = os.getenv("CANDLE_PERIOD", "6h")
    NUM_CANDLES_FOR_AVG = int(os.getenv("NUM_CANDLES_FOR_AVG", "5"))

    # 로깅 설정
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
    ERROR_LOG_FILE = os.getenv("ERROR_LOG_FILE", "logs/error.log")
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "7"))  # 로그 보관 일수

    # API 설정
    BITHUMB_API_URL = os.getenv("BITHUMB_API_URL", "https://api.bithumb.com")

    # 재시도 설정
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "1"))  # 초

    # 데이터베이스 설정
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/candles.db")


# 설정 유효성 검사
def validate_config(config: Config) -> bool:
    """
    설정 유효성을 검사합니다.

    Args:
        config: 설정 객체

    Returns:
        bool: 설정이 유효하면 True, 아니면 False
    """
    if not config.BITHUMB_API_KEY or not config.BITHUMB_API_SECRET:
        print("⚠️  경고: 빗썸 API 키가 설정되지 않았습니다.")
        print("   .env 파일에 BITHUMB_API_KEY와 BITHUMB_API_SECRET를 설정하세요.")
        return False

    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("⚠️  경고: 텔레그램 설정이 완료되지 않았습니다.")
        print("   .env 파일에 TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 설정하세요.")
        return False

    # CANDLE_PERIOD 형식 검증 (예: "6h", "1d", "12h")
    period = config.CANDLE_PERIOD
    if not period or len(period) < 2:
        print(f"⚠️  경고: CANDLE_PERIOD 형식이 잘못되었습니다: '{period}'")
        print("   '6h', '12h', '1d' 형식으로 설정하세요.")
        return False

    unit = period[-1]
    try:
        value = int(period[:-1])
        if value <= 0:
            raise ValueError
    except ValueError:
        print(f"⚠️  경고: CANDLE_PERIOD 형식이 잘못되었습니다: '{period}'")
        print("   '6h', '12h', '1d' 형식으로 설정하세요.")
        return False

    if unit not in ("h", "d"):
        print(f"⚠️  경고: CANDLE_PERIOD 단위가 잘못되었습니다: '{unit}'")
        print("   시간(h) 또는 일(d) 단위만 지원합니다.")
        return False

    return True
