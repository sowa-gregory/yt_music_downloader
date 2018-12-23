from flask import Flask
import youtube_dl
import threading
import queue
import time
import json
import os

flask = Flask(__name__)


class DownloadThread(threading.Thread):
    def __init__(self, queue, song_id):
        super(DownloadThread, self).__init__()
        self.queue = queue
        self.song_id = song_id
  
    def onDownload(self, progress):
        status = progress['status']
        total_bytes = progress['total_bytes']

        if(status == "finished"):
            downloaded_bytes = total_bytes
            eta = 0
        else:
            downloaded_bytes = progress['downloaded_bytes']
            eta = progress['eta']

        song_info = {"filename": progress['filename'], "downloaded_bytes": downloaded_bytes,
                     "total_bytes": total_bytes, "eta": eta}

        data = {
            "status": progress['status'], "song_id": self.song_id, "data": song_info}
        self.queue.put(data)

    def run(self):
        ydl_opts = {'quiet': 'true', 'format': 'bestaudio/best',
                    'outtmpl': 'download/%(title)s.%(ext)s',
                    'progress_hooks': [self.onDownload]}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download(["https://youtu.be/"+self.song_id])
        print("download thread exit\n")

  

class DownloadManager(threading.Thread):
    def __init__(self):
        super(DownloadManager, self).__init__()
        self.stopRequest = threading.Event()
        self.statusQueue = queue.Queue()
        self.threads = []
        self.downloadStatus = {}
        self.locker = threading.Lock()
        self.downloadList = []
        self.maxThreads = 2

        # start manager
        self.start()

    def addSongToDownloadQueue(self, songId):
        with open("download/"+songId+".to_download", "w"):
            pass
        with self.locker:
            self.downloadList.append(songId)
            
    def popDownloadQueue(self):
        with self.locker:
            if self.downloadList:
                return self.downloadList.pop()

    def scanToDownload(self):
        pass

    def startDownload(self):
        ''' starts download of next song when list of songs is not empty and there are awaiting worker threads '''
        songId = self.popDownloadQueue()
        if( songId != None and len(self.threads) < self.maxThreads):
                thr = DownloadThread(self.statusQueue, songId)
                thr.start()
                self.threads.append(thr)
                return True
        return False

    def updateThreadsStatus(self):
        ''' Updates running status of managed download threads. '''
        self.threads = [thr for thr in self.threads if thr.isAlive()]
 
    def run(self):
        self.scanToDownload()

        while(not self.stopRequest.is_set()):
            
            self.updateThreadsStatus()
            print(self.threads)
            while(self.startDownload() == True):
                print("new download")
                pass

            try:
                data = self.statusQueue.get(timeout=1)
                if( data['status']=="finished"):
                    os.remove( "download/"+data['song_id']+".to_download")
                self.setDownloadStatus(data['song_id'], data['data'])

            except queue.Empty:
                pass
        print("manager thread exit")

    def setDownloadStatus(self, songId, status):
        with self.locker:
            self.downloadStatus[songId] = status

    def getDownloadStatus(self):
        with self.locker:
            status = self.downloadStatus.copy()
        return status

    def trystop(self):
        for thr in self.threads:
            if(not thr.isAlive()):
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

downloader = DownloadManager()

@flask.route('/status')
def hello():
    return json.dumps(downloader.getDownloadStatus())

if __name__ == '__main__':

    try:
        time.sleep(2)
        downloader.addSongToDownloadQueue("cJpVlFMHz1E")
        downloader.addSongToDownloadQueue("pRpeEdMmmQ0")

        flask.run(port=80)
    except KeyboardInterrupt:
        pass
    finally:
        downloader.stop()

    print("main thread exit")
