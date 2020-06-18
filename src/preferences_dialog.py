""" Display dialog window about user preferences """

# Author: Roberto Buelvas

import glob
import sys

import serial
import wx


class PreferencesDialog(wx.Dialog):
    """ Class to define dialog window """

    def __init__(self, settings, *args, **kw):
        """ Create new dialog """
        super(PreferencesDialog, self).__init__(*args, **kw)
        self.settings = settings
        self.InitUI()
        self.SetSize((650, 300))
        self.SetTitle('Preferences')

    def InitUI(self):
        """ Define dialog elements """
        ports = [''] + self.GetSerialPorts()

        pnl = wx.Panel(self)
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        vbox2 = wx.BoxSizer(wx.VERTICAL)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        st1 = wx.StaticText(pnl, label='Multispectral', size=(120, 30))
        hbox1.Add(st1, proportion=0, flag=wx.ALL)
        self.chb1 = wx.CheckBox(pnl, label='Connected')
        hbox1.Add(self.chb1, proportion=1, flag=wx.ALL | wx.EXPAND)
        self.chb1.Bind(wx.EVT_CHECKBOX, self.OnChecked1)
        self.cb1 = wx.ComboBox(pnl, choices=ports)
        hbox1.Add(self.cb1, proportion=1, flag=wx.ALL | wx.EXPAND)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        st2 = wx.StaticText(pnl, label='Ultrasonic', size=(120, 30))
        hbox2.Add(st2, proportion=0, flag=wx.ALL)
        self.chb2 = wx.CheckBox(pnl, label='Connected')
        hbox2.Add(self.chb2, proportion=1, flag=wx.ALL | wx.EXPAND)
        self.chb2.Bind(wx.EVT_CHECKBOX, self.OnChecked2)
        self.cb2 = wx.ComboBox(pnl, choices=ports)
        hbox2.Add(self.cb2, proportion=1, flag=wx.ALL | wx.EXPAND)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        st3 = wx.StaticText(pnl, label='GPS', size=(120, 30))
        hbox3.Add(st3, proportion=0, flag=wx.ALL)
        self.chb3 = wx.CheckBox(pnl, label='Connected')
        hbox3.Add(self.chb3, proportion=1, flag=wx.ALL | wx.EXPAND)
        self.chb3.Bind(wx.EVT_CHECKBOX, self.OnChecked3)
        self.cb3 = wx.ComboBox(pnl, choices=ports)
        hbox3.Add(self.cb3, proportion=1, flag=wx.ALL | wx.EXPAND)

        if(self.settings.Exists('multispectralConnected')):
            self.chb1.SetValue(self.settings.ReadBool('multispectralConnected'))
            if(self.chb1.GetValue()):
                self.cb1.Enable(True)
                self.cb1.SetValue(self.settings.Read('multispectralPort'))
            else:
                self.cb1.Enable(False)
            self.chb2.SetValue(self.settings.ReadBool('ultrasonicConnected'))
            if(self.chb2.GetValue()):
                self.cb2.Enable(True)
                self.cb2.SetValue(self.settings.Read('ultrasonicPort'))
            else:
                self.cb2.Enable(False)
            self.chb3.SetValue(self.settings.ReadBool('GPSConnected'))
            if(self.chb3.GetValue()):
                self.cb3.Enable(True)
                self.cb3.SetValue(self.settings.Read('GPSPort'))
            else:
                self.cb3.Enable(False)
        else:
            self.chb1.SetValue(False)
            self.cb1.Enable(False)
            self.chb2.SetValue(False)
            self.cb2.Enable(False)
            self.chb3.SetValue(False)
            self.cb3.Enable(False)

        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, label='OK')
        cancelButton = wx.Button(self, label='Cancel')
        hbox4.Add(okButton)
        hbox4.Add(cancelButton, flag=wx.LEFT, border=5)
        okButton.Bind(wx.EVT_BUTTON, self.OnOK)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)

        vbox2.Add(hbox1, proportion=1, border=10,
                  flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM | wx.EXPAND)
        vbox2.Add(hbox2, proportion=1, border=10,
                  flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM | wx.EXPAND)
        vbox2.Add(hbox3, proportion=1, border=10,
                  flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM | wx.EXPAND)
        pnl.SetSizer(vbox2)

        vbox1.Add(pnl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        vbox1.Add(hbox4, proportion=0, flag=wx.ALIGN_CENTER | wx.ALL,
                  border=10)
        self.SetSizer(vbox1)

    def OnOK(self, e):
        """ Save new settings and close """
        self.settings.WriteBool('multispectralConnected', self.chb1.GetValue())
        self.settings.Write('multispectralPort', self.cb1.GetValue())
        self.settings.WriteBool('ultrasonicConnected', self.chb2.GetValue())
        self.settings.Write('ultrasonicPort', self.cb2.GetValue())
        self.settings.WriteBool('GPSConnected', self.chb3.GetValue())
        self.settings.Write('GPSPort', self.cb3.GetValue())
        self.EndModal(wx.ID_OK)
        # self.Destroy()

    def OnCancel(self, e):
        """ Do nothing and close """
        self.EndModal(wx.ID_CANCEL)
        # self.Destroy()

    def OnChecked1(self, e):
        """ Enable other controls when checkbox is selected """
        chb = e.GetEventObject()
        if(chb.GetValue()):
            self.cb1.Enable(True)
        else:
            self.cb1.Enable(False)

    def OnChecked2(self, e):
        """ Enable other controls when checkbox is selected """
        chb = e.GetEventObject()
        if(chb.GetValue()):
            self.cb2.Enable(True)
        else:
            self.cb2.Enable(False)

    def OnChecked3(self, e):
        """ Enable other controls when checkbox is selected """
        chb = e.GetEventObject()
        if(chb.GetValue()):
            self.cb3.Enable(True)
        else:
            self.cb3.Enable(False)

    def GetSettings(self):
        """ return settings """
        return self.settings

    # https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    def GetSerialPorts(self, maxNum=20):
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        plat = sys.platform
        if plat.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(maxNum)]
        elif plat.startswith('linux') or plat.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif plat.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result
