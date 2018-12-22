from flask import Flask
import youtube_dl
import threading
import queue
import time
import json

flask = Flask(__name__)


class DownloadThread(threading.Thread):
    def __init__(self, queue, song_id, url):
        super(DownloadThread, self).__init__()
        self.stopRequest = threading.Event()
        self.queue = queue
        self.song_id = song_id
        self.url = url

    def run(self):
        counter = 1
        while(not self.stopRequest.is_set()):
            data = {"thread_id": threading.get_ident(), "song_id": self.song_id, "data": {
                "url": self.url, "counter": counter}}
            self.queue.put(data)
            counter = counter+1
            time.sleep(0.1)
        print("download thread exit")

    def stop(self):
        self.stopRequest.set()
        


class DownloadManager(threading.Thread):
    def __init__(self):
        super(DownloadManager, self).__init__()
        self.stopRequest = threading.Event()
        self.queue = queue.Queue()
        self.threads = {}
        self.download_status = {}
        self.locker = threading.Lock()
        self.start()

    def run(self):
        thr = DownloadThread(self.queue, "1234", "asdfasdfasf")
        thr.start()
        self.threads[thr.ident] = thr

        time.sleep(0.5)
        thr = DownloadThread(self.queue, "9877", "blekota")
        thr.start()
        self.threads[thr.ident] = thr

        while(not self.stopRequest.is_set()):
            try:
                data = self.queue.get(timeout=1)
                with self.locker:
                    self.download_status[data['song_id']] = data['data']
            except queue.Empty:
                pass
        print("manager thread exit")

    def getStatus(self):
        with self.locker:
            status = self.download_status.copy()
        return status

    def trystop(self):
        for id in self.threads.keys():
            self.threads[id].stop()
        for id in self.threads.keys():
            if(not self.threads[id].isAlive()):
                self.threads[id].join()

        self.stopRequest.set()
        self.join(1)
        print(self.isAlive())

    def stop(self):
        stopped = False
        while(not stopped):
            try:
                self.trystop()
                stopped = True
            except KeyboardInterrupt:
                pass
       

# Queue of files is stored in separate files with name:
# - URL.to_download - files queued to be downloaded (both not started yet and partially downloaded)
# - URL.failed - files, which cannot be downloaded

# Music files can exists in two different versions representing current status of download progress.
# - name-URL.ext.part - files partially downloaded (in progress)
# - name.ext - files fully downloaded


# Adds url to download queue
# This method doesn't start download instantly, but creates entry represented by temporary file, which is then
# used by downloadManager to plan further downloads.
# Temporary file name has following structure: URL.to_download
#
# parameter url accepts two formats of download urls:
# -long:
# https://www.youtube.com/watch?v=5yac1YCGzNU&feature=youtu.be
# -short:
# https://youtu.be/5yac1YCGzNU

def addUrl(url):
    print(url)

# Scans periodically files, looking for URL.to_download filenames. Internal queue is build based on detected files.
# Queue is then distributed across download threads (actually only one thread is used)


def on_download(progress):
    print(progress)
    print(progress['status'])


def download_test():
    ydl_opts = {
        'quiet': 'true',
        'format': 'bestaudio/best',
        'progress_hooks': [on_download]
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download(['https://youtu.be/5yac1YCGzNU'])


downloader = DownloadManager()


@flask.route('/')
def hello():
    return json.dumps(downloader.getStatus())


if __name__ == '__main__':

    try:
        flask.run(port=80)
    except KeyboardInterrupt:
        pass
    finally:
        downloader.stop()

    print("main thread exit")