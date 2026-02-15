"""
데이터 저장소 모듈
"""
import sqlite3
import pandas as pd
from typing import List, Optional, Dict
from datetime import datetime
import os


class DataStorage:
    """데이터 저장소 클래스"""

    def __init__(self, db_path: str = "data/candles.db"):
        """
        데이터 저장소 초기화

        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path

        # 데이터베이스 디렉토리 생성
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 테이블 생성
        self._create_tables()

    def _create_tables(self):
        """데이터베이스 테이블 생성"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 캔들 데이터 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS candles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER UNIQUE NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON candles(timestamp)
            """)

            conn.commit()

    def save_candles(self, candles: List[Dict], order_currency: str = "XRP") -> int:
        """
        캔들 데이터 저장

        Args:
            candles: 캔들 데이터 리스트
            order_currency: 주문 통화

        Returns:
            저장된 데이터 개수
        """
        if not candles:
            return 0

        saved_count = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for candle in candles:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO candles
                        (timestamp, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        candle["timestamp"],
                        candle["open"],
                        candle["high"],
                        candle["low"],
                        candle["close"],
                        candle["volume"]
                    ))
                    if cursor.rowcount > 0:
                        saved_count += 1
                except sqlite3.IntegrityError:
                    # 중복 데이터 무시
                    pass

            conn.commit()

        return saved_count

    def load_candles(
        self,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        캔들 데이터 로드

        Args:
            start_timestamp: 시작 타임스탬프
            end_timestamp: 종료 타임스탬프
            limit: 가져올 최대 개수 (최신 데이터부터)

        Returns:
            캔들 데이터 리스트
        """
        query = "SELECT timestamp, open, high, low, close, volume FROM candles WHERE 1=1"
        params = []

        if start_timestamp:
            query += " AND timestamp >= ?"
            params.append(start_timestamp)

        if end_timestamp:
            query += " AND timestamp <= ?"
            params.append(end_timestamp)

        # limit이 있으면 최신 데이터를 가져오기 위해 DESC로 정렬
        if limit:
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
        else:
            query += " ORDER BY timestamp ASC"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        # 결과를 딕셔너리 리스트로 변환
        candles = []
        for row in rows:
            candles.append({
                "timestamp": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5]
            })

        # limit을 사용한 경우 시간순으로 재정렬
        if limit:
            candles.reverse()

        return candles

    def get_latest_candle(self) -> Optional[Dict]:
        """
        최신 캔들 조회

        Returns:
            최신 캔들 데이터 (없으면 None)
        """
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM candles
            ORDER BY timestamp DESC
            LIMIT 1
        """

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()

        if row:
            return {
                "timestamp": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5]
            }

        return None

    def get_candles_after(self, timestamp: int) -> List[Dict]:
        """
        특정 타임스탬프 이후의 캔들 데이터 조회

        Args:
            timestamp: 기준 타임스탬프

        Returns:
            캔들 데이터 리스트
        """
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM candles
            WHERE timestamp > ?
            ORDER BY timestamp ASC
        """

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (timestamp,))
            rows = cursor.fetchall()

        candles = []
        for row in rows:
            candles.append({
                "timestamp": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5]
            })

        return candles

    def get_candles_before(self, timestamp: int, count: int = 5) -> List[Dict]:
        """
        특정 타임스탬프 이전의 캔들 데이터 조회

        Args:
            timestamp: 기준 타임스탬프
            count: 가져올 개수

        Returns:
            캔들 데이터 리스트 (최신 순)
        """
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM candles
            WHERE timestamp < ?
            ORDER BY timestamp DESC
            LIMIT ?
        """

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (timestamp, count))
            rows = cursor.fetchall()

        candles = []
        for row in rows:
            candles.append({
                "timestamp": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5]
            })

        # 시간순 정렬 (오름차순)
        candles.reverse()
        return candles

    def to_dataframe(self, candles: List[Dict]) -> pd.DataFrame:
        """
        캔들 데이터를 DataFrame으로 변환

        Args:
            candles: 캔들 데이터 리스트

        Returns:
            pandas DataFrame
        """
        if not candles:
            return pd.DataFrame()

        df = pd.DataFrame(candles)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

        return df

    def delete_old_candles(self, days: int = 365) -> int:
        """
        오래된 캔들 데이터 삭제

        Args:
            days: 보관할 일수

        Returns:
            삭제된 데이터 개수
        """
        # 기준 타임스탬프 계산
        cutoff_timestamp = int((datetime.now().timestamp() - days * 86400) * 1000)

        query = "DELETE FROM candles WHERE timestamp < ?"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (cutoff_timestamp,))
            deleted_count = cursor.rowcount
            conn.commit()

        return deleted_count

    def get_count(self) -> int:
        """
        저장된 캔들 데이터 개수 조회

        Returns:
            캔들 데이터 개수
        """
        query = "SELECT COUNT(*) FROM candles"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            count = cursor.fetchone()[0]

        return count

    def get_timestamp_range(self) -> tuple:
        """
        저장된 캔들의 타임스탬프 범위 조회

        Returns:
            (최소 타임스탬프, 최대 타임스탬프)
        """
        query = "SELECT MIN(timestamp), MAX(timestamp) FROM candles"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()

        if row[0] is None or row[1] is None:
            return (0, 0)

        return (row[0], row[1])
