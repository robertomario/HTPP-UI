""" Display dialog window about ports """

# Author: Roberto Buelvas

import glob
import sys

from wx.lib.scrolledpanel import ScrolledPanel
import serial
import cv2
import wx

# Dict to hold the sensor names and scaling behavior
# In this context, the scaling of the sensor means that the system could
# incorporate different numbers of that sensor without any limit other than
# how many there are available. On the other hand, it would be unexpected to
# have more than 2 GPS or Environmental sensors.
# Cameras are not listed here because they are handled by a differently
devices = {
    "m": ("Multispectral", True),
    "u": ("Ultrasonic", True),
    "g": ("GPS", False),
    "e": ("Environmental", False),
}


class PortsDialog(wx.Dialog):
    """ Class to define dialog window

    Settings in this dialog are of 3 types:
    numSensors: Unique setting defining how many of the scalable sensors
                there are on each side of the system. Many controls depend on
                its value to know how many times to repeat their operations
    connected: Boolean indicating if sensor is connected. If False, the
                ComboBox to select the port will be disabled. There is one
                for each sensor. They have a suffix of the style mL1 or gR.
                See MainWindow.getLabel()
    port: String indicating where the sensor is connected. There is one for
            each connected sensor. In Windows, they are of the format 'COM3'.
            They have a suffix of the style mL1 or gR.
            See MainWindow.getLabel()
    """

    def __init__(self, settings, *args, **kw):
        """ Create new dialog """
        super(PortsDialog, self).__init__(*args, **kw)
        self.settings = settings
        self.initUI(self.settings.ReadInt("numSensors", 1))
        self.SetSize((650, 500))
        self.Centre()
        self.SetTitle("Ports")

    def initUI(self, num_sensors):
        """ Define dialog elements """
        ports = [""] + self.getSerialPorts()
        cameras = [""] + self.getCameraPorts()

        vbox0 = wx.BoxSizer(wx.VERTICAL)
        pnl = ScrolledPanel(self)
        vbox1 = wx.BoxSizer(wx.VERTICAL)

        hbox0 = wx.BoxSizer(wx.HORIZONTAL)
        st0 = wx.StaticText(
            pnl, label="Number of sensor units per side", size=(300, 30)
        )
        hbox0.Add(st0, proportion=0, flag=wx.ALL)
        self.spinCtrl = wx.SpinCtrl(pnl, min=1, initial=num_sensors)
        self.spinCtrl.Bind(wx.EVT_TEXT, self.OnNumberChange)
        hbox0.Add(self.spinCtrl, proportion=0, flag=wx.ALL)

        vbox1.Add(hbox0, proportion=1, border=10, flag=wx.TOP | wx.BOTTOM | wx.EXPAND)

        device_tuples = list(devices.values())
        self.checkbox_to_combobox = {}
        self.setting_to_checkbox = {}
        for device_tuple in device_tuples:
            name = device_tuple[0]
            scaling = device_tuple[1]
            vbox_aux = wx.BoxSizer(wx.VERTICAL)
            st_aux = wx.StaticText(pnl, label=name, size=(120, 30))
            vbox_aux.Add(st_aux, proportion=0, flag=wx.ALL)
            if scaling:
                for i in range(num_sensors):
                    self.addCheckComboBoxes(
                        vbox_aux, pnl, ports, name, "L", number=i + 1
                    )
                for i in range(num_sensors):
                    self.addCheckComboBoxes(
                        vbox_aux, pnl, ports, name, "R", number=i + 1
                    )
            else:
                self.addCheckComboBoxes(vbox_aux, pnl, ports, name, "L")
                self.addCheckComboBoxes(vbox_aux, pnl, ports, name, "R")
            vbox1.Add(
                vbox_aux, proportion=1, border=10, flag=wx.TOP | wx.BOTTOM | wx.EXPAND
            )
        vbox_aux = wx.BoxSizer(wx.VERTICAL)
        st_aux = wx.StaticText(pnl, label="Camera", size=(120, 30))
        vbox_aux.Add(st_aux, proportion=0, flag=wx.ALL)
        vbox1.Add(
            vbox_aux, proportion=1, border=10, flag=wx.TOP | wx.BOTTOM | wx.EXPAND
        )
        self.addCheckComboBoxes(vbox_aux, pnl, cameras, "Camera", "L")
        self.addCheckComboBoxes(vbox_aux, pnl, cameras, "Camera", "R")
        pnl.SetSizer(vbox1)
        pnl.SetupScrolling()

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, label="OK")
        cancelButton = wx.Button(self, label="Cancel")
        hbox1.Add(okButton)
        hbox1.Add(cancelButton, flag=wx.LEFT, border=5)
        okButton.Bind(wx.EVT_BUTTON, self.OnOK)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)

        vbox0.Add(pnl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        vbox0.Add(hbox1, proportion=0, flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        self.SetSizer(vbox0)

    def OnOK(self, e):
        """ Save new settings and close """
        self.settings.WriteInt("numSensors", self.spinCtrl.GetValue())
        other_settings = list(self.setting_to_checkbox.keys())
        for setting in other_settings:
            chb = self.setting_to_checkbox[setting]
            self.settings.WriteBool("connected" + setting, chb.GetValue())
            cb = self.checkbox_to_combobox[chb]
            self.settings.Write("port" + setting, cb.GetValue())
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
        """ Change number of sensor units

        When the number of sensors connected changes, the elements of the
        dialog are destroyed and initUI() is called again to ensure there are
        as many controls as sensors
        """
        intc = e.GetEventObject()
        num_sensors = intc.GetValue()
        if num_sensors is not None:
            self.DestroyChildren()
            self.initUI(num_sensors)
            self.Layout()

    def getSettings(self):
        """ Return settings """
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
        if plat.startswith("win"):
            ports = ["COM%s" % (i + 1) for i in range(minNum, maxNum)]
        elif plat.startswith("linux") or plat.startswith("cygwin"):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob("/dev/tty[A-Za-z]*")
        elif plat.startswith("darwin"):
            ports = glob.glob("/dev/tty.*")
        else:
            raise EnvironmentError("Unsupported platform")

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    def getCameraPorts(self, initial_number=0, final_number=10):
        """ List camera ports names
        
        OpenCV doesn't receive a COM3 type of port, but a number
        """
        available_ports = []
        for i in range(initial_number, final_number):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                ret, frame = cap.read()
            except Exception as e:
                pass
            else:
                cap.release()
                if ret:
                    available_ports.append(str(i))
        return available_ports

    def addCheckComboBoxes(self, boxSizer, pnl, comboOptions, name, side, number=None):
        """ Add a combobox and a checkbox that controls if it is enabled

        Args:
            boxSizer (wx.BoxSizer): BoxSizer that will hold everything created
                                    in this function
            pnl (wx.Panel): Panel to be parent of the elements created, since
                            BoxSizers cannot be used as parent
            comboOptions (list): List of detected ports
            name (str): Name of the sensors related to the controls. Used to
                        create labels of the style mL1 or gR
            side (str): 'L' or 'R'. Used to create labels of the style mL1 or
                        gR
            number (int): If None, means the sensor does not scale. Used to
                          create labels of the style mL1 or gR
        Besides creating the mentioned controls, the function adds them to the
        attributes checkbox_to_combobox and setting_to_checkbox for later use.
        These dictionaries allow to remember which checkbox control which
        combobox
        Each pair of controls is inside a horizontal BoxSizer for alignment
        """
        hbox_aux = wx.BoxSizer(wx.HORIZONTAL)
        if number is None:
            suffix = name[0].lower() + side
        else:
            suffix = name[0].lower() + side + str(number)
        chb_aux = wx.CheckBox(pnl, label=suffix)
        hbox_aux.Add(chb_aux, proportion=1, flag=wx.ALL | wx.EXPAND)
        chb_aux.Bind(wx.EVT_CHECKBOX, self.OnChecked)
        cb_aux = wx.ComboBox(pnl, choices=comboOptions)
        self.checkbox_to_combobox[chb_aux] = cb_aux
        self.setting_to_checkbox[suffix] = chb_aux
        chb_aux.SetValue(self.settings.ReadBool("connected" + suffix, False))
        if chb_aux.GetValue():
            cb_aux.Enable(True)
            cb_aux.SetValue(self.settings.Read("port" + suffix, ""))
        else:
            cb_aux.SetValue("")
            cb_aux.Enable(False)
        hbox_aux.Add(cb_aux, proportion=1, flag=wx.ALL | wx.EXPAND)
        boxSizer.Add(hbox_aux, proportion=1, flag=wx.EXPAND)
