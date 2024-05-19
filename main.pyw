# gui for NARFU schedule viewer.
# WXPython
import sys
from cytolk import tolk
import wx
from guinput import GUInput, ChooseFromList, AuthInput, PopUpMSG
from datepicker import DatePicker
from app_logic import App
from parsers.people import noone, People
from news import news
from autoupdate.wxupdate import Updater, VERSION, restart, YouWannaUpdateDialog, ProgressDlg

class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title=f"Расписание САФУ ({VERSION})", size=(800, 600), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        self.app=App(self.check_auth_cb)
        self.updater=Updater(self.on_update, self.on_total, self.on_progress, self.on_restart)  # I didn't think of a better way to implement this
        self.progress=None  # to not get attribute error
        self.authed=False
        #region GUI
        self.panel = wx.Panel(self, -1)
        self.hint = wx.StaticText(self.panel, label="Примечание. Вы можете выделить дату начала и конца, чтобы получить расписание на этот диапазон.", size=(200, 50))
        self.date_label = wx.StaticText(self.panel, label="Выберите дату")
        self.date_picker = DatePicker(self.panel, self.schedule)
        self.control = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(600, 400))
        self.savetotxtbtn = wx.Button(self.panel, label="Сохранить в файл")
        self.savetotxtbtn.Bind(wx.EVT_BUTTON, self.OnSaveToTxt)
        # layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer2=wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.hint, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.date_label, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.date_picker, 1, wx.ALL | wx.EXPAND, 5)
        sizer2.Add(self.control, 0, wx.ALL | wx.EXPAND, 5)
        sizer2.Add(self.savetotxtbtn, 0, wx.ALL | wx.EXPAND, 5)
        hsizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 5)
        hsizer.Add(sizer2, 1, wx.ALL | wx.EXPAND, 5)
        hsizer.AddStretchSpacer(1)  # add a stretch spacer to make the date picker narrower
        self.panel.SetSizer(hsizer)
        self.Bind(wx.EVT_CLOSE, self.exit)
        self.CreateStatusBar()
        self.menubar()
        self.Centre()
        self.Show(True)
        #endregion
        #if (getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')) or True:  # when bug is fixed, remove or True
        if (n:=news()) is not None:
            self.app.send_command(["toast", "Новость!", n, "ms-winsoundevent:Notification.Looping.Call10"])  # call10 is the best sound
            PopUpMSG(self, "Новость!", n).ShowModal()
        self.status("Авторизация...")

    def on_update(self, status: bool, version):
        # if status, show do you wanna update yes no dialog. If yes, self.updator.q.put(True)
        if status:
            with YouWannaUpdateDialog(self) as ywud:
                if ywud.ShowModal() == wx.ID_OK:
                    self.updater.queue.put(True)  # start the update
        else:
            self.updater.queue.put(False)  # stop the thread

    def on_total(self, total):
        # lets stop the app thread. It is not needed while updating.
        self.app.send_command(["exit"])
        self.progress=ProgressDlg(self, total)
        self.progress.Show()

    def on_progress(self, progress):
        # update the progress dialog
        if self.progress:
            if self.progress.closed:
                self.updater.stop()
                self.progress=None  # to not update the progress bar after it is closed
                # i think we should exit because app thread is stopped
                self.exit()
                return
            self.progress.Update(progress)
        else:
            # lets close the updater
            self.updater.stop()

    def on_restart(self):
        # close the progress dialog and restart the app
        if self.progress:
            self.progress.Close()
        restart(self)  # it receives wxparent as self to close the main window

    def menubar(self):
        # create a menubar
        menubar = wx.MenuBar()
        filemenu = wx.Menu()
        # save to txt
        filemenu.Append(wx.ID_SAVE, "Сохранить в файл\tCTRL+S", "Сохранить расписание в файл")
        filemenu.Append(wx.ID_EXIT, "Выход\tAlt+F4", "Выход из программы")
        helpmenu = wx.Menu()
        helpmenu.Append(wx.ID_ABOUT, "О программе\tF1", "О программе")
        menubar.Append(filemenu, "Файл")
        menubar.Append(helpmenu, "Помощь")
        self.Bind(wx.EVT_MENU, self.OnSaveToTxt, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.exit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        # shortcuts
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('S'), wx.ID_SAVE), (0, wx.WXK_F1, wx.ID_ABOUT)])
        self.SetAcceleratorTable(accel_tbl)
        self.SetMenuBar(menubar)

    def OnAbout(self, event):
        # make the popup like in news with readme.txt
        with open("readme.txt", "r", encoding="UTF-8") as f:
            readme=f.read()
        PopUpMSG(self, "О программе", readme).ShowModal()
        event.Skip()

    def status(self, text, speak=True):
        self.SetStatusText(text)
        if speak:
            tolk.output(text)

    def OnSaveToTxt(self, event):
        # save to schedule.txt
        event.Skip()
        with open("schedule.txt", "w", encoding="UTF-8") as f:
            f.write(self.control.GetValue())
        self.status("Расписание сохранено в schedule.txt")


    def schedule(self, dates=[], toast=False):
        # get the schedule for the selected date
        if len(dates)==0:
            return  # we are not on the leaf of the tree
        self.status("Получение расписания...", False)
        self.control.SetValue("Получение расписания...")
        start_date=min(dates)
        end_date=max(dates) if len(dates)>1 else None  # if there is only one date, end_date is None
        schedcb=lambda schedule: self.schedule_cb(schedule, toast)
        self.app.send_command(["schedule", start_date, end_date, None], schedcb)
        # that's all. This function ends here. The schedule will be displayed in the control when the app thread finishes the command.

    def check_auth_cb(self, state):
        if state==True:  #noqa
            #we ask for name
            if self.app.schedule.people.current==noone:
                self.ask_fullname()
            else:
                self.authed=True
                self.SetTitle(f"Расписание САФУ - {self.app.schedule.people.current.name}")
                self.status("Получение расписания...", True)
                self.schedule(self.date_picker.get_selected_date(), True)
        elif state==... or state==False:  #noqa
            if state==False:  #noqa
                self.show_error("Неверный email или пароль.")
            self.ask_emailnpassword()

    def search_cb(self, results):
        result=self.choose_from_results(results)
        if result is None:
            self.show_error("Ничего не найдено или не выбрано.")
            self.ask_fullname()
            return
        self.app.send_command(["saveperson", result])
        self.authed=True
        self.status("Получение расписания...", True)
        self.schedule(self.date_picker.get_selected_date(), True)

    def schedule_cb(self, schedule, toast=False):
        self.control.SetValue(schedule)
        self.status("Расписание получено.", toast)  # if toast is True, it will be spoken
        if toast:
            # the reason for setting title here is that saveperson command is async and we don't know when it will finish
            self.SetTitle(f"Расписание САФУ - {self.app.schedule.people.current.name}")
            self.app.send_command(["toast", "Расписание САФУ", schedule])


    def ask_emailnpassword(self):
        with AuthInput(self, "Введите email и пароль от модеуса") as authinput:
            status=authinput.ShowModal() == wx.ID_OK
            if status:
                email, password=authinput.GetValues()
                self.app.send_command(["check_credentials", email, password, False]) # check the credentials with no direct pass
            else:
                self.exit()  # user pressed cancel

    def ask_fullname(self, itsme=False):
        with GUInput(self, "Введите ФИО") as guinput:
            status=guinput.ShowModal() == wx.ID_OK
            if status:
                name=guinput.value
                self.app.send_command(["fullname", name], self.search_cb)
            else:
                if itsme: # if asked for my name, exit. In the future it can ask for friend's name for getting their schedule.
                    self.exit()
        self.status("Поиск...")

    def choose_from_results(self, results):
        # results is a list of person dicts with name and other info. Return the person index
        if len(results)==0:
            self.show_error("Ничего не найдено.")
            return -1
        elif len(results)==1:
            return 0
        people=[]
        for person in results:
            people.append(str(person))
        with ChooseFromList(self, "Выберите правильный вариант из списка", people, range(len(results))) as cfl:
            status=cfl.ShowModal() == wx.ID_OK
            selection=cfl.value
            if status:
                return selection
            return None

    def show_error(self, message, exit=False):
        wx.MessageBox(message, "Ошибка", wx.OK | wx.ICON_ERROR)
        if exit:
            self.exit()

    def exit(self, event=None):
        self.status("Выход...")
        self.SetTitle("Выход...")
        self.app.send_command(["exit"])
        self.app.join(timeout=5)
        print("Exiting...")
        #if event:
            #event.Skip()
        #else:
        self.Destroy()  # if called from code


showhide = False
def toggle():
    global showhide
    if showhide:
        frame.Show()
    else:
        frame.Hide()
    showhide = not showhide




if __name__ == "__main__":
    wxapp = wx.App(False)
    if "hide" in sys.argv:  # run as daemon
        showhide = True
    with tolk.tolk():  # for screen reader
        frame = MainWindow()
        wxapp.MainLoop()