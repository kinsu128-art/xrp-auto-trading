"""
예외 처리 모듈
"""


class TradingException(Exception):
    """트레이딩 기본 예외"""
    pass


class DataException(TradingException):
    """데이터 관련 예외"""
    pass


class StrategyException(TradingException):
    """전략 관련 예외"""
    pass


class OrderException(TradingException):
    """주문 관련 예외"""
    pass


class NotificationException(TradingException):
    """알림 관련 예외"""
    pass


class ConfigException(TradingException):
    """설정 관련 예외"""
    pass
