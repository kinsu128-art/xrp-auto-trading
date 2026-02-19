"""
로거 설정 모듈
"""
import logging
import os
import glob
from datetime import datetime, timedelta
from typing import Optional, Dict
from logging.handlers import RotatingFileHandler


def setup_logger(
    name: str = __name__,
    log_level: str = "INFO",
    log_file: str = "logs/app.log",
    error_log_file: str = "logs/error.log"
) -> logging.Logger:
    """
    로거 설정

    Args:
        name: 로거 이름
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로
        error_log_file: 에러 로그 파일 경로

    Returns:
        설정된 로거
    """
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 로그 디렉토리 생성
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # 포맷터 설정
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 (모든 로그)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 에러 파일 핸들러 (ERROR 이상)
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    return logger


class TradeLogger:
    """거래 로거"""

    def __init__(self, logger: logging.Logger):
        """
        거래 로거 초기화

        Args:
            logger: 기본 로거
        """
        self.logger = logger

    def log_buy(
        self,
        currency: str,
        amount: float,
        price: float,
        breakthrough_price: Optional[float] = None,
        avg_close: Optional[float] = None
    ):
        """
        매수 기록

        Args:
            currency: 코인 심볼
            amount: 매수 수량
            price: 매수 가격
            breakthrough_price: 돌파 기준선 가격
            avg_close: 5봉 종가 평균
        """
        log_msg = f"📥 매수: {currency} {amount:.8f} @ {price:.2f} KRW (총 {amount * price:,.0f} KRW)"

        if breakthrough_price is not None:
            log_msg += f" | 돌파 기준선: {breakthrough_price:.2f} KRW"
        if avg_close is not None:
            log_msg += f" | 5봉 종가 평균: {avg_close:.2f} KRW"

        self.logger.info(log_msg)

    def log_sell(
        self,
        currency: str,
        amount: float,
        price: float,
        profit: float,
        profit_percent: float,
        duration_hours: float
    ):
        """
        매도 기록

        Args:
            currency: 코인 심볼
            amount: 매도 수량
            price: 매도 가격
            profit: 수익 (KRW)
            profit_percent: 수익률 (%)
            duration_hours: 보유 시간 (시간)
        """
        profit_emoji = "📈" if profit > 0 else "📉"
        log_msg = (
            f"{profit_emoji} 매도: {currency} {amount:.8f} @ {price:.2f} KRW "
            f"| 수익: {profit:+,.0f} KRW ({profit_percent:+.2f}%) "
            f"| 보유 시간: {duration_hours:.1f}시간"
        )

        self.logger.info(log_msg)

    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[dict] = None
    ):
        """
        에러 기록

        Args:
            error_type: 에러 타입
            error_message: 에러 메시지
            context: 추가 컨텍스트
        """
        log_msg = f"❌ {error_type}: {error_message}"

        if context:
            log_msg += f" | 컨텍스트: {context}"

        self.logger.error(log_msg, exc_info=True)

    def log_system_start(self):
        """시스템 시작 기록"""
        self.logger.info("=" * 50)
        self.logger.info("🚀 XRP 자동매매 시스템 시작")
        self.logger.info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 50)

    def log_system_stop(self):
        """시스템 종료 기록"""
        self.logger.info("=" * 50)
        self.logger.info("⏹️  XRP 자동매매 시스템 종료")
        self.logger.info(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 50)

    def log_candle_close(self, candle: Dict):
        """
        캔들 마감 기록

        Args:
            candle: 캔들 데이터
        """
        log_msg = (
            f"🕐 캔들 마감: 시가={candle['open']:.2f}, "
            f"고가={candle['high']:.2f}, 저가={candle['low']:.2f}, "
            f"종가={candle['close']:.2f}, 거래량={candle['volume']:,.0f}"
        )
        self.logger.debug(log_msg)

    def log_balance(self, krw: float, coin: float, total: float):
        """
        잔고 기록

        Args:
            krw: KRW 잔고
            coin: 코인 잔고
            total: 총 자산
        """
        log_msg = f"💼 잔고: KRW={krw:,.0f}, XRP={coin:.8f}, 총 자산={total:,.0f} KRW"
        self.logger.info(log_msg)


class MetricsLogger:
    """메트릭 로거"""

    def __init__(self, logger: logging.Logger):
        """
        메트릭 로거 초기화

        Args:
            logger: 기본 로거
        """
        self.logger = logger
        self.api_call_count = 0
        self.trade_count = 0
        self.error_count = 0

    def log_api_call(self, endpoint: str, success: bool):
        """
        API 호출 기록

        Args:
            endpoint: API 엔드포인트
            success: 성공 여부
        """
        self.api_call_count += 1
        self.logger.debug(f"📡 API 호출 #{self.api_call_count}: {endpoint} ({'성공' if success else '실패'})")

    def log_trade(self):
        """거래 기록"""
        self.trade_count += 1
        self.logger.info(f"📊 거래 #{self.trade_count} 실행됨")

    def log_error(self, error_type: str):
        """
        에러 기록

        Args:
            error_type: 에러 타입
        """
        self.error_count += 1
        self.logger.error(f"❌ 에러 #{self.error_count}: {error_type}")

    def get_summary(self) -> dict:
        """
        메트릭 요약

        Returns:
            메트릭 요약
        """
        return {
            "api_call_count": self.api_call_count,
            "trade_count": self.trade_count,
            "error_count": self.error_count
        }

    def reset(self):
        """메트릭 리셋"""
        self.api_call_count = 0
        self.trade_count = 0
        self.error_count = 0


def cleanup_old_logs(log_file: str, retention_days: int = 7, logger: Optional[logging.Logger] = None):
    """
    오래된 로그 내역 정리

    1) 메인 로그 파일에서 retention_days 이전 항목 제거
    2) 오래된 로테이션 백업 파일 삭제

    Args:
        log_file: 로그 파일 경로 (예: logs/app.log)
        retention_days: 보관 일수
        logger: 로거 (정리 결과 기록용)
    """
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
    total_removed = 0

    # 1) 메인 로그 파일에서 오래된 항목 제거
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            original_count = len(lines)
            recent_lines = []

            for line in lines:
                # 로그 형식: "2026-02-20 06:00:11 - ..." 에서 날짜 추출
                if len(line) >= 19:
                    try:
                        log_date = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
                        if log_date >= cutoff_date:
                            recent_lines.append(line)
                            continue
                    except ValueError:
                        pass
                    # 날짜 파싱 실패한 줄은 직전 줄의 연속(stacktrace 등)으로 간주
                    # recent_lines에 이미 항목이 있으면 포함
                    if recent_lines:
                        recent_lines.append(line)
                else:
                    if recent_lines:
                        recent_lines.append(line)

            removed_count = original_count - len(recent_lines)

            if removed_count > 0:
                with open(log_file, "w", encoding="utf-8") as f:
                    f.writelines(recent_lines)
                total_removed += removed_count

        except Exception as e:
            if logger:
                logger.error(f"로그 파일 정리 실패 ({log_file}): {e}")

    # 2) 오래된 로테이션 백업 파일 삭제 (app.log.1, app.log.2, ...)
    backup_pattern = f"{log_file}.*"
    for backup_file in glob.glob(backup_pattern):
        try:
            modified_time = datetime.fromtimestamp(os.path.getmtime(backup_file))
            if modified_time < cutoff_date:
                os.remove(backup_file)
                total_removed += 1
                if logger:
                    logger.debug(f"오래된 백업 로그 삭제: {backup_file}")
        except Exception as e:
            if logger:
                logger.error(f"백업 로그 삭제 실패 ({backup_file}): {e}")

    if logger:
        logger.info(f"로그 정리 완료: {log_file} ({retention_days}일 이전 항목 {total_removed}건 제거)")

    return total_removed
