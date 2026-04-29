FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
ffmpeg \
aria2 \
gcc \
libffi-dev \
python3-pip \
wget \
curl \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app/

RUN pip install --upgrade pip
RUN pip install -r Installer

ENV COOKIES_FILE_PATH="/modules/youtube_cookies.txt"
ENV PYTHONUNBUFFERED=1

CMD python3 modules/main.py
