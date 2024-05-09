# guinput
import wx

# constants:
OK=wx.ID_OK
CANCEL=wx.ID_CANCEL


class GUInput(wx.Dialog):
    def __init__(self, parent, title):
        super(GUInput, self).__init__(parent, title=title, size=(250, 150))
        self.status=False  # False means cancel, True means OK
        self.value=""
        self.InitUI()
        self.Centre()

    def InitUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        st1 = wx.StaticText(panel, label='Enter the input:')
        hbox1.Add(st1, flag=wx.RIGHT, border=8)
        self.tc = wx.TextCtrl(panel)
        hbox1.Add(self.tc, proportion=1)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        # ok button triggers on enter also, cancel button triggers on esc
        okButton = wx.Button(panel, label='OK', id=wx.ID_OK)
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        cancelButton = wx.Button(panel, label='Cancel', id=wx.ID_CANCEL)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnClose)
        hbox2.Add(cancelButton, flag=wx.LEFT, border=5)
        hbox2.Add(okButton)

        vbox.Add(hbox2, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
        panel.SetSizer(vbox)

    def proper_close(self):
        if self.Parent is None:
            self.Destroy()
        else:
            self.Close()

    def OnOk(self, e):
        print("debug! Everything is ID_OK")
        self.value=self.tc.GetValue()
        if self.value == "":
            return  # dont allow empty input. Only allow cancel
        self.status=True
        self.proper_close()
        e.Skip()
    def OnClose(self, e):
        self.proper_close()
        e.Skip()

class ChooseFromList(wx.Dialog):
    def __init__(self, parent, title, choices, bound=None):  # bound is the parallel list to choices. So choices are for display, bound is for return
        super(ChooseFromList, self).__init__(parent, title=title, size=(250, 150))
        self.status=False  # False means cancel, True means OK
        self.value=""
        self.choices = choices
        self.bound = bound
        if self.bound is None:
            self.bound = choices
        self.InitUI()
        self.Centre()

    def InitUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        st1 = wx.StaticText(panel, label='Choose from the list:')
        hbox1.Add(st1, flag=wx.RIGHT, border=8)
        self.choice = wx.Choice(panel, choices=self.choices)
        hbox1.Add(self.choice, proportion=1)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        # ok button triggers on enter also, cancel button triggers on esc
        okButton = wx.Button(panel, label='OK', id=wx.ID_OK)
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        cancelButton = wx.Button(panel, label='Cancel', id=wx.ID_CANCEL)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnClose)
        hbox2.Add(cancelButton, flag=wx.LEFT, border=5)
        hbox2.Add(okButton)

        vbox.Add(hbox2, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
        panel.SetSizer(vbox)

    def proper_close(self):
        if self.Parent is None:
            self.Destroy()
        else:
            self.Close()

    def OnOk(self, e):
        self.value=self.bound[self.choice.GetSelection()]
        self.status=True
        self.proper_close()
        e.Skip()
    def OnClose(self, e):
        self.proper_close()
        e.Skip()


class AuthInput(wx.Dialog):
    def __init__(self, parent, title):
        super(AuthInput, self).__init__(parent, title=title, size=(250, 150))
        self.status=False
        self.values = ("" , "")
        self.InitUI()
        self.Centre()

    def InitUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        st1 = wx.StaticText(panel, label='Enter the username:')
        hbox1.Add(st1, flag=wx.RIGHT, border=8)
        self.tc1 = wx.TextCtrl(panel)
        hbox1.Add(self.tc1, proportion=1)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        st2 = wx.StaticText(panel, label='Enter the password:')
        hbox2.Add(st2, flag=wx.RIGHT, border=8)
        self.tc2 = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        hbox2.Add(self.tc2, proportion=1)
        vbox.Add(hbox2, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(panel, label='OK', id=wx.ID_OK)
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        cancelButton = wx.Button(panel, label='Cancel', id=wx.ID_CANCEL)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnClose)
        hbox3.Add(cancelButton, flag=wx.LEFT, border=5)
        hbox3.Add(okButton)
        vbox.Add(hbox3, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
        panel.SetSizer(vbox)

    def proper_close(self):
        if self.Parent is None:
            self.Destroy()
        else:
            self.Close()

    def OnOk(self, e):
        self.values = self.GetValues()
        if self.values[0] == "" or self.values[1] == "":
            return
        self.status=True
        self.proper_close()
        e.Skip()
    def OnClose(self, e):
        self.proper_close()
        e.Skip()

    def GetValues(self):
        return self.tc1.GetValue(), self.tc2.GetValue()
    

def inputbox(parent, title):
    if parent is None:
        app = wx.App()  #noqa F841
    with GUInput(Parent, title) as inputDialog:
        status=inputDialog.ShowModal()
        return status==OK, inputDialog.value

def authbox(parent, title):
    if parent is None:
        app = wx.App()  #noqa F841
    with AuthInput(parent, title) as inputDialog:
        status=inputDialog.ShowModal()
        return status==OK, *inputDialog.values  # no nested tuple

def choosebox(parent, title, choices, bound=None):
    if parent is None:
        app = wx.App()  #noqa F841
    with ChooseFromList(parent, title, choices, bound) as inputDialog:
        status=inputDialog.ShowModal()
        return status==OK, inputDialog.value
