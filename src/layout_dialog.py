""" Display dialog window about layout """

# Author: Roberto Buelvas

from wx.lib.scrolledpanel import ScrolledPanel
import wx


class LayoutDialog(wx.Dialog):
    """ Class to define dialog window

    Settings in this dialog are of 2 types:
    Distances: Starting with D e.g. DL1, DGLX
    Indexes: Starting with I e.g. IEL
    In particular, the indexes are used with the environmental sensors
    as they are mounted alongside a multispectral sensor, so it is useful
    to tell the distance from that sensor rather than from the common point
    DL1 measures horizontal distance from the first sensing unit on the left to
        the middle point of the platform. It is used for both the multispectral
        and ultrasonic sensors, as they are supposed to be aligned
    DL2 measures horizontal distance from the second sensing unit on the left
        to the first sensing unit on the left
    DL3, ..., DL{n} follow the same pattern measuring from the previous
        sensing unit
    DR1, ..., DR{n} follow the same pattern but for sensing units on the right
    DB1 measures vertical distance from the row of ultrasonic sensors to the
        toolbar the holds the sensors
    DB2 measures vertical distance from the row of multispectral sensors to the
        row of ultrasonic sensors
    DGLX measures horizontal distance from the location of the GPS antenna on
        the left to the middle point of the platform
    DGLY measures horizontal distance from the location of the GPS antenna on
        the left to the middle point of the platform
    DGRX, DGRY are equivalent to DGLX and DGLY respectively, but on the right
    IEL indicates to which multispectral sensor the environmental sensor of the
        left is linked
    IER indicates the same but for the sensor on the right
    DEL measures horizontal distance from the environmental sensor on the left
        to the multispectral sensor linked to it
    DER is equivalent to DEL but for the sensor on the right
    For reference of what is horizontal or vertical, see the schematic image
    in this dialog
    """

    def __init__(self, parent, settings, *args, **kw):
        """ Create new dialog """
        super(LayoutDialog, self).__init__(parent, *args, **kw)
        self.settings = settings
        self.initUI()
        self.SetSize((650, 500))
        self.Centre()
        self.SetTitle("Layout")

    def initUI(self):
        """ Define dialog elements """
        num_sensors = self.settings.ReadInt("numSensors", 1)

        vbox0 = wx.BoxSizer(wx.VERTICAL)
        pnl = ScrolledPanel(self)
        vbox1 = wx.BoxSizer(wx.VERTICAL)

        st = wx.StaticText(
            pnl,
            label="If the sensor numbers don't match, "
            + "make first the adjustments in "
            + "Settings>Ports",
            size=(600, 60),
        )
        st.SetFont(wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.NORMAL))
        vbox1.Add(st, proportion=0, flag=wx.ALL)

        image = wx.Image("docs/diagram.png", wx.BITMAP_TYPE_ANY).Rescale(450, 300)
        imageBitmap = wx.StaticBitmap(pnl, bitmap=wx.Bitmap(image))
        vbox1.Add(imageBitmap, proportion=1, flag=wx.ALL | wx.CENTER)

        st = wx.StaticText(pnl, label="All distances in cm")
        vbox1.Add(st, proportion=0, flag=wx.ALL)

        self.setting_to_control = {}

        self.addLabelledCtrl(pnl, vbox1, "DB1")
        self.addLabelledCtrl(pnl, vbox1, "DB2")
        for i in range(num_sensors):
            self.addLabelledCtrl(pnl, vbox1, "DL" + str(i + 1))
        for i in range(num_sensors):
            self.addLabelledCtrl(pnl, vbox1, "DR" + str(i + 1))
        if self.settings.ReadBool("connectedgL", False):
            self.addLabelledCtrl(pnl, vbox1, "DGLX")
            self.addLabelledCtrl(pnl, vbox1, "DGLY")
        if self.settings.ReadBool("connectedgR", False):
            self.addLabelledCtrl(pnl, vbox1, "DGRX")
            self.addLabelledCtrl(pnl, vbox1, "DGRY")
        if self.settings.ReadBool("connectedeL", False):
            self.addLabelledCtrl(pnl, vbox1, "IEL")
            self.addLabelledCtrl(pnl, vbox1, "DEL")
        if self.settings.ReadBool("connectedeR", False):
            self.addLabelledCtrl(pnl, vbox1, "IER")
            self.addLabelledCtrl(pnl, vbox1, "DER")

        pnl.SetSizer(vbox1)
        pnl.SetupScrolling()

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, label="OK")
        cancelButton = wx.Button(self, label="Cancel")
        hbox.Add(okButton)
        hbox.Add(cancelButton, flag=wx.LEFT, border=5)
        okButton.Bind(wx.EVT_BUTTON, self.OnOK)
        cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)

        vbox0.Add(pnl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        vbox0.Add(hbox, proportion=0, flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        self.SetSizer(vbox0)

    def OnOK(self, e):
        """ Save new settings and close """
        other_settings = list(self.setting_to_control.keys())
        for setting in other_settings:
            ctrl = self.setting_to_control[setting]
            if setting[0] == "D":
                self.settings.WriteFloat(setting, ctrl.GetValue())
            else:
                if setting[0] == "I":
                    self.settings.WriteInt(setting, ctrl.GetValue())
        self.EndModal(wx.ID_OK)

    def OnCancel(self, e):
        """ Do nothing and close """
        self.EndModal(wx.ID_CANCEL)

    def getSettings(self):
        """ Return settings """
        return self.settings

    def getSettingsList(self):
        """ Return keys of settings modified in this dialog """
        return list(self.setting_to_control.keys())

    def addLabelledCtrl(self, panel, boxSizer, label):
        """ Add a StaticText and SpinControl pair

        Args:
            boxSizer (wx.BoxSizer): BoxSizer that will hold everything created
                                    in this function
            pnl (wx.Panel): Panel to be parent of the elements created, since
                            BoxSizers cannot be used as parent
            label (str): Label of the format DGLX or DL1 to help identify which
                         setting is modified by each control
        Besides creating the mentioned controls, the function adds them to the
        attribute setting_to_control for later use.
        This dictionary allows to remember which setting is modified by each
        control.
        Each control is stacked on top of each other with StaticText in between
        to identify them
        """
        st = wx.StaticText(panel, label=label)
        boxSizer.Add(st, proportion=0, flag=wx.CENTER | wx.TOP, border=10)
        if label[0] == "D":
            spinCtrl = wx.SpinCtrlDouble(
                panel, min=-3000, max=3000, initial=self.settings.ReadFloat(label)
            )
            spinCtrl.SetDigits(2)
        else:
            if label[0] == "I":
                spinCtrl = wx.SpinCtrl(
                    panel,
                    min=1,
                    max=self.settings.ReadInt("numSensors", 1),
                    initial=self.settings.ReadInt(label),
                )
        boxSizer.Add(spinCtrl, proportion=0, flag=wx.ALL | wx.CENTER)
        self.setting_to_control[st.GetLabelText()] = spinCtrl
