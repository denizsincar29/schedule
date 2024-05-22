import threading
import wx
import httpx
import time

from queue import Queue
def upload_ical(ical: str) -> str:
    response = httpx.post('https://deniz.r1oaz.ru/ical/upload.php', files={'file': ('test.ics', ical, 'text/calendar')})
    data = response.json()
    if response.status_code == 200 and data['status'] == 'success':
        return (True, f"https://deniz.r1oaz.ru/ical/get.php?filename={data['filename']}", data['filename'])
    return (False, data['message']), None  # for 3 return values

def get_ical(filename: str) -> str:
    response = httpx.get('https://deniz.r1oaz.ru/ical/get.php', params={'filename': filename})
    if response.status_code == 200:
        return (True, response.text)
    data = response.json()
    return (False, data['message'])

class GotICalCheck(threading.Thread):
    def __init__(self, filename, on_deleted_callback):
        threading.Thread.__init__(self)
        self.q=Queue()
        self.filename = filename
        self.on_deleted_callback = on_deleted_callback
        self.daemon = True
        self.start()

    def run(self):
        with httpx.Client() as client:
            t=time.time()
            while time.time()-t<115:  # a bit less than 2 minutes
                if not self.q.empty():
                    return  # dialog is already closed
                try:
                    response = client.get('https://deniz.r1oaz.ru/ical/exists.php', params={'filename': self.filename}, timeout=5)
                except httpx.ReadTimeout:
                    continue  # try again
                if response.status_code == 200:
                    data = response.json()
                    if not data['status']:  # timed out
                        wx.CallAfter(self.on_deleted_callback)  # we need to call it even if the file is not found because the callback closes the dialog
                        return
                    print("I'm calling back!")
                    wx.CallAfter(self.on_deleted_callback)
                    return
        wx.CallAfter(self.on_deleted_callback)