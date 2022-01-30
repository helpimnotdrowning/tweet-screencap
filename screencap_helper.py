from re import DOTALL, fullmatch, sub
from time import gmtime, sleep, strftime

from bs4 import BeautifulSoup
from requests import get
from win32api import MessageBox
from pyperclip import copy as to_clipboard
from pynput.keyboard import Controller, Key, Listener


def seconds_to_time(time: int):
    """Convert seconds to time in HH:MM:SS.ms format"""
    hours = gmtime(time).tm_hour
    minutes = gmtime(time).tm_min
    seconds = gmtime(time).tm_sec
    milliseconds = str(time)[-3:]

    return f"({hours},{minutes},{seconds},{milliseconds})"


def message_box(title, message):
    """Show message box with an OK button on foreground"""
    MessageBox(0, message, title, 0x00001000)


def find_time():
    """Find MPC-HC video position by using the web interface"""
    # check this in MPC > View > Options > Player > Web Interface > Check "Listen on port", replace "13579" with your port number
    mpc_vars = get("http://localhost:13579/variables.html").text
    soup = BeautifulSoup(mpc_vars, 'html.parser')

    print(ms_as_int := soup.find_all(id='position'))

    milliseconds = str(ms_as_int).replace("[<p id=\"position\">", "").replace("</p>]", "")
    return seconds_to_time(int(milliseconds)/1000.0)


def fix_time(time):
    """Fixes up timestamp to be directly pasted into tweet_screencap.py"""
    print(time, " FIXING")

    # paste directly into tweet_screencap.py
    if time == "(0,0,0,0)":
        return f'''if self.sec == time_to_seconds{time}:  '''
    else:
        return f'''self.sec = time_to_seconds{time}
                        elif self.sec == time_to_seconds{time}:  '''


def on_press(key):
    pass


def on_release(key):
    """Copy time to clipboard, alt-tab to last app and paste there, then alt-tab back"""
    if key == Key.shift:
        time = fix_time(find_time())
        
        if time == None:
            print("Problem with timestamp.")
            return
        else:
            to_clipboard(time)
        
        with Controller().pressed(Key.alt):
            Controller().tap(Key.tab)
            
        sleep(.5) # pause for a bit to not send paste to task switcher instead of editor
        Controller().press(Key.ctrl.value)
        Controller().tap('v')
        Controller().release(Key.ctrl.value)

        with Controller().pressed(Key.alt):
            Controller().tap(Key.tab)
    elif key == Key.esc:
        exit()


if __name__ == '__main__':

    print("Ready, press SHIFT to copy...")

    # Collect events until released
    with Listener(
        on_press=on_press,
        on_release=on_release) as listener:
        listener.join()
