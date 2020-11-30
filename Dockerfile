FROM balenalib/raspberry-pi-alpine-python:3.9
COPY . /yt_downloader
RUN python -m pip install --upgrade pip
RUN pip install flask
RUN pip install youtube_dl

