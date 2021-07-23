FROM balenalib/raspberry-pi-alpine-python:latest-latest-run
RUN pip install --upgrade pip && pip install wheel 
RUN pip install --no-cache-dir flask && pip install --no-cache-dir youtube_dl
COPY yt_downloader /yt_downloader
CMD ["/usr/local/bin/python", "/yt_downloader/yt_music_downloader.py"]


