# gui for NARFU schedule viewer.
# WXPython
import sys
import os
from ical_share import GotICalCheck
from shutil import rmtree
import screenreader as tolk
import wx
from guinput import GUInput, ChooseFromList, AuthInput, PopUpMSG, ShowQRCode
from datepicker import DatePicker
from app_logic import App
from schedule.parsers.people import noone, People
from news import news
from autoupdate.wxupdate import Updater, VERSION, restart, YouWannaUpdateDialog, ProgressDlg
from webbrowser import open as webopen

class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title=f"Расписание САФУ ({VERSION})", size=(800, 600), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        self.app=App(self.check_auth_cb, self.on_error)
        self.updater=Updater(self.on_update, self.on_total, self.on_progress, self.on_restart, self.on_no_update) if sys.platform=="win32" else None
        self.progress=None  # to not get attribute error
        self.offline=False
        self.authed=False
        self.must_check_auth=(False, False, "")  # if we need to check auth after updating
        self.itsme=True  # get my schedule. When it is False, it gets friend's schedule
        self.together=False  # get the schedule together with the friend, if False, get only the friend's schedule
        self.qrdialog=None
        #region GUI
        self.panel = wx.Panel(self, -1)
        self.hint = wx.StaticText(self.panel, label="Примечание. Вы можете выделить дату начала и конца, чтобы получить расписание на этот диапазон.", size=(200, 50))
        self.date_label = wx.StaticText(self.panel, label="Выберите дату")
        self.date_picker = DatePicker(self.panel, self.schedule)
        self.control = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL, size=(600, 400))
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
        self.Bind(wx.EVT_TEXT_URL, self.on_url_click)
        self.CreateStatusBar()
        self.menubar()
        self.Centre()
        self.Show(True)
        #endregion
        #if (getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')) or True:  # when bug is fixed, remove or True
        self.status("Авторизация...")

    def menubar(self):
        # create a menubar
        menubar = wx.MenuBar()
        filemenu = wx.Menu()
        filemenu.Append(wx.ID_SAVE, "Сохранить в файл\tCTRL+S", "Сохранить расписание в файл")
        filemenu.Append(wx.ID_FILE3, "Экспорт в календарь", "Экспортировать расписание в календарь на телефоне")
        filemenu.Append(wx.ID_FILE1, "Информация о паре\tCTRL+G", "Показать, кто идёт на эту пару")
        filemenu.AppendCheckItem(wx.ID_ADD, "Чужое расписание", "Добавить друга для просмотра его расписания")
        filemenu.AppendCheckItem(wx.ID_FILE2, "Просмотреть пересечение расписаний", "Просмотреть общие пары с другом")
        filemenu.Append(wx.ID_DELETE, "Очистить кеш", "Очистить кеш с расписанием")
        filemenu.Append(wx.ID_EXIT, "Выход\tAlt+F4", "Выход из программы")
        helpmenu = wx.Menu()
        helpmenu.Append(wx.ID_ABOUT, "О программе\tF1", "О программе")
        menubar.Append(filemenu, "Файл")
        menubar.Append(helpmenu, "Помощь")
        self.Bind(wx.EVT_MENU, self.OnSaveToTxt, id=wx.ID_SAVE)
        
        self.Bind(wx.EVT_MENU, self.who_goes, id=wx.ID_FILE1)
        self.Bind(wx.EVT_MENU, self.on_friend, id=wx.ID_ADD)
        self.Bind(wx.EVT_MENU, self.on_clear_cache, id=wx.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.on_together, id=wx.ID_FILE2)
        self.Bind(wx.EVT_MENU, self.on_ical, id=wx.ID_FILE3)
        self.Bind(wx.EVT_MENU, self.exit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        # shortcuts
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('S'), wx.ID_SAVE),
            (0, wx.WXK_F1, wx.ID_ABOUT),
            (wx.ACCEL_CTRL, ord('G'), wx.ID_FILE1),
        ])
        self.SetAcceleratorTable(accel_tbl)
        self.SetMenuBar(menubar)

    def on_ical(self, event):
        if self.offline:
            self.show_error("Нет подключения к интернету. Невозможно экспортировать календарь.")
            return
        def stop_cb():
            if self.app.autoclose is not None and self.app.autoclose.is_alive():
                self.app.autoclose.q.put(True)
        def ical_cb(status, ical):
            if not status:
                self.show_error(f"Ошибка при загрузке календаря на сервер: {ical}")
                return
            self.qrdialog=ShowQRCode(self, "QR-код для добавления в календарь", ical, stop_cb)
            self.qrdialog.Show()
        def close_cb():
            if self.qrdialog is not None:
                self.qrdialog.Close()
                self.qrdialog=None
        self.app.send_command(["ical", close_cb], ical_cb)

    def on_clear_cache(self, event):
        rmtree("cache", ignore_errors=True)  # remove the cache folder
        os.remove("people.json")
        # msg box and exit.
        wx.MessageBox("Кеш очищен. Перезапустите программу.", "Кеш очищен", wx.OK | wx.ICON_INFORMATION)
        self.exit()

    def on_url_click(self, event):
        url = self.control.GetRange(event.GetURLStart(), event.GetURLEnd())
        webopen(url)
        event.Skip()

    def on_friend(self, event):
        self.itsme=not event.IsChecked()  # if checked, it is not me
        if not self.itsme:
            self.ask_fullname(False)  # ask for friend's name
        else:
            self.together=False  # if it is me, it is not together!
            self.GetMenuBar().Check(wx.ID_FILE2, False)  # uncheck the together menu item
            # save the friend as noone
            self.app.schedule.people.friend=noone
            self.schedule(self.date_picker.get_selected_date(), True)
        event.Skip()

    def on_together(self, event):
        self.together=event.IsChecked()
        if self.together and self.itsme:  # if we are together, we need to ask for friend's name
            self.ask_fullname(False)
            self.itsme=False
            self.GetMenuBar().Check(wx.ID_ADD, True)  # check the friend menu item
        #if not itsme, everything is already set. Just schedule. But we can't be together without a friend because the on_friend unchecks this menu item.

        self.schedule(self.date_picker.get_selected_date(), True)
        event.Skip()

    def on_update(self, status: bool, version):
        # if status, show do you wanna update yes no dialog. If yes, self.updater.q.put(True)
        if status:
            with YouWannaUpdateDialog(self) as ywud:
                if ywud.ShowModal() == wx.ID_OK:
                    self.updater.queue.put(True)  # start the update
                else:
                    self.updater.queue.put(False)
        else:
            self.updater.queue.put(False)  # stop the thread

    def on_no_update(self):
        # we decided not to update. Proceed with the app
        if (n:=news()) is not None:
            self.app.send_command(["toast", "Новость!", n, "ms-winsoundevent:Notification.Looping.Call10"])  # call10 is the best sound
            PopUpMSG(self, "Новость!", n).ShowModal()
        if self.must_check_auth[0]:  # we scheduled check_auth_cb while updating
            self.check_auth_cb(self.must_check_auth[1], self.must_check_auth[2])


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


    def OnAbout(self, event):
        # make the popup like in news with readme.txt
        with open("readme.txt", "r", encoding="UTF-8") as f:
            readme=f.read()
        PopUpMSG(self, "О программе", readme).ShowModal()
        event.Skip()

    def status(self, text, speak=True):
        self.SetStatusText(text)
        if speak:
            sr.output(text)

    def OnSaveToTxt(self, event):
        with wx.FileDialog(self, "Сохранить расписание", defaultFile="schedule.txt", wildcard="Text files (*.txt)|*.txt", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            # save the schedule to the file
            pathname = fileDialog.GetPath()
        with open(pathname, "w", encoding="utf-8") as f:
            f.write(self.control.GetValue())
        self.status(f"Расписание сохранено в {pathname}")
        event.Skip()


    def schedule(self, dates=[], toast=False):
        # get the schedule for the selected date
        if len(dates)==0:
            return  # we are not on the leaf of the tree
        self.status("Получение расписания...", False)
        self.control.SetValue("Получение расписания...")
        start_date=min(dates)
        end_date=max(dates) if len(dates)>1 else None  # if there is only one date, end_date is None
        schedcb=lambda schedule: self.schedule_cb(schedule, toast)
        self.app.send_command(["schedule", start_date, end_date, self.itsme, self.together], schedcb)
        # that's all. This function ends here. The schedule will be displayed in the control when the app thread finishes the command.

    def check_auth_cb(self, state, msg):
        if self.progress:  # dont do anything if progress dialog is open. We dont want to show any dialogs while updating
            return
        if self.updater is not None and not self.updater.dead:
            self.must_check_auth=(True, state, msg)  # here we end.
            return
        if state==True:  #noqa
            #we ask for name
            if self.app.schedule.people.current==noone:
                self.ask_fullname()
            else:
                self.authed=True
                self.status("Получение расписания...", True)
                self.schedule(self.date_picker.get_selected_date(), True)
        elif state==... or state==False:  #noqa
            if state==False:  #noqa
                self.show_error(msg, not ("email" in msg))  # if email is in the message, we can ask for email and password again. Otherwise, exit
            self.ask_emailnpassword()

    def on_error(self, msg):
        self.offline=True
        if msg!="":  # if msg is empty, it is not an error, but just we are offline
            wx.CallAfter(self.show_error, f"Модеус глючит: {msg}", False)

    def search_cb(self, results, itsme=True):
        result=self.choose_from_results(results)
        if result is None:
            self.show_error("Ничего не найдено или не выбрано.")
            self.ask_fullname(itsme)
            return
        self.app.send_command(["saveperson", result, itsme])
        if itsme:
            self.authed=True
        self.status("Получение расписания...", True)
        self.schedule(self.date_picker.get_selected_date(), True)

    def schedule_cb(self, schedule, toast=False):
        if "Пара" not in schedule and self.offline:
            self.control.SetValue("Нет подключения к интернету или модеус умер. Попробуйте позже.")
            self.status("Нет подключения к интернету или модеус умер. Попробуйте позже.", toast)
            return
        self.control.SetValue(schedule)
        self.status("Расписание получено.", toast)  # if toast is True, it will be spoken
        if toast:
            # the reason for setting title here is that saveperson command is async and we don't know when it will finish
            if not self.together and not self.itsme:  # only friend's schedule
                title=f"Расписание САФУ - {self.app.schedule.people.friend.name}"
            elif self.together and not self.itsme:  # together with friend
                title=f"Расписание САФУ - {self.app.schedule.people.current.name} и {self.app.schedule.people.friend.name}"
            else:  # only my schedule. Dont give a hell about together
                title=f"Расписание САФУ - {self.app.schedule.people.current.name}"
            if self.offline:
                title+=" (оффлайн)"
            self.SetTitle(title)
            self.app.send_command(["toast", "Расписание САФУ", schedule])

    def who_goes(self, event):  # before it was who_goes, but now it shows the event info
        if self.offline:
            self.show_error("Нет подключения к интернету. Невозможно получить информацию о паре.")
            return
        # an event starts with the word "Пара" and ends with the next "Пара" or the end of the text. Return the event text
        cursor=self.control.GetInsertionPoint()
        #who_goes_cb=lambda result, evt: PopUpMSG(self, "Информация о паре", f"{evt}\n\nКто записан на пару:\n{result}").ShowModal()
        # lets define callback function. If both args are "", it speaks курсор не наведён на пару
        def who_goes_cb(result, evt):
            if result=="" and evt=="":
                self.status("Курсор не наведён на пару.")
            else:
                PopUpMSG(self, "Информация о паре", f"{evt}\n\nКто записан на пару:\n{result}").ShowModal()
        self.app.send_command(["who_goes", cursor], who_goes_cb)
        event.Skip()



    def ask_emailnpassword(self):
        if self.offline:
            # we can't check the credentials without internet, show the error and exit
            self.show_error("Нет подключения к интернету. Невозможно проверить логин и пароль.", True)
            return # in case.
        with AuthInput(self, "Введите email и пароль от модеуса") as authinput:
            status=authinput.ShowModal() == wx.ID_OK
            if status:
                email, password=authinput.GetValues()
                self.app.send_command(["check_credentials", email, password, False]) # check the credentials with no direct pass
            else:
                self.exit()  # user pressed cancel

    def ask_fullname(self, itsme=True):
        with GUInput(self, "Введите ФИО") as guinput:
            status=guinput.ShowModal() == wx.ID_OK
            if status:
                name=guinput.value
                self.app.send_command(["fullname", name, itsme], self.search_cb)
            else:
                if itsme: # if asked for my name, exit. In the future it can ask for friend's name for getting their schedule.
                    self.exit()
        self.status("Поиск...")

    def choose_from_results(self, results):
        # results is a list of person dicts with name and other info. Return the person index
        if len(results)==0:
            if self.offline:
                self.show_error("Нет подключения к интернету. Невозможно получить результаты поиска.", self.itsme)  # if itsme, exit. Otherwise, disable friend mode
                if not self.itsme:  #uncheck all friend related items
                    self.GetMenuBar().Check(wx.ID_ADD, False)
                    self.GetMenuBar().Check(wx.ID_FILE2, False)
                    self.itsme=True
                    self.together=False
                return -1
            self.show_error("Ничего не найдено.")
            return -1
        elif len(results)==1:
            return 0  # incase we get cache if offline
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
    with tolk.ScreenReader() as sr:
        frame = MainWindow()
        wxapp.MainLoop()