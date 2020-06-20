""" Display dialog window about ports """

# Author: Roberto Buelvas

import glob
import sys

from wx.lib.scrolledpanel import ScrolledPanel
import wx.lib.intctrl as intctrl
import serial
import wx


devices = {
    0: ('Multispectral', True),
    1: ('Ultrasonic', True),
    2: ('GPS', False),
    3: ('Environmental', False)
}


class PortsDialog(wx.Dialog):
    """ Class to define dialog window """

    def __init__(self, settings, *args, **kw):
        """ Create new dialog """
        super(PortsDialog, self).__init__(*args, **kw)
        self.settings = settings
        self.initUI(self.settings.ReadInt('numSensors', 1))
        self.SetSize((650, 500))
        self.Centre()
        self.SetTitle('Ports')

    def initUI(self, num_sensors):
        """ Define dialog elements """
        # self.Layout()
        # self.ClearBackground()
        # self.Refresh()

        ports = [''] + self.getSerialPorts()

        vbox0 = wx.BoxSizer(wx.VERTICAL)
        pnl = ScrolledPanel(self)
        vbox1 = wx.BoxSizer(wx.VERTICAL)

        hbox0 = wx.BoxSizer(wx.HORIZONTAL)
        st0 = wx.StaticText(pnl, label='Number of sensor units per side',
                            size=(300, 30))
        hbox0.Add(st0, proportion=0, flag=wx.ALL)
        self.intCtrl = intctrl.IntCtrl(pnl, value=num_sensors, min=1,
                                       limited=True, allow_none=True)
        self.intCtrl.Bind(wx.EVT_TEXT, self.OnNumberChange)
        hbox0.Add(self.intCtrl, proportion=0, flag=wx.ALL)

        vbox1.Add(hbox0, proportion=1, border=10, flag=wx.TOP | wx.BOTTOM
                  | wx.EXPAND)

        device_tuples = list(devices.values())
        self.checkbox_to_combobox = {}
        self.setting_to_checkbox = {}
        for device_tuple in device_tuples:
            name = device_tuple[0]
            scaling = device_tuple[1]
            vbox_aux = wx.BoxSizer(wx.VERTICAL)
            st_aux = wx.StaticText(pnl, label=name, size=(120, 30))
            vbox_aux.Add(st_aux, proportion=0, flag=wx.ALL)
            if(scaling):
                for i in range(num_sensors):
                    hbox_aux = wx.BoxSizer(wx.HORIZONTAL)
                    chb_aux = wx.CheckBox(pnl, label='L'+str(i+1))
                    hbox_aux.Add(chb_aux, proportion=1, flag=wx.ALL
                                 | wx.EXPAND)
                    chb_aux.Bind(wx.EVT_CHECKBOX, self.OnChecked)
                    cb_aux = wx.ComboBox(pnl, choices=ports)
                    self.checkbox_to_combobox[chb_aux] = cb_aux
                    suffix = name+'L'+str(i+1)
                    self.setting_to_checkbox[suffix] = chb_aux
                    chb_aux.SetValue(self.settings.ReadBool('connected'+suffix,
                                                            False))
                    if(chb_aux.GetValue()):
                        cb_aux.Enable(True)
                        cb_aux.SetValue(self.settings.Read('port'+suffix, ''))
                    else:
                        cb_aux.Enable(False)
                    hbox_aux.Add(cb_aux, proportion=1, flag=wx.ALL | wx.EXPAND)
                    vbox_aux.Add(hbox_aux, proportion=1, flag=wx.EXPAND)
                for i in range(num_sensors):
                    hbox_aux = wx.BoxSizer(wx.HORIZONTAL)
                    chb_aux = wx.CheckBox(pnl, label='R'+str(i+1))
                    hbox_aux.Add(chb_aux, proportion=1, flag=wx.ALL
                                 | wx.EXPAND)
                    chb_aux.Bind(wx.EVT_CHECKBOX, self.OnChecked)
                    cb_aux = wx.ComboBox(pnl, choices=ports)
                    self.checkbox_to_combobox[chb_aux] = cb_aux
                    suffix = name+'R'+str(i+1)
                    self.setting_to_checkbox[suffix] = chb_aux
                    chb_aux.SetValue(self.settings.ReadBool('connected'+suffix,
                                     False))
                    if(chb_aux.GetValue()):
                        cb_aux.Enable(True)
                        cb_aux.SetValue(self.settings.Read('port'+suffix, ''))
                    else:
                        cb_aux.Enable(False)
                    hbox_aux.Add(cb_aux, proportion=1, flag=wx.ALL | wx.EXPAND)
                    vbox_aux.Add(hbox_aux, proportion=1, flag=wx.EXPAND)
            else:
                hbox_aux = wx.BoxSizer(wx.HORIZONTAL)
                chb_aux = wx.CheckBox(pnl, label='L')
                hbox_aux.Add(chb_aux, proportion=1, flag=wx.ALL | wx.EXPAND)
                chb_aux.Bind(wx.EVT_CHECKBOX, self.OnChecked)
                cb_aux = wx.ComboBox(pnl, choices=ports)
                self.checkbox_to_combobox[chb_aux] = cb_aux
                self.setting_to_checkbox[name+'L'] = chb_aux
                chb_aux.SetValue(self.settings.ReadBool('connected'+name+'L',
                                 False))
                if(chb_aux.GetValue()):
                    cb_aux.Enable(True)
                    cb_aux.SetValue(self.settings.Read('port'+name+'L', ''))
                else:
                    cb_aux.Enable(False)
                hbox_aux.Add(cb_aux, proportion=1, flag=wx.ALL | wx.EXPAND)
                vbox_aux.Add(hbox_aux, proportion=1, flag=wx.EXPAND)

                hbox_aux = wx.BoxSizer(wx.HORIZONTAL)
                chb_aux = wx.CheckBox(pnl, label='R')
                hbox_aux.Add(chb_aux, proportion=1, flag=wx.ALL | wx.EXPAND)
                chb_aux.Bind(wx.EVT_CHECKBOX, self.OnChecked)
                cb_aux = wx.ComboBox(pnl, choices=ports)
                self.checkbox_to_combobox[chb_aux] = cb_aux
                self.setting_to_checkbox[name+'R'] = chb_aux
                chb_aux.SetValue(self.settings.ReadBool('connected'+name+'R',
                                 False))
                if(chb_aux.GetValue()):
                    cb_aux.Enable(True)
                    cb_aux.SetValue(self.settings.Read('port'+name+'R', ''))
                else:
                    cb_aux.Enable(False)
                hbox_aux.Add(cb_aux, proportion=1, flag=wx.ALL | wx.EXPAND)
                vbox_aux.Add(hbox_aux, proportion=1, flag=wx.EXPAND)
            vbox1.Add(vbox_aux, proportion=1, border=10, flag=wx.TOP
                      | wx.BOTTOM | wx.EXPAND)
        pnl.SetSizer(vbox1)
        pnl.SetupScrolling()

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, label='OK')
        cancelButton = wx.Button(self, label='Cancel')
        hbox1.Add(okButton)
        hbox1.Add(cancelButton, flag=wx.LEFT, border=5)
        okButton.Bind(wx.EVT_BUTTON, self.OnOK)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)

        vbox0.Add(pnl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        vbox0.Add(hbox1, proportion=0, flag=wx.ALIGN_CENTER | wx.ALL,
                  border=10)
        self.SetSizer(vbox0)

    def OnOK(self, e):
        """ Save new settings and close """
        self.settings.WriteInt('numSensors', self.intCtrl.GetValue())
        other_settings = list(self.setting_to_checkbox.keys())
        for setting in other_settings:
            chb = self.setting_to_checkbox[setting]
            self.settings.WriteBool('connected'+setting, chb.GetValue())
            cb = self.checkbox_to_combobox[chb]
            self.settings.Write('port'+setting, cb.GetValue())
        self.EndModal(wx.ID_OK)
        # self.Destroy()

    def OnCancel(self, e):
        """ Do nothing and close """
        self.EndModal(wx.ID_CANCEL)
        # self.Destroy()

    def OnChecked(self, e):
        """ Enable other controls when checkbox is selected """
        chb = e.GetEventObject()
        is_connected = chb.GetValue()
        cb = self.checkbox_to_combobox[chb]
        cb.Enable(is_connected)

    def OnNumberChange(self, e):
        """ Change number of sensor units """
        intc = e.GetEventObject()
        num_sensors = intc.GetValue()
        if(num_sensors is not None):
            self.DestroyChildren()
            self.initUI(num_sensors)
            self.Layout()

    def getSettings(self):
        """ return settings """
        return self.settings

    # https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    def getSerialPorts(self, minNum=0, maxNum=25):
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        plat = sys.platform
        if plat.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(minNum, maxNum)]
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
