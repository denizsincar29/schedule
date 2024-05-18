import wx
import httpx
import os
import sys
from packaging import version
from subprocess import Popen
from threading import Thread
from queue import Queue
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
    Popen("setup.exe --silent", shell=True)
    sys.exit()



class YouWannaUpdateDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Обновление", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.message="Доступно обновление. Хотите обновить?"
        self.ok=False
        self.init_ui()

    def init_ui(self):
        # create buttons:
        updatebtn=wx.Button(self, label="Обновить")
        updatebtn.Bind(wx.EVT_BUTTON, self.on_update)
        cancelbtn=wx.Button(self, label="Отмена")
        cancelbtn.Bind(wx.EVT_BUTTON, self.on_cancel)
        sizer=wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=self.message), 0, wx.ALL, 5)
        sizer.Add(updatebtn, 0, wx.ALL, 5)
        self.SetSizer(sizer)

    def on_update(self, e):
        self.ok=True
        self.Close()

    def on_cancel(self, e):
        self.Close()


class ProgressDlg(wx.Dialog):
    def __init__(self, parent, total):
        super().__init__(parent, title="Обновление", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.init_ui(total)
        self.closed=False

    def init_ui(self, total):
        sizer=wx.BoxSizer(wx.VERTICAL)
        self.gauge=wx.Gauge(self, range=total)
        sizer.Add(self.gauge, 0, wx.ALL, 5)
        self.SetSizer(sizer)
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_close(self, e):
        self.closed=True
        self.Destroy()


# make our own 2 functions instead of download release. One will return response (to get total size) and other will download the file
def get_response():
    with httpx.Client(follow_redirects=True) as client:
        response = client.get("https://deniz.r1oaz.ru/schedule/setup.exe", timeout=None)
    response.raise_for_status()
    return response

def download(response):  # progress will be yielded!
    with open("setup.exe", 'wb') as f:
        downloaded=0 # downloaded bytes
        for chunk in response.iter_bytes():
            f.write(chunk)
            downloaded+=len(chunk)
            yield downloaded
    

def update(current_version, parent):  # i think this must be called even before the main window is created
    def check_update(current_version):
        # can we busy parent?
        with wx.BusyInfo("Проверка обновлений..."):
            release = get_latest_release()  # hope it goes quickly
            latest_version = ver(release['version'])
            if current_version < latest_version or release['force_update']:
                return True, latest_version
        return False, latest_version

    status, version=check_update(current_version)
    if status:
        dlg=YouWannaUpdateDialog(parent)
        dlg.ShowModal()
        if not dlg.ok:
            return  False # we did not update
        # download and update
        response=get_response()
        total=int(response.headers['Content-Length'])
        progress=ProgressDlg(parent, total)
        progress.Show()
        for p in download(response):
            # if progress is cancelled, we must stop the download
            if progress.closed:
                return False
            progress.gauge.SetValue(p)
        progress.Destroy()
        # i think we cannot restart from here. We must close the main window and restart. Lets just return True
        return True


# experimental downloading thread
def download_thread(response, progcb, distroycb):
    for p in download(response):
        wx.CallAfter(progcb, p)  # call the progress callback in main thread
    wx.CallAfter(distroycb)  # i think destroycb doesn't distroy itself but restarts with distroying the main window



def update_thread(current_version, parent):
    def check_update(current_version):
        # can we busy parent?
        with wx.BusyInfo("Проверка обновлений..."):
            release = get_latest_release()  # hope it goes quickly
            latest_version = ver(release['version'])
            if current_version < latest_version or release['force_update']:
                return True, latest_version
        return False, latest_version

    status, version=check_update(current_version)
    if status:
        dlg=YouWannaUpdateDialog(parent)
        dlg.ShowModal()
        if not dlg.ok:
            return  False # we did not update
        # download and update
        response=get_response()
        total=int(response.headers['Content-Length'])
        progress=ProgressDlg(parent, total)
        progress.Show()
        t=Thread(target=download_thread, args=(response, progress.update, lambda: restart(parent)))  # restart is called in main thread
        t.start()
        # i think we cannot restart from here. We must close the main window and restart. Lets just return True
        return True  # from now on, the thread will handle the download and restart automatically.