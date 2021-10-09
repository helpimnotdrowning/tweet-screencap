# WARNING: This helper was made for a 1680x1050 monitor. If you need to use it on a monitor with a different resolution, make an issue at https://github.com/helpimnotdrowning/tweet_screencap/issues

import re
from base64 import b64decode
from io import BytesIO
from time import sleep

import pyautogui as phk
import win32api
from PIL.Image import open
from numpy import asarray
from pyperclip import copy as to_clipboard

"""
A quick guide to installing pytesseract on Windows, because it's difficult for some reason:
    1) Download the latest 64 bit installer from here : https://github.com/UB-Mannheim/tesseract/wiki#tesseract-installer-for-windows
    2) Install it for all users (install for current user *might* work, but not sure)
    3) Install pytesseract using pip ( `pip install pytesseract` )
"""
from pytesseract import image_to_string
from pynput.keyboard import Key, Listener, Controller

# store images as base64 for ease of transport
find1 = b'iVBORw0KGgoAAAANSUhEUgAAABQAAAAJBAMAAADA7xF7AAAAKlBMVEUEBAT//wDAwMBCQkIcHBwWFhbMzMzX19eysrL///8zMzPx8fGAgACGhobhABxjAAAARElEQVR4nGNgEGAyZmBgUHEMBZJs5QwM5S0ODCDmTK1FuyFMjnKtRWBRGQGOu1qL7rY4HgSJgpkQBUjMDgaGDjATbi4ADyYV53Bwg2wAAAAASUVORK5CYII='
find2 = b'iVBORw0KGgoAAAANSUhEUgAAABQAAAAJBAMAAADA7xF7AAAAHlBMVEUAAAAEBAS/v7++vr59fQD+/v77+wDAwMCFhYX4+ADa1Qx6AAAAMklEQVR4nGNgAAFBIUMRAQYIU9UwAcosDzUUhDEjEMwOw5QJcCaSKIwpqGGYCGOCzAUAw1gJqN+0gBIAAAAASUVORK5CYII='


# base64 bytes to PIL Image
def b64_2_PIL_Image(b64):
    im_bytes = b64decode(b64)
    im_file = BytesIO(im_bytes)
    return open(im_file)
    
    
# fixes int strings like '003' -> '3' so python doesnt SyntaxError me
def fix_int(string):
    return str(int(string))
    
    
def message_box(title, message):
    win32api.MessageBox(0, message, title, 0x00001000)
    
    
# finds MPC-HC timestamp in screen
def find_time():
    # Instead of searching the whole screen, search only in the bottom left of the left middle of the screen
    # ┌────────│──────┐
    # │        │       │
    # │        │       │
    # └────────│──────┘
    #         ^ here
    screenshot = phk.screenshot(region=(656, 984, 154, 22))
    
    return image_to_string(asarray(screenshot), config="-c tessedit_char_whitelist=0123456789:.\/")


def fix_time(time):
    """Fix up timestamp to be pasted into your local tweet_screencap.py"""
    # using DOTALL because sometimes tesseract will also send some extra characters on a newline
    stripped_time = re.sub('/.*', '', time, flags=re.DOTALL)
    
    # if the regex fails, it return the string unchanged, so this comparison is perfectly valid
    if stripped_time == time:
        print(f'\n\n{time}\n\n')
        message_box("", "There was a problem parsing the time from MPC. Try another timestamp.")
        return
    
    # if the video is longer than an hour, MPC-HC will add a XX: to the start of the video elapsed time
    # it does not remove a XX: if the video is shorter than a minute, however.
    if re.fullmatch('(\d\d:){1}\d\d\.\d\d\d', stripped_time):
        fixed_time = ', '.join(['0', fix_int(stripped_time[0:2]), fix_int(stripped_time[3:5]), fix_int(stripped_time[6:9])])
    
    elif re.fullmatch('(\d\d:){2}\d\d\.\d\d\d',stripped_time):
        fixed_time = ', '.join([fix_int(stripped_time[0:2]), fix_int(stripped_time[3:5]), fix_int(stripped_time[6:8]), fix_int(stripped_time[9:12])])
    
    else:
        print(f'\n\n{stripped_time}\n\n')
        message_box("", "There was a problem parsing the time from MPC. Try another timestamp.")
        return
    
    if fixed_time == "0, 0, 0, 0":
        return f'''if self.sec == time_to_seconds({fixed_time}):  '''
    else:
        return f'''self.sec = time_to_seconds({fixed_time})
                    elif self.sec == time_to_seconds({fixed_time}):  '''


def on_press(key): pass


# i am very unreasonably proud of this
# this finds and copies the time to the clipboard,
# alt-tabs to last app (should be n++ or whatever you may be editing tweet_screencap.py with)
# pastes,
# and then alt-tabs back
def on_release(key):
    if key == Key.shift:
        found_time = find_time()
        print(found_time)
        time = fix_time(found_time)
        
        if time == None:
            print("Problem with timestamp.")
            return
        else:
            to_clipboard(time)
        
        with Controller().pressed(Key.alt):
            Controller().tap(Key.tab)
            
        sleep(.5)  # pause for a bit because as to not send the paste to the task switcher and not notepad++
        Controller().press(Key.ctrl.value)
        Controller().tap('v')
        Controller().release(Key.ctrl.value)
       
        with Controller().pressed(Key.alt):
            Controller().tap(Key.tab)
    elif key == Key.esc:
        exit()


if __name__ == '__main__':
    
    print("ello & ready, press SHIFT to go")
    
    # Collect events until released
    with Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
        