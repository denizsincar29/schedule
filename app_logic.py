# app logic for the wxpython app
'''
a short doc on how to send commands to the app thread:
- the command is a list with the first element being the command name and the rest being the arguments
- the command is send using the send_command method
- the command is executed in the app thread and the result is sent back to the main thread using the callback function
- at the start of the app thread, the on_auth function is called with the result of the authentication. If explisitly needed, the check_credentials function can be called to re-authenticate the user with the None callback, since the callback for check credentials is on_auth.
commands:
- schedule: get the schedule for the current person. The arguments are the start and end dates in the datetime object and an overlap person id (str). The result is the schedule string.
- fullname: search for a person by their full name. The argument is the full name. The result is a list of person dicts.
saveperson: save the person with the given index in results list. The arguments is the person id and a boolean whether this person is the main person or friend which schedule is being viewed. No callback.
- check_credentials: check the credentials. The arguments are the email and password. The result is the authentication result, which is passed to the on_auth function. No other callback.
- exit: exit the app thread. No arguments, no callback.


'''


from schedule import Schedule, auth, noone
from threading import Thread
from queue import Queue
from random import choice
from wx import CallAfter as wxrun  # fully rewriting the thread not to use queues.
from win11toast import notify
from ical_share import upload_ical, get_ical, GotICalCheck
import os
import dotenv # move dotenv check here


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
            command.extend([None]*(5-len(command)))
            match command[0]:
                case "schedule":
                    itsme=command[3] if command[3] is not None else True
                    together=command[4] if command[4] is not None else False
                    c_person=self.schedule.people.current if itsme else self.schedule.people.friend
                    t_person=self.schedule.people.current if not itsme and together else noone  # if we are together, we need to pass the friend. Otherwise, we pass noone
                    wxrun(cb, self.schedule.schedule(c_person, command[1], command[2], t_person).humanize())
                case "fullname":
                    wxrun(cb, self.schedule.search_person(command[1], False), command[2])
                case "saveperson":
                    if command[2] is None:
                        command[2]=True  # we need to pass a boolean to the function
                    self.schedule.save_result(command[1], command[2])
                    diffs=self.schedule.get_month(-1)  # -1 is the current month
                    if len(diffs)>0:
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
                        wxrun(cb, str(self.schedule.who_goes(evt)), str(evt))
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
        if self.on_auth:
            wxrun(self.on_auth, authed, errmsg)

    def send_command(self, command, on_finish=None):
        self.forward.put((command, on_finish))

