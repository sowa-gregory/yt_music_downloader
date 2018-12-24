# Youtube music downloader

## Description

Youtube music downloader is a web server service, which allows for queuing and downloading music/audio remotely from youtube. Music is extracted from published videos after providing url to particular material. User interacts with service using web browser. Multiple users could control downloading process simultanously.
Server side download processing if fully independent from browser and continues even if nobody is connected. Downloaded files are stored in chosen location at the server.

## Application

Potential usage of the solution is to enrich functionality of existing set top boxes/multimedia servers. Typically users transfers existing downloaded or obtained music files to those servers manually. If somebody wants to extract audio from youtube videos, then additional dedicated software must be involved. The solution allows to fully automate the process. Now downloading is controlled remotely and final extracted music files are directly stored in proper location without unnecessary copying and additional conversion burden.

## Limitations

Best quality audio stream is automatically selected to be extracted from video by downloading server functionality. Those streams are very frequently stored in webm file format, which might not be supported by all existing multimedia servers and players.
Author decided to keep audio in its original format to avoid reencoding and possible degradation of quality.

To fully benefit from the solution, please select modern multimedia servers, which supports contemporary audio containers. VLC and MPD are examples of compatible solutions.

## Technology

Server side of the solution is build using Python 3. Web service functionality utilizes Flask framework. Youtube integration uses ytdownload-dl library.

Front side of the solution is build in form of single page application. Web page connects to server to obtain current dowload status and to request new files. Communication is based on REST type of web API exposed by the server - client uses axios library.

### REST endpoint

## Installation

## ToDo

### Fixed (release v1.0)

- web console cannot reconnect to server on network error
- order of downloads - sometimes file added later apears before another downloads (it's required to switch to OrderedDict collection)
- remove whitespaces from download url
  
### Pending

- validate download url structure at server side
- splitting classes into separate files
- code refactoring
- add scanning of pending downloads at startup in order to resume them
- failed downloads must remove .to_download files
- download directory to be provided from command line
- port provided from command line options
- invalid title of song displayed in web console, when download directory starts with "/" - absolute path

## Version history

2018-12-24 - initial functional release v1.0
