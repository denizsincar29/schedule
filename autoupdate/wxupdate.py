import wx
import httpx
import os
import sys
from time import time
from packaging import version
from subprocess import Popen
from threading import Thread
from queue import Queue
from .version import VERSION
ver=version.parse  # from autoupdate.update import ver  # for convenience


def get_latest_release():
    """
    Retrieves the latest version

    Returns:
        dict: A dictionary containing the JSON response of the latest release.

    Raises:
        httpx.HTTPError: If the HTTP request to the GitHub API fails or returns an error.

    """
    url = f"https://deniz.r1oaz.ru/schedule/version.json"
    with httpx.Client() as client:
        response = client.get(url)
    response.raise_for_status()
    j=response.json()
    return j

def restart(wxparent=None):
    """
    Restarts the current program.
    Note: This function does not return. Any cleanup action (like saving data) must be done before calling this function.

    Args:
    wxparent (wx.Window): The parent window to close. If None, the main window will not be closed.
    """
    if wxparent is not None:
        wxparent.Close()  # close the main window
    # popen inno setup setup.exe --silent
    Popen(["setup.exe", "/SILENT", "/FORCECLOSEAPPLICATIONS"])
    sys.exit()



class YouWannaUpdateDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Обновление", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.message="Доступно обновление. Хотите обновить?"
        self.init_ui()

    def init_ui(self):
        # create buttons with id ok and cancel
        updatebtn=wx.Button(self, label="Обновить", id=wx.ID_OK)
        cancelbtn=wx.Button(self, label="Отмена", id=wx.ID_CANCEL)
        sizer=wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=self.message), 0, wx.ALL, 5)
        sizer.Add(updatebtn, 0, wx.ALL, 5)
        self.SetSizer(sizer)


class ProgressDlg(wx.ProgressDialog):
    def __init__(self, parent, total):
        super().__init__("Обновление", "Идёт обновление программы. Пожалуйста подождите.", total, parent, wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME | wx.PD_REMAINING_TIME | wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE)

    @property
    def closed(self):
        if self.WasCancelled():
            self.Destroy()
        return self.WasCancelled()



# make our own 2 functions instead of download release. One will return response (to get total size) and other will download the file
def get_response():  # get headers.
    url = f"https://deniz.r1oaz.ru/schedule/setup.exe"
    with httpx.Client() as client:
        headers = client.head(url)
        # return total size in bytes
        return int(headers.headers['Content-Length'])

def download():  # progress will be yielded!
    with open("setup.exe", 'wb') as f, httpx.stream("GET", "https://deniz.r1oaz.ru/schedule/setup.exe") as response:
        downloaded=0 # downloaded bytes
        for chunk in response.iter_bytes():
            f.write(chunk)
            downloaded+=len(chunk)
            yield downloaded
    




def check_update():  # this will be called in a thread
    release = get_latest_release()  # hope it goes quickly
    latest_version = ver(release['version'])
    if VERSION < latest_version or release['force_update']:
        return True, latest_version
    return False, latest_version

# a full class for updating in thread
# first it will check updates and send (True, latest_version) or (False, VERSION) to self.on_update callback. If no updates, thread will simply end. If there is update, it will wait for a boolean to its queue. If the boolean is True, it will download and update. If False, it will end.
#  the download starts by sending total size to total callback and then progress callback is called with the progress. When download is finished, it will call the restart callback.
# all callbacks are wx.CallAfter-ed
class Updater(Thread):
    def __init__(self, on_update, on_total, on_progress, on_restart, on_no_update):
        Thread.__init__(self)
        self.on_update=on_update
        self.on_total=on_total
        self.on_progress=on_progress
        self.on_restart=on_restart
        self.on_no_update=on_no_update
        self.queue=Queue()
        self.daemon=True
        self.start()

    @property
    def dead(self):
        return not self.is_alive()

    def run(self):
        status, version=check_update()
        wx.CallAfter(self.on_update, status, version)
        if status:  # has update
            if self.queue.get():  # we wanna update! go ahead!
                total=get_response()
                wx.CallAfter(self.on_total, total)
                for p in download():
                    if not self.queue.empty():
                        return # stop download
                    wx.CallAfter(self.on_progress, p)
                wx.CallAfter(self.on_restart)
        wx.CallAfter(self.on_no_update)  # we decided not to update! But i dont recommend not updating my program! :D
        self.queue.task_done()

    def stop(self):  # from the main thread
        self.queue.put(False)