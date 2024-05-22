# guinput
import wx
import qrcode

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
        st1 = wx.StaticText(panel, label='Введите текст:')
        hbox1.Add(st1, flag=wx.RIGHT, border=8)
        self.tc = wx.TextCtrl(panel)
        hbox1.Add(self.tc, proportion=1)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        # ok button triggers on enter also, cancel button triggers on esc
        okButton = wx.Button(panel, label='ОК', id=wx.ID_OK)
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        cancelButton = wx.Button(panel, label='Отменить', id=wx.ID_CANCEL)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnClose)
        hbox2.Add(cancelButton, flag=wx.LEFT, border=5)
        hbox2.Add(okButton)
        vbox.Add(hbox2, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
        panel.SetSizer(vbox)

    def OnOk(self, e):
        self.value=self.tc.GetValue()
        if self.value == "":
            return  # dont allow empty input. Only allow cancel
        self.status=True
        self.Close()
        e.Skip()
    def OnClose(self, e):
        self.Close()
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
        st1 = wx.StaticText(panel, label='Выберите из списка:')
        hbox1.Add(st1, flag=wx.RIGHT, border=8)
        self.choice = wx.Choice(panel, choices=self.choices)
        hbox1.Add(self.choice, proportion=1)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        # ok button triggers on enter also, cancel button triggers on esc
        okButton = wx.Button(panel, label='ОК', id=wx.ID_OK)
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        cancelButton = wx.Button(panel, label='Отменить', id=wx.ID_CANCEL)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnClose)
        hbox2.Add(cancelButton, flag=wx.LEFT, border=5)
        hbox2.Add(okButton)

        vbox.Add(hbox2, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
        panel.SetSizer(vbox)

    def OnOk(self, e):
        self.value=self.bound[self.choice.GetSelection()]
        self.status=True
        self.Close()
        e.Skip()
    def OnClose(self, e):
        self.Close()
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
        st1 = wx.StaticText(panel, label='Введите имя пользователя:')
        hbox1.Add(st1, flag=wx.RIGHT, border=8)
        self.tc1 = wx.TextCtrl(panel)
        hbox1.Add(self.tc1, proportion=1)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        st2 = wx.StaticText(panel, label='Введите пароль:')
        hbox2.Add(st2, flag=wx.RIGHT, border=8)
        self.tc2 = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        hbox2.Add(self.tc2, proportion=1)
        vbox.Add(hbox2, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(panel, label='ОК', id=wx.ID_OK)
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        cancelButton = wx.Button(panel, label='Отменить', id=wx.ID_CANCEL)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnClose)
        hbox3.Add(cancelButton, flag=wx.LEFT, border=5)
        hbox3.Add(okButton)
        vbox.Add(hbox3, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
        panel.SetSizer(vbox)

    def OnOk(self, e):
        self.values = self.GetValues()
        if self.values[0] == "" or self.values[1] == "":
            return
        self.status=True
        self.Close()
        e.Skip()
    def OnClose(self, e):
        self.Close()
        e.Skip()

    def GetValues(self):
        return self.tc1.GetValue(), self.tc2.GetValue()


class PopUpMSG(wx.Dialog):
    # like an inputbox, but the edit box is read-only and full of text
    def __init__(self, parent, title, text, cancelbtn=False):
        super(PopUpMSG, self).__init__(parent, title=title, size=(400, 200))
        self.InitUI(text, cancelbtn)
        self.Centre()

    def InitUI(self, text, cancelbtn):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        st1 = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL | wx.TE_RICH2, size=(400, 50))
        st1.SetValue(text)
        hbox1.Add(st1, flag=wx.RIGHT, border=8)
        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        oklabel="Закрыть" if not cancelbtn else "ОК"
        okButton = wx.Button(panel, label=oklabel, id=wx.ID_OK)
        okButton.Bind(wx.EVT_BUTTON, self.OnClose)
        hbox2.Add(okButton)
        if cancelbtn:
            cancelButton = wx.Button(panel, label='Отменить', id=wx.ID_CANCEL)
            cancelButton.Bind(wx.EVT_BUTTON, self.OnClose)
            hbox2.Add(cancelButton, flag=wx.LEFT, border=5)
        vbox.Add(hbox2, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
        panel.SetSizer(vbox)

    def OnClose(self, e):
        self.Close()
        e.Skip()

class ShowQRCode(wx.Dialog):
    def __init__(self, parent, title, text, closed_callback=lambda: None):
        super(ShowQRCode, self).__init__(parent, title=title, size=(600, 400))
        self.closed_callback = closed_callback
        self.InitUI(text)
        self.Centre()

    def InitUI(self, text):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        # Generate QR code
        qr_image = self.generate_qr_code(text)
        qr_bitmap = wx.Bitmap(qr_image)
        # Display QR code
        qr = wx.StaticBitmap(panel, bitmap=qr_bitmap)
        vbox.Add(qr, flag=wx.ALIGN_CENTER|wx.ALL, border=20)
        # Close button
        okButton = wx.Button(panel, label='Закрыть', id=wx.ID_OK)
        okButton.Bind(wx.EVT_BUTTON, self.on_close_button)  # if closed automatically, the callback will not be called
        vbox.Add(okButton, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)        
        panel.SetSizer(vbox)

    def generate_qr_code(self, text):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        return pil_image_to_wx_image(img)

    def on_close_button(self, event):
        wx.CallAfter(self.closed_callback)
        event.Skip()

    def OnClose(self, event):
        self.Destroy()

def pil_image_to_wx_image(pil_img, copy_alpha=True):
    """
    Image conversion from a Pillow Image to a wx.Image.
    """
    orig_width, orig_height = pil_img.size
    wx_img = wx.Image(orig_width, orig_height)
    wx_img.SetData(pil_img.convert('RGB').tobytes())
    if copy_alpha and (pil_img.mode[-1] == 'A'):
        alpha = pil_img.getchannel("A").tobytes()
        wx_img.InitAlpha()
        for i in range(orig_width):
            for j in range(orig_height):
                wx_img.SetAlpha(i, j, alpha[i + j * orig_width])
    return wx_img

def QRCode(text):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return pil_image_to_wx_image(img).ConvertToBitmap()



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

def popupmsg(parent, title, text, cancelbtn=False):
    if parent is None:
        app = wx.App()  #noqa F841
    with PopUpMSG(parent, title, text, cancelbtn) as inputDialog:
        status=inputDialog.ShowModal()
        return status==OK
    
def showqrcode(parent, title, text):
    if parent is None:
        app = wx.App()  #noqa F841
    with ShowQRCode(parent, title, text) as inputDialog:
        status=inputDialog.ShowModal()
        return status==OK  # always returns OK