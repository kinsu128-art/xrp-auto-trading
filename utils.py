"""
유틸리티 함수
"""
import logging
from typing import Any
from datetime import datetime


def log_exception(logger: logging.Logger, e: Exception, context: str = ""):
    """
    예외 로깅

    Args:
        logger: 로거
        e: 예외
        context: 추가 컨텍스트
    """
    logger.error(f"{context}: {type(e).__name__}: {str(e)}", exc_info=True)


def format_number(value: float, decimals: int = 2) -> str:
    """
    숫자 포맷팅 (콤마 구분)

    Args:
        value: 값
        decimals: 소수점 자릿수

    Returns:
        포맷팅된 문자열
    """
    return f"{value:,.{decimals}f}"


def format_currency(value: float, currency: str = "KRW") -> str:
    """
    통화 포맷팅

    Args:
        value: 값
        currency: 통화 심볼

    Returns:
        포맷팅된 통화 문자열
    """
    return f"{format_number(value)} {currency}"


def format_percent(value: float, decimals: int = 2) -> str:
    """
    퍼센트 포맷팅

    Args:
        value: 값
        decimals: 소수점 자릿수

    Returns:
        포맷팅된 퍼센트 문자열
    """
    return f"{value:+.{decimals}f}%"


def calculate_fee(amount: float, price: float, fee_rate: float) -> float:
    """
    수수료 계산

    Args:
        amount: 수량
        price: 가격
        fee_rate: 수수료율

    Returns:
        수수료
    """
    total_value = amount * price
    return total_value * fee_rate


def validate_positive_number(value: Any, name: str = "값") -> bool:
    """
    양수 검증

    Args:
        value: 검증할 값
        name: 값 이름

    Returns:
        유효하면 True, 아니면 False
    """
    try:
        num = float(value)
        return num > 0
    except (ValueError, TypeError):
        return False


def calculate_position_size(
    capital: float,
    price: float,
    risk_per_trade: float = 0.02,
    stop_loss_percent: float = 0.05
) -> float:
    """
    포지션 사이즈 계산

    Args:
        capital: 자본
        price: 가격
        risk_per_trade: 거래당 리스크 비율 (기본 2%)
        stop_loss_percent: 손절가 비율 (기본 5%)

    Returns:
        포지션 사이즈 (수량)
    """
    risk_amount = capital * risk_per_trade
    risk_per_unit = price * (stop_loss_percent / 100)
    position_size = risk_amount / risk_per_unit

    return position_size


def format_timestamp(timestamp_ms: int, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    타임스탬프 포맷팅

    Args:
        timestamp_ms: 밀리초 타임스탬프
        format_str: 포맷 문자열

    Returns:
        포맷팅된 시간 문자열
    """
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime(format_str)


def truncate(value: float, decimals: int = 8) -> float:
    """
    소수점 자릿수 제한

    Args:
        value: 값
        decimals: 소수점 자릿수

    Returns:
        자릿수가 제한된 값
    """
    multiplier = 10 ** decimals
    return int(value * multiplier) / multiplier


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    안전한 나눗셈

    Args:
        numerator: 분자
        denominator: 분모
        default: 분모가 0일 때 반환할 기본값

    Returns:
        나눗셈 결과
    """
    if denominator == 0:
        return default
    return numerator / denominator
