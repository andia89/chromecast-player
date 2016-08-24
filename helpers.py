import subprocess
import mimetypes
import re
import json
import os
from urllib.parse import urlparse, unquote, quote_plus

supported_picture_formats = {'mjpeg': 'jpg', 'png':'png', 'jpeg':'jpg','jpg':'jpg', 'gif':'gif', 'webp':'webp'}
supported_formats = {'mp4':('video/mp4', 0), 'webm':('video/webm', 1), 'ogg':('audio/ogg', 2), 'flac_2':("audio/flac", 1.5),'aac':("audio/aac", 1.8), 'flac':("audio/x-flac", 1.6), 'mp3':('audio/mpeg', 3), 'wav':('audio/wav', 4), 'mp4_2':('audio/mp4', 5)}


def get_mimetype(filename, ffprobe_cmd=None):
    """ find the container format of the file """
    # default value
    mimetype = "video/mp4"

    # guess based on filename extension
    guess = mimetypes.guess_type(filename)[0]
    if guess is not None:
        if guess.lower().startswith("video/") or guess.lower().startswith("audio/"):
            mimetype = guess

    # use the OS file command...
    try:
        file_cmd = 'file --mime-type -b "%s"' % filename
        file_mimetype = subprocess.check_output(file_cmd, shell=True).strip().lower().decode('utf-8')
        if file_mimetype.startswith("video/") or file_mimetype.startswith("audio/"):
            mimetype = file_mimetype
    except:
        pass

    # use ffmpeg/avconv if installed
    if ffprobe_cmd is None:
        return mimetype
    
    # ffmpeg/avconv is installed
    has_video = False
    has_audio = False
    format_name = None
    
    ffprobe_cmd = '%s -show_streams -show_format -print_format json -v quiet "%s"' % (ffprobe_cmd, filename)
    ffmpeg_process = subprocess.Popen(ffprobe_cmd, stdout=subprocess.PIPE, shell=True)
    com = ffmpeg_process.communicate()[0]
    dicti = json.loads(com.decode('utf-8'))
    for stream in dicti['streams']:
        if stream['codec_type'] == 'video':
            if stream['codec_name'] not in supported_picture_formats.keys():
                has_video = True
                format_name = stream['codec_name']
        if stream['codec_type'] == 'audio':
            has_audio = True
            format_name = stream['codec_name']

    # use the default if it isn't possible to identify the format type
    if format_name is None:
        return mimetype

    if has_video:
        mimetype = "video/"
    else:
        mimetype = "audio/"
        
    if "mp4" in format_name:
        mimetype += "mp4"
    elif "h264" in format_name:
        mimetype = "video/mp4"
    elif "aac" in format_name:
        mimetype = "audio/aac"
    elif "webm" in format_name:
        mimetype += "webm"
    elif "ogg" in format_name:
        mimetype += "ogg"
    elif "mp3" in format_name:
        mimetype = "audio/mpeg"
    elif "wav" in format_name:
        mimetype = "audio/wav"
    elif "flac" in format_name:
        mimetype = "audio/flac"
    else:   
        mimetype += "mp4"

    return mimetype


def get_transcoder_cmds(preferred_transcoder=None):
    """ establish which transcoder utility to use depending on what is installed """
    probe_cmd = None
    transcoder_cmd = None
    
    ffmpeg_installed = is_transcoder_installed("ffmpeg")
    avconv_installed = is_transcoder_installed("avconv")  
    
    # if anything other than avconv is preferred, try to use ffmpeg otherwise use avconv    
    if preferred_transcoder != "avconv":
        if ffmpeg_installed:
            transcoder_cmd = "ffmpeg"
            probe_cmd = "ffprobe"
        elif avconv_installed:
            transcoder_cmd = "avconv"
            probe_cmd = "avprobe"
    
    # otherwise, avconv is preferred, so try to use avconv, followed by ffmpeg  
    else:
        if avconv_installed:
            transcoder_cmd = "avconv"
            probe_cmd = "avprobe"
        elif ffmpeg_installed:
            transcoder_cmd = "ffmpeg"
            probe_cmd = "ffprobe"
            
    return transcoder_cmd, probe_cmd


def is_transcoder_installed(transcoder_application):
    """ check for an installation of either ffmpeg or avconv """
    try:
        subprocess.check_output([transcoder_application, "-version"])
        return True
    except OSError:
        return False

def decode_network_uri(url):
    try:
        proc = subprocess.Popen(['youtube-dl', '-j', url], stdout=subprocess.PIPE)
        ret = proc.communicate()[0]
        dicti = json.loads(ret.decode('utf-8'))
        if 'formats' in list(dicti.keys()):
            exts = []
            for fs in dicti['formats']:
                ind = 100
                if not fs['ext'] in exts:
                    exts.append(fs['ext'])
            exte = 'mp4'
            mime = 'video/mp4'
            for ext in exts:
                if ext in supported_formats.keys() and ind > supported_formats[ext][1]:
                    ind = supported_formats[ext][1]
                    mime = supported_formats[ext][0]
                    exte = ext
            proc = subprocess.Popen(['youtube-dl', '-f', exte, '-g', url], stdout=subprocess.PIPE)
            ret = proc.communicate()[0].decode('utf-8')
            url = ret
        else:
            url = dicti['url']
            mime = supported_formats[dicti['ext']][0]
        if url:
            return (url, False, mime, False, None, None, None)
        else:
            return None
    except Exception as e:
        return None


def decode_local_uri(uri, transcoder, probe, preferred_transcoder):
    url = unquote(urlparse(uri).path)
    mime = get_mimetype(url, probe)
    transcode = False
    if transcoder:
        transcode = True
    print(supported_formats.keys())
    for k in supported_formats.keys():
        if mime == supported_formats[k][0]:
            transcode = False
    metadata = None
    thumb = None
    if os.path.exists(url):
        metadata, thumb, image_mime = get_metadata(url, mime, preferred_transcoder)
        return (url, True, mime, transcode and transcoder, metadata, thumb, image_mime)
    else:
        return None


def get_metadata(filename, mime, preferred_transcoder):
    """ get metadata from local files, including thumbnails """
    trans, probe = get_transcoder_cmds(preferred_transcoder=preferred_transcoder)
    if not probe:
        return None, None, None
    if mime.startswith("audio/"):
        metadata = {'metadataType':3}
        proc = subprocess.Popen([probe, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ret = proc.communicate()
        ret = ret[0].decode('utf-8')
        info = json.loads(ret)
        thumb = None
        image_mime = None
        if 'tags' in info['format']:
            for line in info['format']['tags']:
                if re.search('title', line, re.IGNORECASE):
                    metadata['title'] = info['format']['tags'][line]
                elif re.search('album', line, re.IGNORECASE):
                    metadata['albumName'] = info['format']['tags'][line]
                elif re.search('album artist', line, re.IGNORECASE) or re.search('albumartist', line, re.IGNORECASE):
                    metadata['albumArtist'] = info['format']['tags'][line]
                elif re.search('artist', line, re.IGNORECASE):
                    metadata['artist'] = info['format']['tags'][line]
                elif re.search('composer', line, re.IGNORECASE):
                    metadata['composer'] = info['format']['tags'][line]
                elif re.search('track', line, re.IGNORECASE):
                    try:
                        track = info['format']['tags'][line].split("/")[0]
                        metadata['trackNumber'] = int(track.lstrip("0"))
                    except:
                        pass
                elif re.search('disc', line, re.IGNORECASE):
                    try:
                        disc = info['format']['tags'][line].split("/")[0]
                        metadata['discNumber'] = int(disc.lstrip("0"))
                    except:
                        pass
        cover_str = None
        if len(info['streams']) > 1:
            if info['streams'][0]['codec_type'] == 'video':
                cover_str = 0
            elif info['streams'][1]['codec_type'] == 'video':
                cover_str = 1
        if cover_str and info['streams'][cover_str]['tags']['comment']:
            if info['streams'][cover_str]['tags']['comment'] == 'Cover (front)':
                if info['streams'][cover_str]['codec_name'] in supported_picture_formats.keys():
                    ext = info['streams'][cover_str]['codec_name']
                    proc = subprocess.Popen([trans, '-i', filename, '-v', 'quiet', '-vcodec', 'copy', '-f', ext, 'pipe:1'], stdout=subprocess.PIPE)
                    t = proc.communicate()[0]
                    thumb = t
                    image_mime = 'image/'+supported_picture_formats[ext]
        return metadata, thumb, image_mime
    elif mime.startswith("video/"):
        metadata = {'metadataType':1}
        proc = subprocess.Popen([probe, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ret = proc.communicate()
        ret = ret[0].decode('utf-8')
        info = json.loads(ret)
        if 'tags' in info['format']:
            for line in info['format']['tags']:
                if re.search('title', line, re.IGNORECASE):
                    metadata['title'] = info['format']['tags'][line]
        return metadata, None, None


