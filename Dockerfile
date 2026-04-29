FROM python:3.11

RUN apt-get update && apt-get install -y \
ffmpeg \
aria2 \
gcc \
libffi-dev \
wget \
curl \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app/

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r Installer

ENV COOKIES_FILE_PATH=/app/modules/youtube_cookies.txt
ENV PYTHONUNBUFFERED=1

CMD ["python3","modules/main.py"]
