# gui for NARFU schedule viewer.
# WXPython

import wx
from guinput import GUInput, ChooseFromList, AuthInput
from datepicker import DatePicker
from app_logic import App
import sys

class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title="Расписание САФУ", size=(800, 600), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        self.app=App(self.check_auth_cb)
        self.person=None
        self.authed=False
        # panel
        self.panel = wx.Panel(self, -1)
        # create the date picker
        self.date_picker = DatePicker(self.panel, self.schedule)  # on date change, get the schedule
        self.control = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY)  # we will use this to display the schedule
        self.savetotxtbtn = wx.Button(self.panel, label="Сохранить в файл")
        self.savetotxtbtn.Bind(wx.EVT_BUTTON, self.OnSaveToTxt)
        # layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.date_picker, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.control, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.savetotxtbtn, 0, wx.ALL | wx.EXPAND, 5)
        self.panel.SetSizer(sizer)
        self.Bind(wx.EVT_CLOSE, self.exit)
        self.CreateStatusBar()
        self.Centre()
        self.Show(True)
        self.SetStatusText("Авторизация...")

    def OnSaveToTxt(self, event):
        # save to schedule.txt
        event.Skip()
        with open("schedule.txt", "w") as f:
            f.write(self.control.GetValue())
        self.SetStatusText("Расписание сохранено в schedule.txt")




    def schedule(self, dates=[]):
        # get the schedule for the selected date
        if len(dates)==0:
            return  # we are not on the leaf of the tree
        self.SetStatusText("Получение расписания...")
        self.control.SetValue("Получение расписания...")
        start_date=min(dates)
        end_date=max(dates) if len(dates)>1 else None  # if there is only one date, end_date is None
        self.app.send_command(["schedule", start_date, end_date, None], self.schedule_cb)
        # that's all. This function ends here. The schedule will be displayed in the control when the app thread finishes the command.

    def check_auth_cb(self, state):
        if state==True:  #noqa
            #we ask for name
            if self.app.person is None:
                self.ask_fullname()
            else:
                self.authed=True
                self.SetStatusText("Получение расписания...")
                self.schedule(self.date_picker.get_selected_date())
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
        self.SetStatusText("Получение расписания...")
        self.schedule(self.date_picker.get_selected_date())

    def schedule_cb(self, schedule):
        self.control.SetValue(schedule)
        self.SetStatusText("Расписание получено.")





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
        self.SetStatusText("Поиск...")

    def choose_from_results(self, results):
        # results is a list of person dicts with name and other info. Return the person index
        if len(results)==0:
            self.show_error("Ничего не найдено.")
            return -1
        elif len(results)==1:
            return 0
        people=[]
        for person in results:
            people.append(self.app.schedule.humanize_person(person["id"], results))
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
        self.SetStatusText("Выход...")
        self.SetTitle("Выход...")
        self.app.send_command(["exit"])
        self.app.join()  # we dont cut, we wait like a gentleman
        if event:
            event.Skip()
        else:
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
    frame = MainWindow()
    wxapp.MainLoop()