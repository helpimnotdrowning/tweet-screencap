# if you have problems, make an issue here --> https://github.com/helpimnotdrowning/tweet-screencap/issues/new <-- and ill try to help

# REQUIRES FFMPEG + FFPROBE IN PATH ( install instructions here --> https://video.stackexchange.com/a/20496 )
# IF YOU DONT HAVE FFMPEG INSTALLED IT WILL CRASH

# TODO: Add check to see if ffmpeg/ffprobe is installed

import logging
import os
import sys
from dataclasses import dataclass
from time import gmtime, strftime
from time import sleep
from typing import Callable, TYPE_CHECKING

import schedule
import tweepy

import get_frame
from get_frame import _read_image as read_image, _save_image as save_image

testing_mode = False


def get_logger(name: str) -> logging.Logger:
    """Make logger."""
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    ch.setFormatter(logging.Formatter(
        '[%(asctime)s.%(msecs)03d] [%(name)s/%(levelname)s]: %(message)s', '%H:%M:%S'
    ))
    
    logger.addHandler(ch)
    
    return logger


def self_do_nothing_if(check_func: Callable, message: str = None) -> Callable:
    """
    Decorator to skip a function inside a class when `check_func` is `True`
    
    `check_func` is a function that returns a `bool`, preferably like `lambda self: self.skip_functions`
    """
    
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if check_func(self):
                get_logger("SelfDoNothingIf").info(f"Skipping {func.__qualname__}(){f': {message}' if message != None else ''}")
                del logging.Logger.manager.loggerDict['SelfDoNothingIf']
            else:
                return func(self, *args, **kwargs)
        
        return wrapper
    
    return decorator


def write_file(file: str, content: str) -> None:
    """Writes to a file"""
    with open(file, 'w+') as file_:
        file_.write(str(content))


def read_file(file: str) -> str:
    """Return file"""
    with open(file, 'r') as file_:
        return file_.read()


def time_to_seconds(hours=0, minutes=0, seconds=0, ms=0) -> float:
    """Convert time to seconds.milliseconds."""
    hour_in_minutes = hours * 60
    minutes += hour_in_minutes
    seconds += (minutes * 60) + (ms * .001)
    return float(seconds)


def seconds_to_time(seconds: float) -> str:
    """Convert seconds to time in HH:MM:SS.ms format."""
    return strftime("%H:%M:%S", gmtime(seconds)) + str(round(seconds % 1, 3))[1:]


def s_if(condition) -> str:
    """Little function to pluralize some words so I don't have to write some if statement everytime."""
    return 's' if condition else ''


class OutOfFramesError(Exception):
    pass


@dataclass
class Episode:
    """Dataclass to hold path to episode and its name. The order is reversed for some reason, but I don't mind it."""
    path: str
    name: str


@dataclass
class Season:
    """Dataclass to hold seaosn name and the Episodes it contains."""
    name: str
    episodes: list[Episode]


@dataclass
class Series:
    """Dataclass to hold series name and the seasons it contains."""
    name: str
    seasons: list[Season]


class TwitterAPI:
    """Wrapper for Tweepy's Twitter API to make my life easier."""
    
    # TODO: Make testing_mode passed as arg to __init__ instead of each individual method
    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret):
        self.api = self.authenticate(consumer_key, consumer_secret, access_token, access_token_secret)
        
        self.log = get_logger("TwitterAPI")
    
    def authenticate(self, consumer_key: str, consumer_secret: str, access_token: str, access_token_secret: str) -> tweepy.api:
        """Authenticate to Twitter API."""
        
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        
        return tweepy.API(auth)
    
    @self_do_nothing_if(lambda self: testing_mode, "Text tweet not sent.")
    def tweet_text(self, text: str) -> None:
        """Send tweet with text."""
        
        self.api.update_status(status=text)
        self.log.debug('Text tweet sent.')
    
    @self_do_nothing_if(lambda self: testing_mode, "Image tweet not sent.")
    def tweet_image(self, image_path: str) -> None:
        """Send a tweet with a single image."""
        # TODO: Multiple images? may help if people use this for other types of image bots.
        
        media_id = self.api.media_upload(filename=image_path).media_id_string
        self.api.update_status(media_ids=[media_id])
        
        self.log.debug('Image tweet sent.')
    
    @self_do_nothing_if(lambda self: testing_mode, "Bio not updated.")
    def update_bio(self, bio_text: str) -> None:
        self.api.update_profile(description=bio_text)
        self.log.debug('Bio updated.')


class ScreencapBot:
    def __init__(self, argv: list[str], keyfile: str):
        self.login(keyfile)
        
        self.log = get_logger("ScreencapBot")
        
        self.sec, self.episode, self.season = self.load_state()
        self.next_frame_custom_image = False
        self.custom_frame = ''
        
        # Add seasons, episodes in order.
        self.series = Series('Series Name!', [
            Season('Series Name! Season 1 (Series!)', [
                Episode('C:/path/to/season1/video1.mp4', "Episode 1"),
                Episode("C:/path/to/season1/video2.mp4", "Episode 2"),
                Episode("C:/path/to/season1/video3.mkv", "Episode 3"),
            ]),
            Season('Series Name! Season 2 (Series!!)', [
                Episode("C:/path/to/season2/video1.mp4", "Episode 1"),
                Episode("C:/path/to/season2/video2.mp4", "Episode 2"),
                Episode("C:/path/to/season2/video3.mkv", "Episode 3"),
            ]),
            Season('Series Name!: The Movie', [
                Episode("C:/path/to/movie/movie.mkv", "Movie")
            ])
        ])
        
        self.parse_args(argv)
        
        schedule.every().hour.at(":00").do(self.main)
        schedule.every().hour.at(":30").do(self.main)
        
        while True:
            schedule.run_pending()
            sleep(1)
    
    def login(self, keyfile: str) -> tweepy.api:
        """Load keyfile containing your Twitter API keys, login to Twitter"""
        try:
            _key_file = read_file(keyfile)
        except FileNotFoundError:
            write_file('./ScreencapBot.kyf',"""CONSUMER_KEY
CONSUMER_SECRET
ACCESS_TOKEN
ACCESS_TOKEN_SECRET""")
            raise FileNotFoundError("Your keyfile was not found. Please fill out the shiny and newly made keyfile at ./ScreencapBot.kyf.") from None
        
        _key_file_split = _key_file.splitlines()
        
        if len(_key_file_split) != 4:
            raise ValueError(f"""Keyfile {keyfile} is improperly formatted: expected format is:
CONSUMER_KEY
CONSUMER_SECRET
ACCESS_TOKEN
ACCESS_TOKEN_SECRET""")
        
        CONSUMER_KEY = _key_file_split[0]
        CONSUMER_SECRET = _key_file_split[1]
        ACCESS_TOKEN = _key_file_split[2]
        ACCESS_TOKEN_SECRET = _key_file_split[3]
        
        self.api = TwitterAPI(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    
    def parse_args(self, argv) -> None:
        """Parse command line args"""
        global testing_mode
        self.log.debug(f"CMD args: {argv}")
        
        if '-h' in argv or '-?' in argv:
            print("""
Unrecognized commands are IGNORED.

Usage:
  -h
  -?
     ...what do you think this does?
  
  -test
     Disables sending tweets and saving state.
     
  -tweet
  -tweet number
     Tweet number times, or once if no number is given. Asks for confirmation if -test isn't also passed.
     
  -inc_sec_dont_tweet
     Increment to the next frame without actually sending anything. Useful when the bot crashes because it ran out of frames and you don't want to double post.
     TODO: fix that"""
                  )
            exit()
        
        if '-test' in argv:
            testing_mode = True
        else:
            testing_mode = False
        
        if '-tweet' in argv:
            try:
                times_to_tweet = int(argv[argv.index('-tweet') + 1])
                if times_to_tweet < 1:
                    exit('nothing below 1 for -tweet next time')
            
            except (ValueError, IndexError):
                times_to_tweet = 1
            
            if testing_mode:
                for i in range(times_to_tweet):
                    self.main()
            
            elif input(f"Send {times_to_tweet} tweet{s_if(times_to_tweet > 1)}? (y/n): ").lower()[0] == 'y':
                self.log.info(f"Tweeting {times_to_tweet} time{s_if(times_to_tweet > 1)}...")
                for i in range(times_to_tweet):
                    self.main()
            
            else:
                self.log.info("Not tweeting.")
        
        if '-inc_sec_dont_tweet' in argv:
            self.log.info('Incrementing time and NOT sending tweet...')
            self.main(dont_tweet_but_still_increment=True)
            self.log.info('Time was incremented, exiting.')
            exit()
    
    def load_state(self):
        """Load screencap state, and create it if it doesn't exist."""
        if not os.path.exists("./state.txt"):
            write_file("./state.txt", "0\n0\n1")
            self.log.info("Created state file, starting from the top!")
        
        state = read_file("state.txt")
        state_split = state.splitlines()
        
        season = int(state_split[0])
        episode = int(state_split[1])
        _sec = state_split[2]
        
        # check if sec is in the tuple format (copied from the time_to_seconds method call spam below) to make specific frame testing easier
        if _sec.startswith('('):
            try:
                _sec_split = _sec.split(",")
            except:
                raise ValueError(f"Couldn't load time: couldn't split up custom timestamp, no commas.\nRaw timestamp: {_sec}")
            
            if len(_sec_split) != 4:
                raise ValueError(f"Couldn't load time: incorrect number of values in custom timestamp, expected 4, got {len(_sec_split)} values.\nRaw timestamp: {_sec}")
            try:
                _sec_split[0] = int(_sec_split[0][1:].strip())
                _sec_split[1] = int(_sec_split[1].strip())
                _sec_split[2] = int(_sec_split[2].strip())
                _sec_split[3] = int(_sec_split[3][:-1].strip())
            except:
                raise ValueError(f"Failed to parse custom timestamp: expected format is '(hour, minutes, seconds, milliseconds)'.\nRaw timestamp: {_sec}")
            
            sec = time_to_seconds(*_sec_split)
        
        # if its not, its just a normal float :)
        else:
            sec = float(_sec)
        
        self.log.info(f"State loaded: Season {str(season + 1)}, episode {str(episode + 1)} at {seconds_to_time(sec)}")
        
        return sec, episode, season
    
    @self_do_nothing_if(lambda self: testing_mode, "State was not saved to disk.")
    def save_state(self):
        """Save screencap state."""
        write_file("./state.txt", f"{str(self.season)}\n{str(self.episode)}\n{str(self.sec)}")
        
        self.log.info("State saved to disk.")
    
    def get_episode(self) -> str:
        """Get current episode.
        Goes to next season if the current one is over, and exits when the final season is over."""
        
        # try to set season, if more seasons than exist (series over), exit
        try:
            season = self.series.seasons[self.season]
        except IndexError:
            raise OutOfFramesError("No more frames, series is over. Congratulations!, unless it isn't and something broke...")
        
        # try to set video, if more videos than exist (season over), go to next season and reset video to 0
        try:
            episode = season.episodes[self.episode]
        except IndexError:
            self.season += 1
            self.episode = 0
            episode = self.get_episode()
        
        return episode
    
    def switch_to_next_episode(self) -> None:
        """Switch to next episode, for use at the end of the if chains in main"""
        self.episode += 1
        self.sec = 0
        
        self.log.info("Switching to next episode.")
        
    def fixed_check_season_and_episode(self, season: int, episode: int) -> bool:
        """One-indexed check the current season+episode, for making keeping track of the frames easier."""
        return self.season == (season - 1) and self.episode == (episode - 1)
        
    def set_custom_next_frame(self, file: str):
        """Make file the next frame instead of something from an episode"""
        self.next_frame_custom_image = True
        self.custom_frame = file
        
    def main(self, dont_tweet_still_increment=False):
        if dont_tweet_still_increment:
            self_api_tweet_image = lambda x: x
        else:
            self_api_tweet_image = self.api.tweet_image
        
        episode = self.get_episode().path
        
        if get_frame.get_length(episode) >= self.sec:
            # check if a custom frame is queued, if it is, use that instead of getting a frame.
            if self.next_frame_custom_image:
                frame = read_image(self.custom_frame)
                success = True
            
            else:
                success, frame = get_frame.get_frame(episode, self.sec)
            
            if success:
                save_image(frame, "temp.png")
                
                if self.next_frame_custom_image:
                    self.log.info(f"{'NOT' if dont_tweet_still_increment else ''} Sending custom frame at {self.custom_frame} ({seconds_to_time(self.sec)} ({self.sec}))")
                else:
                    self.log.info(f"{'NOT' if dont_tweet_still_increment else ''} Sending frame at {seconds_to_time(self.sec)} ({self.sec})")
                self.next_frame_custom_image = False
                
                self_api_tweet_image('temp.png')
                
                if self.fixed_check_season_and_episode(1, 1):
                    if self.sec == time_to_seconds(0):
                        raise OutOfFramesError("Ran out of frames while in episode!")
                else:
                    raise OutOfFramesError(f"New episode {self.episode} of seaoson {self.season + 1} has no frames!")
                
                self.save_state()
                self.api.update_bio(f"""Tweeting hand-picked screenshots from {self.series.name} every 30 minutes, in order, again.
Source code below.
Now Playing: {self.series.seasons[self.season].name} {self.series.seasons[self.season].episodes[self.episode].name}""")
                self.log.info(f"Next frame will be at {seconds_to_time(self.sec)} ({self.sec})")
        
        else:
            self.switch_to_next_episode()
        
        sleep(1)


if __name__ == '__main__':
    bot = ScreencapBot(sys.argv, "ScreencapBot.kyf")
