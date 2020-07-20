""" Display main window """

# Author: Roberto Buelvas

from datetime import datetime
import random
import time
import math
import os

import numpy as np
import wx

from .sensors import openPort, getSensorReading, setupGPSProjection, processGPS
from .ports_dialog import PortsDialog, devices
from .plot_notebook import Plot, PlotNotebook
from .repeated_timer import RepeatedTimer
from .layout_dialog import LayoutDialog
from .camera_handler import CameraFrame

# Dict to hold which sensor is the source for each measured variable
# m >> Multispectral
# u >> Ultrasonic
# g >> GPS
# e >> Environmental
variables = {
    "m": [
        "CI",
        "NDRE",
        "NDVI",
        "proxy Distance",
        "proxy LAI",
        "proxy CCC",
        "Red-Edge",
        "NIR",
        "Red",
    ],
    "u": ["Distance"],
    "g": ["Longitude", "Latitude", "X", "Y", "Heading", "Velocity", "Time"],
    "e": [
        "Canopy Temperature",
        "Air Temperature",
        "Humidity",
        "Reflected PAR",
        "Incident PAR",
        "Pressure",
    ],
}


class MainWindow(wx.Frame):
    """ Class to define main window

    This class both creates the main window of the UI and controls the
    operations that are done within it.

    Attr:
        cfg (wx.ConfigBase): Settings are saved in here, which creates a file
            in a hidden folder to store values. These values are kept if the
            program stops running and even if the computers turns off. It uses
            a key-value system similar to dictionaries
        btn_test (wx.ToggleButton): Button to toggle in and out of 'Test Mode'
        logText (wx.TextCtrl): Control where information is logged
        mapAxes (matplotlib.Axes): Axes to create map plot
        mapPanel (Plot): Panel containing the Figure where the map is drawn
        rt (RepeatedTimer): Object to create a new thread on timer periodically
        axes (dict): Dict to hold the Axes for each measured variables. Keys
            are of the format 'mL1/NDVI' or 'gR/Latitude'. Used to create the
            plots
        label_to_device (dict): Dict to hold the serial devices for each label.
            Keys are labels of the format 'mL1' or 'gR'. Used to get sensor
            readings
        previous_measurements (dict): Dict to hold the measurements taken in
            the immediately previous set. Keys are of the format 'mL1/NDVI' or
            'gR/Latitude'. Used to create the plots and process GPS data
        labels (list): List of all possible labels of the style mL1 or gR given
            the number of scaling sensors
        lastRecord (list): List showing positions in the text log where each
            set of measurements ends. Used to erase the last set of values from
            the log text
        origin_longitude (float): Stores value of the first GPS reading to use
            for conversion to planar coordinates
        origin_latitude (float): Stores value of the first GPS reading to use
            for conversion to planar coordinates
        F_lon (float): Stores value of the first GPS reading to use for
            conversion to planar coordinates
        F_lat (float): Stores value of the first GPS reading to use for
            conversion to planar coordinates
        origin_time (float): Stores value of the first GPS reading to use for
            conversion to calculation of velocity
        numReadings (int): Stores how many sets of measurements have been taken
            in the current survey. Set back to 0 when log text is cleared or
            exported to file

    """

    def __init__(self, *args, **kwargs):
        """ Create new window """
        super(MainWindow, self).__init__(*args, **kwargs)
        self.cfg = wx.Config("HTPPconfig")
        self.cfg.WriteBool("notEmpty", True)
        self.camera_frame = CameraFrame(self, self.updateCameraPorts())
        self.camera_frame.Bind(wx.EVT_CLOSE, self.OnCameraClose)
        self.labels = []
        self.axes = {}
        self.label_to_device = {}
        self.clearVariables()
        self.initUI()

    def initUI(self):
        """ Define window elements """
        # Toolbar
        menubar = wx.MenuBar()

        fileMenu = wx.Menu()
        newmi = wx.MenuItem(fileMenu, wx.ID_NEW, "&New")
        fileMenu.Append(newmi)
        self.Bind(wx.EVT_MENU, self.OnNew, newmi)
        savemi = wx.MenuItem(fileMenu, wx.ID_SAVE, "&Save")
        fileMenu.Append(savemi)
        self.Bind(wx.EVT_MENU, self.OnSave, savemi)
        fileMenu.AppendSeparator()
        qmi = wx.MenuItem(fileMenu, wx.ID_EXIT, "&Quit")
        fileMenu.Append(qmi)
        self.Bind(wx.EVT_MENU, self.OnQuit, qmi)
        menubar.Append(fileMenu, "&File")

        settingsMenu = wx.Menu()
        portsmi = wx.MenuItem(settingsMenu, wx.ID_PREFERENCES, "&Ports")
        settingsMenu.Append(portsmi)
        self.Bind(wx.EVT_MENU, self.OnPorts, portsmi)
        layoutmi = wx.MenuItem(settingsMenu, wx.ID_ANY, "&Layout")
        settingsMenu.Append(layoutmi)
        self.Bind(wx.EVT_MENU, self.OnLayout, layoutmi)
        clearmi = wx.MenuItem(settingsMenu, wx.ID_ANY, "&Clear")
        settingsMenu.Append(clearmi)
        self.Bind(wx.EVT_MENU, self.OnClear, clearmi)
        menubar.Append(settingsMenu, "&Settings")

        viewMenu = wx.Menu()
        self.camerami = viewMenu.AppendCheckItem(wx.ID_ANY, "&Camera")
        self.Bind(wx.EVT_MENU, self.OnCamera, self.camerami)
        menubar.Append(viewMenu, "&View")

        helpMenu = wx.Menu()
        aboutmi = wx.MenuItem(helpMenu, wx.ID_ABOUT, "&About")
        helpMenu.Append(aboutmi)
        self.Bind(wx.EVT_MENU, self.OnAbout, aboutmi)
        menubar.Append(helpMenu, "&Help")

        self.SetMenuBar(menubar)

        # Window
        backgroundPanel = wx.Panel(self)
        backgroundPanel.SetBackgroundColour("#ededed")

        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)

        outerBox = wx.BoxSizer(wx.HORIZONTAL)

        leftBox = wx.BoxSizer(wx.VERTICAL)
        st1 = wx.StaticText(backgroundPanel, label="Map:")
        self.mapPanel = Plot(backgroundPanel)
        self.mapAxes = self.mapPanel.figure.gca()
        st2 = wx.StaticText(backgroundPanel, label="Log:")
        self.logText = wx.TextCtrl(
            backgroundPanel, style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.logSettings()
        leftBox.Add(st1, proportion=0, flag=wx.ALL)
        leftBox.Add(self.mapPanel, wx.ID_ANY, wx.EXPAND | wx.ALL, 20)
        leftBox.Add(st2, proportion=0, flag=wx.ALL)
        leftBox.Add(self.logText, wx.ID_ANY, wx.EXPAND | wx.ALL, 20)

        middleBox = wx.BoxSizer(wx.VERTICAL)
        st3 = wx.StaticText(backgroundPanel, label="Plot:")
        self.plotter = PlotNotebook(backgroundPanel)
        num_sensors = self.cfg.ReadInt("numSensors", 1)
        for device_name in list(variables.keys()):
            variable_names = variables[device_name]
            scaling = devices[device_name][1]
            for name in variable_names:
                self.axes[name] = self.plotter.add(
                    name, device_name, scaling, num_sensors
                )

        middleBox.Add(st3, proportion=0, flag=wx.ALL)
        middleBox.Add(self.plotter, proportion=7, flag=wx.EXPAND | wx.ALL, border=20)

        rightBox = wx.BoxSizer(wx.VERTICAL)
        btn_connect = wx.ToggleButton(backgroundPanel, label="Connect")
        btn_start = wx.ToggleButton(backgroundPanel, label="Start")
        self.btn_test = wx.ToggleButton(backgroundPanel, label="Test Mode")
        btn_measure = wx.Button(backgroundPanel, label="Measure")
        btn_erase = wx.Button(backgroundPanel, label="Erase")
        btn_connect.Bind(wx.EVT_TOGGLEBUTTON, self.OnConnect)
        btn_start.Bind(wx.EVT_TOGGLEBUTTON, self.OnStart)
        btn_measure.Bind(wx.EVT_BUTTON, self.OnMeasure)
        btn_erase.Bind(wx.EVT_BUTTON, self.OnErase)
        rightBox.Add(btn_connect, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(btn_start, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(self.btn_test, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(btn_measure, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(btn_erase, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)

        outerBox.Add(leftBox, proportion=2, flag=wx.EXPAND | wx.ALL, border=20)
        outerBox.Add(middleBox, proportion=3, flag=wx.EXPAND | wx.ALL, border=20)
        outerBox.Add(rightBox, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        backgroundPanel.SetSizer(outerBox)

        self.Maximize()
        self.SetTitle("High-Throughput Plant Phenotyping Platform")
        self.Centre()

    def OnNew(self, e):
        """ Toolbar option to reset log without saving """
        confirmDiag = wx.MessageDialog(
            None,
            ("Are you sure you want to clear " + "the log?"),
            "Question",
            (wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION),
        )
        dialogFlag = confirmDiag.ShowModal()
        if dialogFlag == wx.ID_YES:
            self.logText.SetValue("")
            self.logSettings()
            self.plotter.clear()
            num_sensors = self.cfg.ReadInt("numSensors", 1)
            self.plotter.redoLegend(variables, devices, num_sensors)
            self.plotter.refresh()
            self.mapPanel.clear()
            self.mapPanel.refresh()
            self.clearVariables()

    def OnSave(self, e):
        """ Toolbar option to save and reset log """
        rootName = (
            "data/HTPPLogFile"
            + datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d")
            + "X"
        )
        i = 1
        while os.path.isfile(rootName + str(i) + ".txt"):
            i += 1
        finalFilename = rootName + str(i) + ".txt"
        self.logText.SaveFile(finalFilename)
        self.logText.SetValue("")
        self.logSettings()
        self.plotter.clear()
        num_sensors = self.cfg.ReadInt("numSensors", 1)
        self.plotter.redoLegend(variables, devices, num_sensors)
        self.plotter.refresh()
        self.mapPanel.clear()
        self.mapPanel.refresh()
        self.clearVariables()

    def OnQuit(self, e):
        """ Toolbar option to exit application """
        self.Close()

    def OnCamera(self, e):
        self.camera_frame.Show(self.camerami.IsChecked())

    def OnCameraClose(self, e):
        self.camerami.Check(False)
        self.camera_frame.close()
        self.camera_frame = CameraFrame(self, self.updateCameraPorts())
        self.camera_frame.Hide()

    def OnAbout(self, e):
        """ Toolbar option to show About dialog """
        wx.MessageBox(
            (
                "High-Throughput Plant Phenotyping Platform \n"
                "Made by Roberto Buelvas\n"
                "McGill University, 2020\n"
                "Version 0.1\n"
            ),
            "About",
            wx.OK | wx.ICON_INFORMATION,
        )

    def OnPorts(self, e):
        """ Toolbar option to open ports dialog window """
        pDialog = PortsDialog(self.cfg, self)
        dialogFlag = pDialog.ShowModal()
        if dialogFlag == wx.ID_OK:
            results = pDialog.getSettings()
            num_sensors = results.ReadInt("numSensors", 1)
            self.cfg.WriteInt("numSensors", num_sensors)
            for label in self.labels:
                self.cfg.WriteBool(
                    "connected" + label, results.ReadBool("connected" + label)
                )
                self.cfg.Write("port" + label, results.Read("port" + label))
            self.logSettings()
            self.labels = self.getLabels()
            self.plotter.redoLegend(variables, devices, num_sensors)
            self.camera_frame.close()
            self.camera_frame = CameraFrame(self, self.updateCameraPorts())
            self.camera_frame.Show(self.camerami.IsChecked())
        pDialog.Destroy()

    def OnLayout(self, e):
        """ Toolbar option to open ports dialog window """
        lDialog = LayoutDialog(self.cfg, self)
        dialogFlag = lDialog.ShowModal()
        if dialogFlag == wx.ID_OK:
            results = lDialog.getSettings()
            settings_list = lDialog.getSettingsList()
            for setting_key in settings_list:
                if setting_key[0] == "D":
                    self.cfg.WriteFloat(setting_key, results.ReadFloat(setting_key))
                if setting_key[0] == "I":
                    self.cfg.WriteInt(setting_key, results.ReadInt(setting_key))
            self.logSettings()
        lDialog.Destroy()

    def OnClear(self, e):
        """ Toolbar option to clear all settings

        This removes every entry from the attribute cfg, except for a dummy
        entry 'notEmpty' to prevent the ConfigBase of being entirerly empty,
        which causes it to crash.
        Not to be confounded with the method clearVariables(), which resets
        some other attributes whose values are only relevant for the current
        survey
        """
        confirmDiag = wx.MessageDialog(
            None,
            ("Are you sure you want to clear " + "the settings?"),
            "Question",
            (wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION),
        )
        dialogFlag = confirmDiag.ShowModal()
        if dialogFlag == wx.ID_YES:
            all_config_keys = []
            more, value, index = self.cfg.GetFirstEntry()
            while more:
                all_config_keys.append(value)
                more, value, index = self.cfg.GetNextEntry(index)
            all_config_keys.remove("notEmpty")
            for key in all_config_keys:
                self.cfg.DeleteEntry(key)

    def OnConnect(self, e):
        """ Toggle button action to connect/disconnect from sensors

        Besides opening the ports to the serial devices, this method also
        populates the attribute label_to_device for later use
        It also does a first GPS reading to set the constants of processing
        """
        btn = e.GetEventObject()
        is_pressed = btn.GetValue()
        is_test_mode = self.btn_test.GetValue()
        if is_test_mode:
            if is_pressed:
                btn.SetLabelText("Disconnect")
                for label in self.labels:
                    if (label[0] == "g") and self.cfg.ReadBool(
                        "connected" + label, False
                    ):
                        reading = [-73.939830, 45.423804]
                        self.GPS_constants = setupGPSProjection(reading)
            else:
                btn.SetLabelText("Connect")
        else:
            if is_pressed:
                btn.SetLabelText("Disconnect")
                self.label_to_device = {}
                for label in self.labels:
                    if self.cfg.ReadBool("connected" + label, False):
                        port = self.cfg.Read("port" + label, "")
                        if port == "":
                            wx.MessageBox(
                                (
                                    "The port for "
                                    + label
                                    + "has not been properly selected"
                                ),
                                "Empty port",
                                wx.OK | wx.ICON_WARNING,
                            )
                            break
                        else:
                            device = openPort(port, label)
                            self.label_to_device[label] = device
                            if label[0] == "g":
                                reading = np.array([np.nan, np.nan])
                                while any(np.isnan(reading)):
                                    reading = getSensorReading(device, label)
                                self.GPS_constants = setupGPSProjection(reading)
            else:
                btn.SetLabelText("Connect")
                self.disconnect()

    def OnStart(self, e):
        """ Button action to take measurements periodically

        When clicked for the first time, it will create a RepeatedTimer to call
        getAllReadings() every second. When clicked again, it will stop the
        timer.
        If in 'Test Mode', instead of calling the getAllReadings() method,
        it will call simulateSensorReadings()
        """
        btn = e.GetEventObject()
        is_pressed = btn.GetValue()
        if is_pressed:
            btn.SetLabelText("Stop")
            is_test_mode = self.btn_test.GetValue()
            if is_test_mode:
                self.rt = RepeatedTimer(1, self.simulateSensorReadings)
            else:
                self.rt = RepeatedTimer(1, self.getAllReadings)
        else:
            btn.SetLabelText("Start")
            self.rt.stop()

    def OnMeasure(self, e):
        """ Button action to take a single set of measurements

        If in 'Test Mode', instead of calling the getAllReadings() method,
        it will call simulateSensorReadings()
        """
        is_test_mode = self.btn_test.GetValue()
        if is_test_mode:
            self.simulateSensorReadings()
        else:
            self.getAllReadings()

    def OnErase(self, e):
        """ Button action to delete last measurement from log text """
        if self.logText.GetValue() != "":
            lastPosition = self.logText.GetLastPosition()
            self.logText.Remove(self.lastRecord[-1], lastPosition)
            if len(self.lastRecord) > 1:
                del self.lastRecord[-1]

    def sayHi(self):
        """ Display text for debugging the OnStart method """
        self.logText.AppendText("Hi, Roberto \n")

    def simulateSensorReadings(self):
        """ Return random numbers to represent behavior of getAllReadings()

        For the GPS output the behavior is not random, but fixed.
        It is used when in 'Test Mode'
        """
        self.lastRecord.append(self.logText.GetLastPosition())
        self.logText.AppendText("*****" + str(self.numReadings) + "*****\n")
        for label in self.labels:
            if self.cfg.ReadBool("connected" + label, False):
                if label[0] == "g":
                    reading = [
                        -73.939830 + 0.001 * self.numReadings,
                        45.423804 + 0.001 * self.numReadings,
                    ]
                else:
                    reading = []
                    for i in range(len(variables[label[0]])):
                        reading.append(random.random())
                self.updateUI(np.array(reading), label)
        self.plotter.refresh()
        self.numReadings += 1

    def getAllReadings(self):
        """ Get readings from all sensors

        Everytime a new measurement arrives, it triggers a call to the
        updateUI() method
        It also appends a header to the log text of the style '***0***'
        Will fail if the Connect button is not activated
        """
        self.lastRecord.append(self.logText.GetLastPosition())
        self.logText.AppendText("*****" + str(self.numReadings) + "*****\n")
        for label in self.labels:
            if self.cfg.ReadBool("connected" + label, False):
                reading = getSensorReading(self.label_to_device[label], label)
                self.updateUI(reading, label)
        self.plotter.refresh()
        self.numReadings += 1

    def updateUI(self, someValue, label):
        """ Updates UI after receiving new sensor data

        This is a general method that calls the more specific ones if necessary
        """
        if label[0] == "g":
            values = processGPS(
                someValue,
                label,
                self.GPS_constants,
                self.numReadings,
                self.previous_measurements,
                self.cfg,
            )
            if values is None:
                wx.MessageBox(
                    ("The dimensions in Layout have not been " + "properly set"),
                    "Empty port",
                    wx.OK | wx.ICON_WARNING,
                )
            else:
                self.updateMap(values, label)
                self.updateLog(values, label)
                self.updatePlot(values, label)
        else:
            values = someValue
            self.updateLog(values, label)
            self.updatePlot(values, label)

    def updateLog(self, someValue, label):
        """ Update log text after receiving new sensor data """
        if someValue is not None:
            ts = datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")
            value_text = []
            for value in someValue:
                value_text.append(str(np.round(value, 4)))
            self.logText.AppendText(
                (label + ";" + ts + ";" + ",".join(value_text) + "\n")
            )

    def updatePlot(self, someValue, label):
        """ Updates plots after receiving new sensor data

        Instead of appending new points to a pre-existing plot, everytime a new
        point arrives, a new plot is created next to it. Because it is made to
        match in color and style, it looks as if everything was connected.
        However, because of this way of updating the plots, the legends need to
        be created manually.
        Besides creating new plots, this method updates the attribute
        previous_measurements
        """
        sensor_type = label[0]
        if devices[sensor_type][1]:
            # color_number is to form the format 'C0' to cycle over colors
            # The value of 1 needs to be substracted because the 'C0' format
            # uses '0 to n-1' indexing, while the labels use '1 to n'
            color_number = int(label[2]) - 1
            if label[1] == "R":
                # The order was made so that all right sensors would go after
                # all the left ones
                color_number += self.cfg.ReadInt("numSensors", 1)
        else:
            if label[1] == "L":
                color_number = 0
            else:
                color_number = 1
        measured_properties = variables[sensor_type]
        for i, measured_property in enumerate(measured_properties):
            # The first set of measurements produce just dots, while the
            # subsequent ones produce lines connecting those dots
            if self.numReadings == 0:
                if np.isnan(someValue[i]):
                    self.axes[measured_property].plot(
                        0,
                        -1,
                        marker=",",
                        color="C" + str(color_number),
                        markerfacecolor="C" + str(color_number),
                    )
                else:
                    self.axes[measured_property].plot(
                        0,
                        someValue[i],
                        marker="o",
                        color="C" + str(color_number),
                        markerfacecolor="C" + str(color_number),
                    )
            else:
                previous = self.previous_measurements[label + "/" + measured_property]
                if np.isnan(someValue[i]):
                    if np.isnan(previous):
                        self.axes[measured_property].plot(
                            [self.numReadings - 1, self.numReadings],
                            [-1, -1],
                            marker=",",
                            color="C" + str(color_number),
                            markerfacecolor="C" + str(color_number),
                        )
                    else:
                        self.axes[measured_property].plot(
                            [self.numReadings - 1, self.numReadings],
                            [previous, -1],
                            marker=",",
                            color="C" + str(color_number),
                            markerfacecolor="C" + str(color_number),
                        )
                else:
                    if np.isnan(previous):
                        self.axes[measured_property].plot(
                            [self.numReadings - 1, self.numReadings],
                            [-1, someValue[i]],
                            marker=",",
                            color="C" + str(color_number),
                            markerfacecolor="C" + str(color_number),
                        )
                        self.axes[measured_property].plot(
                            self.numReadings,
                            someValue[i],
                            marker="o",
                            color="C" + str(color_number),
                            markerfacecolor="C" + str(color_number),
                        )
                    else:
                        self.axes[measured_property].plot(
                            [self.numReadings - 1, self.numReadings],
                            [previous, someValue[i]],
                            marker="o",
                            color="C" + str(color_number),
                            markerfacecolor="C" + str(color_number),
                        )
            self.previous_measurements[label + "/" + measured_property] = someValue[i]

    def updateMap(self, someValue, label):
        """ Update map after receiving new sensor data

        Place a marker in the locations of the map where the vehicle and
        the sensors are (except the GPS receiver itself).
        It uses the Settings from the Layout dialog to calculate relative
        positions and convert from the world coordinate system to that of the
        vehicle (or vice-versa)
        The first set of readings doesn't produce changes in the plot because
        at least two measurements are required to compute the heading, which
        in turn is required to know how to orient the sensor markers
        """
        if (self.numReadings > 0) and (not any(np.isnan(someValue[2:5]))):
            vehicle_x = someValue[2]
            vehicle_y = someValue[3]
            heading_radians = math.pi * someValue[4] / 180
            self.mapAxes.plot(vehicle_x, vehicle_y, "bs")
            for label in self.labels:
                if (label[0] != "g") and self.cfg.ReadBool("connected" + label, False):
                    if label[0] == "u":
                        color = "y"
                        db = self.cfg.ReadFloat("DB1") / 100
                    else:
                        color = "r"
                        db = (
                            self.cfg.ReadFloat("DB1") + self.cfg.ReadFloat("DB2")
                        ) / 100
                    if label[0] == "e":
                        color = "g"
                        index = self.cfg.ReadInt("IE" + label[1])
                        accumulator = 0
                        for i in range(index):
                            accumulator += self.cfg.ReadFloat(
                                "D" + label[1] + str(i + 1)
                            )
                        if label[1] == "L":
                            ds = -1 * accumulator / 100
                        else:
                            ds = accumulator / 100
                        ds += self.cfg.ReadFloat("DE" + label[1]) / 100
                    else:
                        accumulator = 0
                        for i in range(int(label[2])):
                            accumulator += self.cfg.ReadFloat(
                                "D" + label[1] + str(i + 1)
                            )
                        if label[1] == "L":
                            ds = -1 * accumulator / 100
                        else:
                            ds = accumulator / 100
                    sensor_x = (
                        vehicle_x
                        + ds * math.sin(heading_radians)
                        - db * math.cos(heading_radians)
                    )
                    sensor_y = (
                        vehicle_y
                        - ds * math.cos(heading_radians)
                        - db * math.sin(heading_radians)
                    )
                    self.mapAxes.plot(
                        sensor_x,
                        sensor_y,
                        marker="P",
                        color=color,
                        markerfacecolor=color,
                    )
            self.mapPanel.refresh()

    def logSettings(self):
        """ Append settings to log """
        self.logText.AppendText("**************Settings-Start**************\n")
        more, value, index = self.cfg.GetFirstEntry()
        while more:
            initial = value[0]
            if value != "notEmpty":
                if (initial == "I") or (initial == "n"):
                    property = str(self.cfg.ReadInt(value))
                if initial == "D":
                    property = str(self.cfg.ReadFloat(value))
                if initial == "c":
                    property = str(self.cfg.ReadBool(value))
                if initial == "p":
                    property = self.cfg.Read(value)
                self.logText.AppendText("{" + value + ": " + property + "}\n")
            more, value, index = self.cfg.GetNextEntry(index)
        self.logText.AppendText("**************Settings-End****************\n")

    def getLabels(self):
        """ Produces list of sensor labels

        Since many methods need to iterate over all the labels, it is handy to
        have the attribute labels to keep them available. This method is used
        to update the value of labels whenever the number of sensors changes
        """
        num_sensors = self.cfg.ReadInt("numSensors", 1)
        labels = []
        device_tuples = list(devices.values())
        for device_tuple in device_tuples:
            name = device_tuple[0]
            scaling = device_tuple[1]
            initial = name[0].lower()
            if scaling:
                for i in range(num_sensors):
                    labels.append(initial + "L" + str(i + 1))
                for i in range(num_sensors):
                    labels.append(initial + "R" + str(i + 1))
            else:
                labels.append(initial + "L")
                labels.append(initial + "R")
        return labels

    def updateCameraPorts(self):
        camera_ports = [None, None]
        if self.cfg.ReadBool("connectedcL", False):
            try:
                camera_ports[0] = int(self.cfg.Read("portcL", ""))
            except Exception as e:
                pass
        if self.cfg.ReadBool("connectedcR", False):
            try:
                camera_ports[1] = int(self.cfg.Read("portcR", ""))
            except Exception as e:
                pass
        return camera_ports

    def disconnect(self):
        """ Disconnect from all serial sensors """
        all_devices = list(self.label_to_device.values())
        for device in all_devices:
            device.close()
        self.label_to_device = {}

    def clearVariables(self):
        """ Resets the values of attributes any time a new survey starts """
        self.labels = self.getLabels()
        self.numReadings = 0
        self.lastRecord = [0]
        self.previous_measurements = {}
        self.GPS_constants = [0, 180, 90, 0, 0]
