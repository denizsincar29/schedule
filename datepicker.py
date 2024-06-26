# a custem datepicker widget for wxPython

import wx
from datetime import date
from dateutil.relativedelta import relativedelta
from pytz import timezone
from calendar import isleap
moscow=timezone("Europe/Moscow")
months=["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]  # 1-based index

class DatePicker(wx.TreeCtrl):
    def __init__(self, parent, dt_callback, *args, **kwargs):
        super(DatePicker, self).__init__(parent, style=wx.TR_MULTIPLE, *args, **kwargs)
        self.root = self.AddRoot("root")
        years = [date.today().year, date.today().year + 1]
        self.current_year = self.AppendItem(self.root, str(years[0]))
        self.next_year = self.AppendItem(self.root, str(years[1]))
        for i in range(1, 13):
            month = self.AppendItem(self.current_year, months[i-1])
            ny_month = self.AppendItem(self.next_year, months[i-1])
            days = [0, 0]
            if i in [1, 3, 5, 7, 8, 10, 12]:
                days = [31, 31]
            elif i in [4, 6, 9, 11]:
                days = [30, 30]
            else:
                days = [(29 if isleap(years[0]) else 28), (29 if isleap(years[1]) else 28)]
            for j in range(1, days[0] + 1):
                self.AppendItem(month, str(j))
            for j in range(1, days[1] + 1):
                self.AppendItem(ny_month, str(j))
        self.focus_tree_item_by_date(date.today())
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnDateChanged)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnDateChanged)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnDateChanged)
        self.dt_callback = dt_callback

    def focus_tree_item_by_date(self, date):
        year = date.year
        month = date.month
        day = date.day
        year_item = self.get_year_item(year)
        if year_item is None:
            return
        month_item = self.get_month_item(year_item, months[month - 1])
        if month_item is None:
            return
        day_item = self.get_day_item(month_item, day)
        if day_item is None:
            return
        self.SelectItem(day_item)

    def get_year_item(self, year):
        item, cookie = self.GetFirstChild(self.root)
        while item.IsOk():
            if self.GetItemText(item) == str(year):
                return item
            item, cookie = self.GetNextChild(self.root, cookie)
        return None

    def get_month_item(self, year_item, month):
        item, cookie = self.GetFirstChild(year_item)
        while item.IsOk():
            if self.GetItemText(item) == month:
                return item
            item, cookie = self.GetNextChild(year_item, cookie)
        return None

    def get_day_item(self, month_item, day):
        item, cookie = self.GetFirstChild(month_item)
        while item.IsOk():
            if self.GetItemText(item) == str(day):
                return item
            item, cookie = self.GetNextChild(month_item, cookie)
        return None


    # new version. If month is selected instead of day, it will return first and last day of the month.
    def get_selected_date(self):
        items = self.GetSelections()
        dates=[]
        for item in items:  # if no item, it will pass
            if item is None:
                continue
            if item.IsOk():
                if not self.ItemHasChildren(item):
                    day = int(self.GetItemText(item))
                    month = months.index(self.GetItemText(self.GetItemParent(item))) + 1
                    year = int(self.GetItemText(self.GetItemParent(self.GetItemParent(item))))
                    dates.append(date(year, month, day))
                elif self.ItemHasChildren(item) and not self.ItemHasChildren(self.GetFirstChild(item)[0]): # if month is selected
                    month = months.index(self.GetItemText(item)) + 1
                    year = int(self.GetItemText(self.GetItemParent(item)))
                    start_date=date(year, month, 1)
                    end_date=start_date+relativedelta(months=1)-relativedelta(days=1)
                    dates.append(start_date)
                    dates.append(end_date)
        return dates

    def OnDateChanged(self, event):
        self.dt_callback(self.get_selected_date())
        event.Skip()


if __name__ == "__main__":
    # test the datepicker
    app = wx.App(False)
    frame = wx.Frame(None, title="Datepicker test")
    panel = wx.Panel(frame)
    date_picker = DatePicker(panel, lambda x: print(x))
    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(date_picker, 1, wx.EXPAND)
    panel.SetSizer(sizer)
    frame.Show()
    app.MainLoop()