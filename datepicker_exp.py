# a simple wx calender dialog

import wx
from wx.adv import CalendarCtrl
from datetime import datetime

class DatePicker(CalendarCtrl):
    def __init__(self, parent, on_change, *args, **kwargs):
        super(DatePicker, self).__init__(parent, *args, **kwargs)
        self.on_change=on_change
        self.Bind(wx.adv.EVT_CALENDAR_SEL_CHANGED, self.on_date_change)

    def on_date_change(self, event):
        date=self.GetDate()
        # pass datetime object
        self.on_change(date)
        event.Skip()

    def set_by_datetime(self, date):
        self.SetDate(date)