FROM python:3.11-slim

# 시스템 패키지 설치 (matplotlib 한글 폰트 + 타임존)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-nanum \
    fontconfig \
    tzdata \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# 타임존 설정 (한국시간)
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# matplotlib 헤드리스 백엔드
ENV MPLBACKEND=Agg

# 작업 디렉토리
WORKDIR /app

# 의존성 설치 (캐시 활용을 위해 먼저 복사)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 데이터/로그/리포트 디렉토리 생성
RUN mkdir -p data logs reports

# 헬스체크
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "import requests; requests.get('https://api.bithumb.com/public/ticker/XRP_KRW', timeout=5)" || exit 1

# 기본 실행: 실전 모드 (--confirm으로 대화형 프롬프트 스킵)
ENTRYPOINT ["python", "main.py"]
CMD ["--mode", "live", "--confirm"]
