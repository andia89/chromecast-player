# Chromecast-player

Chromecast-player written using Python3.x and PyGTK. The player allows you to play local files from your computer and network streams which are parsed using `youtube-dl`. The player supports playlists, changing volume, connecting to different chromecasts, and on the fly conversion of local files (using ffmpeg or avconv) with media types not supported by chromecast.

### NOTE: This is still a very early beta, so there will be bugs!!! Feel free to report them here :)

##Dependencies
The script needs Python3.x to run, and relies on `pychromecast` that does the communicating with the chromecast. Apart from that I tried to use standard python libraries. If you want to play network streams, you need a version of `youtube-dl` somewhere in your `$PATH`

##Usage
Just download the repo, `cd` into the folder and run:

```
./player.py
```


You can pass uris (either local files or network streams) directly on the command line

```
./player.py /path/to/file1 www/a/stream
```

You can select local files and hit `Play now` in the file-chooser dialog, to selected files immediately, or hit `Add to playlist` to append them to currently playing files/network streams. The same is true for network streams. 

##Acknowledgments
The script relies heavily on [pychromecast](https://github.com/balloob/pychromecast) written by Paulus Schoutsen.

A lot of code is also taken from [stream2chromecast](https://github.com/Pat-Carter/stream2chromecast) written by Pat-Carter who figured out how to stream local files to the chromecast. 
