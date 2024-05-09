# gui for NARFU schedule viewer.
# WXPython

import dotenv # for email and password
import wx
from threading import Thread
from guinput import GUInput, ChooseFromList, AuthInput
from datetime import datetime
from calendar import isleap
from app_logic import App

months=["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

dotenv.load_dotenv(".env")

class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title="Расписание САФУ", size=(800, 600), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        self.app=App()  # start app thread before anything else to not wait.
        self.person=None
        self.authed=False
        # panel
        self.panel = wx.Panel(self, -1)
        # create the date picker
        self.custom_date_picker()
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
        # command checker runs over and over again by wx timer
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.reply_checker, self.timer)
        self.timer.Start(milliseconds = 750, oneShot = True)  # run the reply checker every 750 ms
        print("timer started")

    def custom_date_picker(self):
        # the default date picker is not screen reader friendly. We make a custom that allows to tab navigate through the window.
        # so we will make a custom date picker using tree control. It has 2 subtrees for current year and next year, and each subtree has 12 subtrees for each month, and each month has x subtrees for each day. (taking into account leap years)
        self.date_picker = wx.TreeCtrl(self.panel)
        root = self.date_picker.AddRoot("root")
        years=[datetime.now().year, datetime.now().year+1]
        current_year = self.date_picker.AppendItem(root, str(years[0]))
        next_year = self.date_picker.AppendItem(root, str(years[1]))
        for i in range(12):
            month = self.date_picker.AppendItem(current_year, months[i])
            ny_month = self.date_picker.AppendItem(next_year, months[i])
            days = [0,0]
            if i in [1, 3, 5, 7, 8, 10, 12]:
                days = [31, 31]
            elif i in [4, 6, 9, 11]:
                days = [30, 30]
            else:
                days=[(29 if isleap(years[0]) else 28), (29 if isleap(years[1]) else 28)]
            for j in range(1, days[0]+1):
                self.date_picker.AppendItem(month, str(j))
            for j in range(1, days[1]+1):
                self.date_picker.AppendItem(ny_month, str(j))
        # focus the current date
        self.focus_tree_item_by_datetime(datetime.now())
        self.date_picker.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnDateChanged)        

    def focus_tree_item_by_datetime(self, date):
        # get the tree item by the date
        # date is a datetime object
        year = date.year
        month = date.month
        day = date.day
        root = self.date_picker.GetRootItem()
        year_item = self.get_year_item(year)
        if year_item is None:
            return
        month_item = self.get_month_item(year_item, months[month-1])
        if month_item is None:
            return
        day_item = self.get_day_item(month_item, day)
        if day_item is None:
            return
        self.date_picker.SelectItem(day_item)

    def get_year_item(self, year):
        root = self.date_picker.GetRootItem()
        item, cookie = self.date_picker.GetFirstChild(root)
        while item.IsOk():
            if self.date_picker.GetItemText(item) == str(year):
                return item
            item, cookie = self.date_picker.GetNextChild(root, cookie)
        return None

    def get_month_item(self, year_item, month):
        item, cookie = self.date_picker.GetFirstChild(year_item)
        while item.IsOk():
            if self.date_picker.GetItemText(item) == month:
                return item
            item, cookie = self.date_picker.GetNextChild(year_item, cookie)
        return None

    def get_day_item(self, month_item, day):
        item, cookie = self.date_picker.GetFirstChild(month_item)
        while item.IsOk():
            if self.date_picker.GetItemText(item) == str(day):
                return item
            item, cookie = self.date_picker.GetNextChild(month_item, cookie)
        return None

    def get_selected_date(self):
        # get the selected date from the tree control
        item = self.date_picker.GetSelection()
        # check if the item is from the leaf before getting the date
        if not (item is not None and self.date_picker.ItemHasChildren(item) == False):
            return None
        if item.IsOk():
            day = int(self.date_picker.GetItemText(item))
            month = months.index(self.date_picker.GetItemText(self.date_picker.GetItemParent(item))) + 1
            year = int(self.date_picker.GetItemText(self.date_picker.GetItemParent(self.date_picker.GetItemParent(item))))
            return datetime(year, month, day)
        return None

    def OnSaveToTxt(self, event):
        # save to schedule.txt
        event.Skip()
        with open("schedule.txt", "w") as f:
            f.write(self.control.GetValue())
        self.SetStatusText("Расписание сохранено в schedule.txt")


    def OnDateChanged(self, event):
        # get the schedule
        event.Skip()
        if self.authed:
            self.schedule()
        event.Skip()


    def schedule(self):
        # get the schedule for the selected date
        date = self.get_selected_date()
        if date is None:
            self.show_error("Выберите дату.")
            return
        self.SetStatusText("Получение расписания...")
        self.control.SetValue("Получение расписания...")
        self.app.send_command(["schedule", date, None, None]) # end date and overlap are None
        # that's all. This function ends here. The schedule will be displayed in the control when the app thread finishes the command.

    def reply_checker(self, event, *args): # now commands are tuples, so we can use tuple match command[0]
        event.Skip()
        # if i will get headaches from this, the credential checker will return quickly and if it is not authed, it will ask for credentials again.
        if not self.app.has_reply:
            return
        reply = self.app.get_reply()
        match reply[0]:
            case "Unknown":
                self.show_error("Ошибка. Поток приложения плетёт всякую чушь. Отправьте разработчику.", True)
            case "auth":
                # now we check. If welcome, we do nothing. If invalid or credentials, we ask for credentials.
                if reply[1]=="welcome":
                    #we ask for name
                    if self.app.person is None:
                        self.ask_fullname()
                elif reply[1]=="invalid" or reply[1]=="credentials":
                    if reply[1]=="invalid":
                        self.show_error("Неверный email или пароль.")
                    self.ask_emailnpassword()


            case "search":
                result=self.choose_from_results(reply[1])
                if result is None:
                    self.show_error("Ничего не найдено или не выбрано.")
                    self.ask_fullname()
                    return
                self.app.send_command(["saveperson", result])
                self.authed=True
                self.SetStatusText("Получение расписания...")
                self.schedule()
            case "schedule":
                self.control.SetValue(reply[1])
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
            print("before showmodal")
            status=guinput.ShowModal() == wx.ID_OK
            print("after showmodal")  # frost! not responding
            if status:
                name=guinput.value
                self.app.send_command(["fullname", name])
            else:
                if itsme: # if asked for my name, exit. In the future it can ask for friend's name for getting their schedule.
                    self.exit()
        self.SetStatusText("Поиск...")

    def choose_from_results(self, results):
        # results is a list of person dicts with name and other info. Return the person dict that the user chose.
        if len(results)==0:
            self.show_error("Ничего не найдено.")
            return None
        elif len(results)==1:
            return results[0]  # dont need to ask the user
        
        with ChooseFromList(self, "Выберите правильный вариант из списка", [person["name"] for person in results], results) as cfl:
            status=cfl.ShowModal() == wx.ID_OK
            selection=cfl.GetSelection()
            if status:
                return selection
            return None

    def show_error(self, message, exit=False):
        wx.MessageBox(message, "Ошибка", wx.OK | wx.ICON_ERROR)
        if exit:
            self.exit()

    def exit(self, event=None):
        if event: event.Skip()
        self.SetStatusText("Выход...")
        self.SetTitle("Выход...")
        self.app.send_command(["exit"])
        self.app.join()  # we dont cut, we wait like a gentleman
        self.Close()



# make fake callbacks for testing
if __name__ == "__main__":
    wxapp = wx.App(False)
    frame = MainWindow()
    wxapp.MainLoop()