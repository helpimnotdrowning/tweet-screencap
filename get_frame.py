# extracts individual frames from a video file to folder
import logging
import subprocess
from datetime import datetime
from os import remove
from pathlib import Path as path
from time import gmtime, strftime
from typing import TYPE_CHECKING, Tuple, Type, Union

from cv2 import imread, imwrite

if TYPE_CHECKING:
    from numpy import ndarray


def get_logger(name: str) -> logging.Logger:
    """Make logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    ch.setFormatter(logging.Formatter(
        '[%(asctime)s.%(msecs)03d] [%(name)s/%(levelname)s]: %(message)s', '%H:%M:%S')
    )
    
    logger.addHandler(ch)
    
    return logger


log = get_logger("Get_Frame")


def _read_image(file: str) -> 'ndarray':
    """Read image in numpy format"""
    return imread(file)


def _save_image(image: 'ndarray', file_name: str) -> None:
    """Save image in numpy format"""
    imwrite(file_name, image)


def _delete_file(file):
    """Delete a file, warn if it couldn't instead of crashing."""
    try:
        remove(file)
    except Exception:
        log.warning(f"File {file} could not be deleted.")


def get_length(filename: str) -> float:
    """Get length of video in seconds."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    try:
        return float(result.stdout)
    except ValueError:
        raise OSError(f"Could not get length of file {filename}.") from None


def get_frame(video_filepath: str, time: float) -> Tuple[bool, Union['ndarray', None]]:
    video_filepath = str(path(video_filepath))
    length = get_length(video_filepath)
    
    if time > length or time < 0:
        return False, None
    
    tmp_file_name = datetime.now().strftime("tmp_GET_FRAME_%H%M%S%f.png")
    
    result = subprocess.run(
        ['ffmpeg', '-y', '-loglevel', 'warning', '-ss', str(time), '-i', video_filepath, '-vframes', '1', tmp_file_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    if "Output file is empty, nothing was encoded" in str(result.stdout):
        return False, None
    
    img = _read_image(tmp_file_name)
    _delete_file(tmp_file_name)
    
    if img is None:
        return False, None
        
    return True, img


if __name__ == '__main__':
    video = input('video path : ')
    time = float(input('time : '))
    save_as = input('save as : ')
    
    get_frame(video, time)
    _save_image(get_frame(video, time)[1], save_as)
