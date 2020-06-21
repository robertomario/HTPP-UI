""" Display dialog window about layout """

# Author: Roberto Buelvas

from wx.lib.scrolledpanel import ScrolledPanel
import wx


class LayoutDialog(wx.Dialog):
    """ Class to define dialog window """

    def __init__(self, settings, *args, **kw):
        """ Create new dialog """
        super(LayoutDialog, self).__init__(*args, **kw)
        self.settings = settings
        self.initUI()
        self.SetSize((650, 500))
        self.Centre()
        self.SetTitle('Layout')

    def initUI(self):
        num_sensors = self.settings.ReadInt('numSensors', 1)

        vbox0 = wx.BoxSizer(wx.VERTICAL)
        pnl = ScrolledPanel(self)
        vbox1 = wx.BoxSizer(wx.VERTICAL)

        st = wx.StaticText(pnl, label="If the sensor numbers don't match, "
                                      + "make first the adjustments in "
                                      + "Settings>Ports", size=(600, 60))
        st.SetFont(wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.NORMAL))
        vbox1.Add(st, proportion=0, flag=wx.ALL)

        image = wx.Image('docs/diagram.png', wx.BITMAP_TYPE_ANY) \
                  .Rescale(450, 300)
        imageBitmap = wx.StaticBitmap(pnl, bitmap=wx.Bitmap(image))
        vbox1.Add(imageBitmap, proportion=1, flag=wx.ALL | wx.CENTER)

        st = wx.StaticText(pnl, label="All distances in cm")
        vbox1.Add(st, proportion=0, flag=wx.ALL)

        self.setting_to_control = {}

        self.addLabelledCtrl(pnl, vbox1, "DB1")
        self.addLabelledCtrl(pnl, vbox1, "DB2")
        for i in range(num_sensors):
            self.addLabelledCtrl(pnl, vbox1, "DL"+str(i+1))
        for i in range(num_sensors):
            self.addLabelledCtrl(pnl, vbox1, "DR"+str(i+1))
        if(self.settings.ReadBool('connectedGPSL', False)):
            self.addLabelledCtrl(pnl, vbox1, "DGLX")
            self.addLabelledCtrl(pnl, vbox1, "DGLY")
        if(self.settings.ReadBool('connectedGPSR', False)):
            self.addLabelledCtrl(pnl, vbox1, "DGRX")
            self.addLabelledCtrl(pnl, vbox1, "DGRY")
        if(self.settings.ReadBool('connectedEnvironmentalL', False)):
            self.addLabelledCtrl(pnl, vbox1, "IEL")
        if(self.settings.ReadBool('connectedEnvironmentalR', False)):
            self.addLabelledCtrl(pnl, vbox1, "IER")

        pnl.SetSizer(vbox1)
        pnl.SetupScrolling()

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, label='OK')
        cancelButton = wx.Button(self, label='Cancel')
        hbox.Add(okButton)
        hbox.Add(cancelButton, flag=wx.LEFT, border=5)
        okButton.Bind(wx.EVT_BUTTON, self.OnOK)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)

        vbox0.Add(pnl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        vbox0.Add(hbox, proportion=0, flag=wx.ALIGN_CENTER | wx.ALL,
                  border=10)
        self.SetSizer(vbox0)

    def OnOK(self, e):
        """ Save new settings and close """
        other_settings = list(self.setting_to_control.keys())
        for setting in other_settings:
            ctrl = self.setting_to_control[setting]
            if(setting[0] == 'D'):
                self.settings.WriteFloat(setting, ctrl.GetValue())
            else:
                if(setting[0] == 'I'):
                    self.settings.WriteInt(setting, ctrl.GetValue())
        self.EndModal(wx.ID_OK)
        # self.Destroy()

    def OnCancel(self, e):
        """ Do nothing and close """
        self.EndModal(wx.ID_CANCEL)
        # self.Destroy()

    def getSettings(self):
        """ return settings """
        return self.settings

    def addLabelledCtrl(self, panel, boxSizer, label):
        st = wx.StaticText(panel, label=label)
        boxSizer.Add(st, proportion=0, flag=wx.CENTER | wx.TOP, border=10)
        if(label[0] == 'D'):
            if('G' in label):
                spinCtrl = wx.SpinCtrlDouble(panel, min=-1000, max=1000,
                                             initial=self.settings
                                                         .ReadFloat(label))
            else:
                spinCtrl = wx.SpinCtrlDouble(panel, max=1000,
                                             initial=self.settings
                                                         .ReadFloat(label))
            spinCtrl.SetDigits(2)
        else:
            if(label[0] == 'I'):
                spinCtrl = wx.SpinCtrl(panel, min=1,
                                       max=self.settings
                                               .ReadInt('numSensors', 1),
                                       initial=self.settings.ReadInt(label))
        boxSizer.Add(spinCtrl, proportion=0, flag=wx.ALL | wx.CENTER)
        self.setting_to_control[st.GetLabelText()] = spinCtrl
