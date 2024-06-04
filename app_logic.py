# app logic for the wxpython app


from schedule import Schedule, auth, noone
from threading import Thread
from queue import Queue
from random import choice
from wx import CallAfter as wxrun  # fully rewriting the thread not to use queues.
from ical_share import upload_ical, get_ical, GotICalCheck
from screenreader import notify
import os
import asyncio
import dotenv # move dotenv check here
import ctypes
from time import time

def raise_to_thread(target_tid, exception):
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), ctypes.py_object(exception))
    # ref: http://docs.python.org/c-api/init.html#PyThreadState_SetAsyncExc
    if ret == 0:
        raise ValueError("Invalid thread ID")
    elif ret > 1:
        # Huh? Why would we notify more than one threads?
        # Because we punch a hole into C level interpreter.
        # So it is better to clean up the mess.
        ctypes.pythonapi.PyThreadState_SetAsyncExc(target_tid, NULL)
        raise SystemError("PyThreadState_SetAsyncExc failed")

dotdotdot=... # for the match statement


def randomsound():
    greatsounds=["Alarm4", "Alarm6", "Alarm10"]
    return f"ms-winsoundevent:Notification.Looping.{choice(greatsounds)}"




class App(Thread):
    def __init__(self, on_auth=lambda: None, on_error=lambda: None):
        Thread.__init__(self)
        self.forward = Queue()
        self.schedule = None  # don't use this if not authed. Else you'll get angry customers chasing you with pitchforks.
        self.on_auth=on_auth  # function to run after the user has been authenticated
        self.on_error=on_error  # function to run after an error has occured
        self.confirmed_offline=False  # if we have confirmed that we are in offline mode, we will not call the on_error function again
        self.autoclose=None  # if we have a GotICalCheck thread, we need to keep it here
        self.daemon = True  # we don't want to keep the program running after the main thread exits
        self.start()

    def run(self):
        dotenv.load_dotenv(".env")  # dont eat from the parent directory.
        email=os.environ.get("MODEUS_EMAIL", "")
        password=os.environ.get("MODEUS_PASSWORD", "")
        self.check_credentials(email, password, True)
        if self.schedule is not None and self.schedule.no_internet and not self.confirmed_offline:
            wxrun(self.on_error, "Нет интернета или модеус глючит. Программа будет работать в оффлайн режиме, то есть будет показывать только данные из кеша.")
            self.confirmed_offline=True
        while True:
            if self.schedule is not None and self.schedule.no_internet and not self.confirmed_offline:
                wxrun(self.on_error, "")  # without a message to trigger the gui offline boolean change
                self.confirmed_offline=True
            command, cb = self.forward.get()  # cb is a callback function to run after the command is executed
            if cb is None:
                cb=lambda *args, **kwargs: None
            command.extend([None]*(6-len(command)))
            match command[0]:
                case "schedule":
                    itsme=command[3] if command[3] is not None else True
                    together=command[4] if command[4] is not None else False
                    c_person=self.schedule.people.current if itsme else self.schedule.people.friend
                    t_person=self.schedule.people.current if not itsme and together else noone  # if we are together, we need to pass the friend. Otherwise, we pass noone
                    #self.schedule.schedule_async(c_person, command[1], command[2],  t_person, cb)  # very experimental
                    wxrun(cb, self.schedule.schedule(c_person, command[1], command[2], t_person).humanize(False))
                case "fullname":
                    wxrun(cb, self.schedule.search_person(command[1], False), command[2])
                case "saveperson":
                    if command[2] is None:
                        command[2]=True  # itsme
                    self.schedule.save_result(command[1], command[2])
                    diffs=self.schedule.get_month(-1)  # -1 is the current month
                    if len(diffs)>0 and command[2]:  # if we saved the main person, we need to notify the user
                        notify("Расписание изменилось!", diffs.human_diff(), audio=randomsound())
                case "check_credentials":
                    self.check_credentials(command[1], command[2], command[3])
                case "ical":
                    ical=self.schedule.last_events.ics()
                    status, message, filename=upload_ical(ical)
                    self.autoclose=GotICalCheck(filename, command[1])
                    wxrun(cb, status, message)
                case "who_goes": # command takes cursor position of an event and returns who goes there
                    evt=self.schedule.last_events.get_event_by_strindex(command[1])
                    if evt is None:
                        wxrun(cb, "", "")
                    else:
                        wxrun(cb, str(self.schedule.who_goes(evt)), evt.humanize(True))
                case "toast":
                    notify(command[1], command[2], audio=command[3])  # audio can be None or filename
                case "exit":
                    return  # exit the thread
                case _:
                    print(("Unknown", "command"))
            self.forward.task_done()


    def check_credentials(self, email, password, direct_pass=False):
        errmsg="Неверный логин или пароль" # default error message
        authed=direct_pass  # if we loaded the credentials from the environment, we don't need to check them
        if not email or not password:
            authed=... # we don't have the credentials
        if not direct_pass and auth!=...:
            authed, errmsg=auth(email, password)  #replace the default error message with the one from the server
        if authed==True:  #noq: F632
            if not direct_pass:
                os.environ["MODEUS_EMAIL"]=email
                os.environ["MODEUS_PASSWORD"]=password
                with open(".env", "w") as f:
                    f.write(f"MODEUS_EMAIL={email}\nMODEUS_PASSWORD={password}\n")
            self.schedule=Schedule(email, password, self.on_error)
            self.schedule.load_people()
            diffs=self.schedule.get_month(-1)  # -1 is the current month
            if len(diffs)>0 and command[2]:  # if we saved the main person, we need to notify the user
                notify("Расписание изменилось!", diffs.human_diff(), audio=randomsound())
        if self.on_auth:
            wxrun(self.on_auth, authed, errmsg)

    def send_command(self, command, on_finish=None):
        self.forward.put((command, on_finish))

