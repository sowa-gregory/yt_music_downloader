from flask import Flask
import youtube_dl
import threading
import queue
import time
import json
import os
import collections
import logging

flask = Flask(__name__, static_url_path='/static')

class Config(object):
    _downloadPath = None
    _removeTimeout = 30

    @staticmethod
    def getDownloadPath():
        return Config._downloadPath

    @staticmethod
    def setDownloadPath(path):
        if(not os.path.isdir(path)):
            raise Exception("invalid download path")
        Config._downloadPath = path

    @staticmethod
    def setRemoveTimeout(seconds):
        Config._removeTimeout = seconds

    @staticmethod
    def getRemoveTimeout():
        return Config._removeTimeout


class DownloadThread(threading.Thread):
    def __init__(self, queue, song_id):
        super(DownloadThread, self).__init__()
        self.queue = queue
        self.song_id = song_id

    def _fileNameToTitle(self, fileName):
        # remove directory prefix from filename
        title = fileName[fileName.rindex(os.sep)+1:]
        # remove extenstion from filename
        return title[:title.rindex('.')]

    def onDownload(self, download_data):
        # status fields
        # song_id title status percent eta
        title = self._fileNameToTitle(download_data['filename'])
        status = download_data['status']

        if(status == "finished"):
            eta = "-"
            percent = "100%"
        else:
            eta = download_data['_eta_str']
            percent = download_data['_percent_str']

        data = {self.song_id: {"title": title,
                               "status": status, "percent": percent, "eta": eta}}
        self.queue.put(data)

    def run(self):
        ydl_opts = {'quiet': 'true', 'format': 'bestaudio/best',
                    'outtmpl': Config.getDownloadPath()+'/%(title)s.%(ext)s',
                    'progress_hooks': [self.onDownload]}

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download(["https://youtu.be/"+self.song_id])
        except youtube_dl.utils.DownloadError as error:
            data = {self.song_id: {"title": "{---}",
                                   "status": "failed", "percent": "-", "eta": "-"}}
            self.queue.put(data)

        print("download thread exit\n")


class DownloadManager(threading.Thread):
    def __init__(self):
        super(DownloadManager, self).__init__()
        self.stopRequest = threading.Event()
        self.statusQueue = queue.Queue()
        self.threads = []
        self.downloadStatus = collections.OrderedDict()
        self.locker = threading.Lock()
        self.downloadList = []
        self.maxThreads = 2

    def addSongToDownloadQueue(self, songId):
        with open(Config.getDownloadPath()+"/"+songId+".to_download", "w"):
            pass
        with self.locker:
            self.downloadList.append(songId)
        data = {songId: {"title": "{---}",
                         "status": "waiting", "percent": "-", "eta": "-"}}
        self.setDownloadStatus(data)

    def popDownloadQueue(self):
        with self.locker:
            if self.downloadList:
                return self.downloadList.pop()

    def scanToDownload(self):
        pass

    def startDownload(self):
        ''' starts download of next song when list of songs is not empty and there are awaiting worker threads '''
        songId = self.popDownloadQueue()
        if(songId != None and len(self.threads) < self.maxThreads):
            thr = DownloadThread(self.statusQueue, songId)
            thr.start()
            self.threads.append(thr)
            return True
        return False

    def updateThreadsStatus(self):
        ''' Updates running status of managed download threads. '''
        self.threads = [thr for thr in self.threads if thr.is_alive()]

    def checkOutdatedStatuses(self):
        currentTime = time.time()
        removeTimeout = Config.getRemoveTimeout()
        for key in list(self.downloadStatus.keys()):
            currentStatus = self.downloadStatus[key]
            if(currentStatus['status'] == 'finished' and currentTime-currentStatus['update_time'] > removeTimeout):
                print("status remove")
                del self.downloadStatus[key]

    def run(self):
        self.scanToDownload()

        while(not self.stopRequest.is_set()):
            self.updateThreadsStatus()
            self.checkOutdatedStatuses()
            while(self.startDownload() == True):
                pass
            try:
                status = self.statusQueue.get(timeout=5)
                songId = list(status.keys())[0]

                if(status[songId]['status'] == "finished"):
                    os.remove(Config.getDownloadPath() +
                              "/"+songId+".to_download")
                # move status into data
                self.setDownloadStatus(status)
            except queue.Empty:
                pass

    def setDownloadStatus(self, status):
        # this is the method to get first key value
        songId = list(status.keys())[0]
        with self.locker:
            tempStatus = status[songId]
            tempStatus["update_time"] = time.time()
            self.downloadStatus[songId] = tempStatus

    def getDownloadStatus(self):
        with self.locker:
            return self.downloadStatus.copy()

    def trystop(self):
        for thr in self.threads:
            if(not thr.is_alive()):
                thr.join()

        self.stopRequest.set()
        self.join(1)

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

# Scans periodically files, looking for URL.to_download filenames. Internal queue is build based on detected files.
# Queue is then distributed across download threads (actually only one thread is used)


@flask.route('/newsong/<string:song_id>')
def newSong(song_id):
    downloader.addSongToDownloadQueue(song_id)
    return "ok"


@flask.route('/status')
def getStatus():
    return json.dumps(downloader.getDownloadStatus())


@flask.route('/')
def root():
    return flask.send_static_file('index.html')


if __name__ == '__main__':

    downloader = None
    try:
        Config.setDownloadPath("/music")
        Config.setRemoveTimeout(300)
        downloader = DownloadManager()
        downloader.start()

        # flask uses strange logger name - werkzeug
        log = logging.getLogger('werkzeug')
        log.disabled = True
        flask.logger.disabled = True

        flask.run(host="0.0.0.0", port=80)
    except KeyboardInterrupt:
        pass
    finally:
        if(downloader):
            downloader.stop()

    print("main thread exit")
