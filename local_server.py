import sys, os
import signal
import time
import http.server
import urllib.request, urllib.parse, urllib.error
import mimetypes
from threading import Thread
import subprocess
import http.client
import urllib.parse
import select



FFMPEG = 'ffmpeg -i "%s" -preset ultrafast -f mp4 -frag_duration 3000 -b:v 2000k -loglevel error %s -'
AVCONV = 'avconv -i "%s" -preset ultrafast -f mp4 -frag_duration 3000 -b:v 2000k -loglevel error %s -'


class ImageRequestHandler(http.server.BaseHTTPRequestHandler):
    content_type = "image/png"
    content = b""
    
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", self.content_type)
        self.wfile.write(self.content)
        return


class SubtitleRequestHandler(http.server.BaseHTTPRequestHandler):
    content_type = "text/vtt"
    
    def do_GET(self):
        filepath = urllib.parse.unquote_plus(self.path)
        
        self.send_headers(filepath)       
        self.write_response(filepath)


    def send_headers(self, filepath):
        self.protocol_version = "HTTP/1.1"
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-type", self.content_type)
        self.send_header("Accept-Encoding", "*")
        self.send_header("Content-length", str(os.path.getsize(filepath)))
        self.end_headers()


    def write_response(self, filepath):
        with open(filepath, "br") as f: 
            self.wfile.write(f.read())


class RequestHandler(http.server.BaseHTTPRequestHandler):
    content_type = "video/mp4"
    
    """ Handle HTTP requests for files which do not need transcoding """
    def do_GET(self):
        filepath = urllib.parse.unquote_plus(self.path)
        
        self.send_headers(filepath)       
        self.write_response(filepath)


    def send_headers(self, filepath):
        content_length = str(os.path.getsize(filepath))
        self.protocol_version = "HTTP/1.1"
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-type", self.content_type)
        self.send_header("Accept-Encoding", "*")
        self.send_header("Content-length", content_length)
        self.send_header("Range", "bytes=0-%s"%(content_length))
        self.end_headers()


    def write_response(self, filepath):
        with open(filepath, "br") as f: 
            self.wfile.write(f.read())


class TranscodingRequestHandler(RequestHandler):
    """ Handle HTTP requests for files which require realtime transcoding with ffmpeg """
    transcoder_command = FFMPEG
    transcode_options = ""
    content_type = "video/mp4"
                    
    def write_response(self, filepath):

        ffmpeg_command = self.transcoder_command % (filepath, self.transcode_options) 
        
        ffmpeg_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, shell=True)       

        for line in ffmpeg_process.stdout:
            chunk_size = "%0.2X" % len(line)
            self.wfile.write(chunk_size.encode())
            self.wfile.write("\r\n".encode())
            self.wfile.write(line) 
            self.wfile.write("\r\n".encode())
            
        self.wfile.write("0".encode())
        self.wfile.write("\r\n\r\n".encode())
        
        
    def send_headers(self, filepath):
        self.protocol_version = "HTTP/1.1"
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-type", self.content_type)
        self.send_header("Accept-Encoding", "*")
        self.end_headers()
