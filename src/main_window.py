""" Display main window """

# Author: Roberto Buelvas

from datetime import datetime
import time
import math
import os

import numpy as np
import wx

from .sensors import SensorHandler, setupGPSProjection, variables
from .ports_dialog import PortsDialog, devices
from .plot_notebook import Plot, PlotNotebook
from .repeated_timer import RepeatedTimer
from .layout_dialog import LayoutDialog
from .cameras import CameraFrame


class MainWindow(wx.Frame):
    """ Class to define main window

    This class both creates the main window of the UI and controls the
    operations that are done within it.

    Attr:
        cfg (wx.ConfigBase): Settings are saved in here, which creates a file
            in a hidden folder to store values. These values are kept if the
            program stops running and even if the computers turns off. It uses
            a key-value system similar to dictionaries
        btn_connect (wx.ToggleButton): Button to toggle connect/disconnect
        btn_start (wx.ToggleButton): Button to toggle start/stop reading every second
        btn_test (wx.ToggleButton): Button to toggle in and out of 'Test Mode'
        btn_measure (wx.Button): Button to take a single set of readings
        logText (wx.TextCtrl): Control where information is logged
        timer (wx.Timer): Object to call a function periodically
        sensor_handler (SensorHandler): Object to control multiple sensors at once
        camera_frame (CameraFrame): Secondary frame to display video from cameras
        mapAxes (matplotlib.Axes): Axes to create map plot
        mapPanel (Plot): Panel containing the Figure where the map is drawn
        axes (dict): Dict to hold the Axes for each measured variables. Keys
            are of the format 'mL1/NDVI' or 'gR/Latitude'. Used to create the
            plots
        labels (list): List of all possible labels of the style mL1 or gR given
            the number of scaling sensors
        last_record (list): List showing positions in the text log where each
            set of measurements ends. Used to erase the last set of values from
            the log text
        num_readings (int): Stores how many sets of measurements have been taken
            in the current survey. Set back to 0 when log text is cleared or
            exported to file
    """

    def __init__(self, *args, **kwargs):
        """ Create new window """
        super(MainWindow, self).__init__(*args, **kwargs)
        self.cfg = wx.Config("HTPPconfig")
        self.cfg.WriteBool("notEmpty", True)
        self.labels = self.updateLabels()
        self.axes = {}
        self.reset()
        self.initUI()
        self.sensor_handler = None
        self.updateSensorHandler()
        self.camera_frame = None
        self.updateCameraFrame()
        self.camera_frame.Bind(wx.EVT_CLOSE, self.OnCameraClose)
        self.timer = wx.Timer(self, wx.Window.NewControlId())
        self.Bind(wx.EVT_TIMER, self.OnUpdate, id=self.timer.GetId())
        self.Bind(wx.EVT_CLOSE, self.OnClose)

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
        self.btn_connect = wx.ToggleButton(backgroundPanel, label="Connect")
        self.btn_start = wx.ToggleButton(backgroundPanel, label="Start")
        self.btn_start.Disable()
        self.btn_test = wx.ToggleButton(backgroundPanel, label="Test Mode")
        self.btn_measure = wx.Button(backgroundPanel, label="Measure")
        self.btn_measure.Disable()
        btn_erase = wx.Button(backgroundPanel, label="Erase")
        self.btn_connect.Bind(wx.EVT_TOGGLEBUTTON, self.OnConnect)
        self.btn_start.Bind(wx.EVT_TOGGLEBUTTON, self.OnStart)
        self.btn_measure.Bind(wx.EVT_BUTTON, self.OnUpdate)
        btn_erase.Bind(wx.EVT_BUTTON, self.OnErase)
        rightBox.Add(self.btn_connect, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(self.btn_start, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(self.btn_test, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(self.btn_measure, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(btn_erase, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)

        outerBox.Add(leftBox, proportion=2, flag=wx.EXPAND | wx.ALL, border=20)
        outerBox.Add(middleBox, proportion=3, flag=wx.EXPAND | wx.ALL, border=20)
        outerBox.Add(rightBox, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        backgroundPanel.SetSizer(outerBox)

        self.Maximize()
        self.SetTitle("High-Throughput Plant Phenotyping Platform")
        self.Centre()

    def OnClose(self, e):
        """ Response to close event
        
        Make sure to disconnect from all sensors and camera before exiting
        """
        self.sensor_handler.closeAll()
        self.camera_frame.close()
        self.DestroyLater()

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
            self.reset()

    def OnSave(self, e):
        """ Toolbar option to save and reset log """
        rootName = "data/HTPPLogFile" + datetime.now().strftime("%Y-%m-%d") + "X"
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
        self.reset()

    def OnQuit(self, e):
        """ Toolbar option to exit application """
        self.Close()

    def OnCamera(self, e):
        """ Show or hide camera frame depeding on checkable menu item """
        self.camera_frame.Show(self.camerami.IsChecked())

    def OnCameraClose(self, e):
        """ Safely close camera frame """
        self.camerami.Check(False)
        self.updateCameraFrame()

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
        pDialog = PortsDialog(self, self.cfg)
        dialogFlag = pDialog.ShowModal()
        if dialogFlag == wx.ID_OK:
            results = pDialog.getSettings()
            num_sensors = results.ReadInt("numSensors", 1)
            self.cfg.WriteInt("numSensors", num_sensors)
            self.labels = self.updateLabels()
            for label in self.labels:
                self.cfg.WriteBool(
                    "connected" + label, results.ReadBool("connected" + label)
                )
                self.cfg.Write("port" + label, results.Read("port" + label))
            self.updateSensorHandler()
            self.updateCameraFrame()
            self.logSettings()
            self.plotter.redoLegend(variables, devices, num_sensors)
        pDialog.Destroy()

    def OnLayout(self, e):
        """ Toolbar option to open ports dialog window """
        lDialog = LayoutDialog(self, self.cfg)
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
        # TODO
        condition = False
        if condition:
            wx.MessageBox(
                "The dimensions in Layout have not been properly set",
                "Empty port",
                wx.OK | wx.ICON_WARNING,
            )
        lDialog.Destroy()

    def OnClear(self, e):
        """ Toolbar option to clear all settings

        This removes every entry from the attribute cfg, except for a dummy
        entry 'notEmpty' to prevent the ConfigBase of being entirerly empty,
        which causes it to crash.
        Not to be confounded with the method reset(), which resets
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

        When in 'Test Mode', it simulates a first GPS reading to compute the projection
        constants
        Start and Measure buttons are only enabled if connected
        Test button is only enabled if disconnected 
        """
        btn = e.GetEventObject()
        is_pressed = btn.GetValue()
        is_test_mode = self.btn_test.GetValue()
        if is_test_mode:
            if is_pressed:
                for label in self.labels:
                    if (label[0] == "g") and self.cfg.ReadBool(
                        "connected" + label, False
                    ):
                        reading = [-73.939830, 45.423804]
                        self.sensor_handler.GPS_constants = setupGPSProjection(reading)
                btn.SetLabelText("Disconnect")
            else:
                btn.SetLabelText("Connect")
        else:
            if is_pressed:
                success = self.sensor_handler.openAll()
                if success:
                    btn.SetLabelText("Disconnect")
                    self.btn_start.Enable(is_pressed)
                    self.btn_measure.Enable(is_pressed)
                    self.btn_test.Enable(not is_pressed)
                else:
                    wx.MessageBox(
                        "At least one port has not been properly set up",
                        "Empty port",
                        wx.OK | wx.ICON_WARNING,
                    )
                    btn.SetValue(False)
            else:
                self.sensor_handler.closeAll()
                btn.SetLabelText("Connect")
                self.btn_start.Enable(is_pressed)
                self.btn_measure.Enable(is_pressed)
                self.btn_test.Enable(not is_pressed)

    def OnStart(self, e):
        """ Button action to take measurements periodically

        When clicked for the first time, it will start the timer. When clicked again,
        it will stop it.
        """
        btn = e.GetEventObject()
        is_pressed = btn.GetValue()
        if is_pressed:
            self.timer.Start(200.0)
            btn.SetLabelText("Stop")
        else:
            self.timer.Stop()
            btn.SetLabelText("Start")
        self.btn_connect.Enable(not is_pressed)
        self.btn_measure.Enable(not is_pressed)
        self.btn_test.Enable(not is_pressed)

    def OnErase(self, e):
        """ Button action to delete last measurement from log text """
        if self.logText.GetValue() != "":
            lastPosition = self.logText.GetLastPosition()
            self.logText.Remove(self.last_record[-1], lastPosition)
            if len(self.last_record) > 1:
                del self.last_record[-1]

    def OnUpdate(self, e):
        """ Updates UI by getting new sensor data

        This is a general method that calls the more specific ones if necessary
        """
        is_test_mode = self.btn_test.GetValue()
        self.last_record.append(self.logText.GetLastPosition())
        self.logText.AppendText("*****" + str(self.num_readings) + "*****\n")
        if is_test_mode:
            for label in self.labels:
                if self.cfg.ReadBool("connected" + label, False):
                    reading = self.sensor_handler.simulate(
                        label, self.num_readings, self.cfg
                    )
                    if label[0] == "g":
                        self.updateMap(reading, label)
                    self.updateLog(reading, label)
                    self.updatePlot(reading, label)
        else:
            for label in self.labels:
                reading = self.sensor_handler.read(label, self.num_readings, self.cfg)
                if reading is not None:
                    if label == "g":
                        self.updateMap(reading, label)
                    self.updateLog(reading, label)
                    self.updatePlot(reading, label)
        self.plotter.refresh()
        self.num_readings += 1

    def updateLog(self, someValue, label):
        """ Update log text after receiving new sensor data """
        if someValue is not None:
            ts = datetime.now().strftime("%H:%M:%S.%f")
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
            if self.num_readings == 0:
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
                previous = self.sensor_handler.previous_measurements[
                    label + "/" + measured_property
                ]
                if np.isnan(someValue[i]):
                    if np.isnan(previous):
                        self.axes[measured_property].plot(
                            [self.num_readings - 1, self.num_readings],
                            [-1, -1],
                            marker=",",
                            color="C" + str(color_number),
                            markerfacecolor="C" + str(color_number),
                        )
                    else:
                        self.axes[measured_property].plot(
                            [self.num_readings - 1, self.num_readings],
                            [previous, -1],
                            marker=",",
                            color="C" + str(color_number),
                            markerfacecolor="C" + str(color_number),
                        )
                else:
                    if np.isnan(previous):
                        self.axes[measured_property].plot(
                            [self.num_readings - 1, self.num_readings],
                            [-1, someValue[i]],
                            marker=",",
                            color="C" + str(color_number),
                            markerfacecolor="C" + str(color_number),
                        )
                        self.axes[measured_property].plot(
                            self.num_readings,
                            someValue[i],
                            marker="o",
                            color="C" + str(color_number),
                            markerfacecolor="C" + str(color_number),
                        )
                    else:
                        self.axes[measured_property].plot(
                            [self.num_readings - 1, self.num_readings],
                            [previous, someValue[i]],
                            marker="o",
                            color="C" + str(color_number),
                            markerfacecolor="C" + str(color_number),
                        )

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
        if (self.num_readings > 0) and (not any(np.isnan(someValue[4:7]))):
            vehicle_x = someValue[4]
            vehicle_y = someValue[5]
            heading_radians = math.pi * someValue[6] / 180
            self.mapAxes.plot(vehicle_x, vehicle_y, "bs")
            for label in self.labels:
                if (label[0] != "g") and self.cfg.ReadBool("connected" + label, False):
                    if label[0] == "u":
                        color = "y"
                        db = self.cfg.ReadFloat("DB1") / 100
                    else:
                        color = "r"
                        db = (self.cfg.ReadFloat("DB1") + self.cfg.ReadFloat("DB2")) / 100
                    if label[0] == "e":
                        color = "g"
                        index = self.cfg.ReadInt("IE" + label[1])
                        accumulator = 0
                        for i in range(index):
                            accumulator += self.cfg.ReadFloat("D" + label[1] + str(i + 1))
                        if label[1] == "L":
                            ds = -1 * accumulator / 100
                        else:
                            ds = accumulator / 100
                        ds += self.cfg.ReadFloat("DE" + label[1]) / 100
                    else:
                        accumulator = 0
                        for i in range(int(label[2])):
                            accumulator += self.cfg.ReadFloat("D" + label[1] + str(i + 1))
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

    def updateLabels(self):
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

    def updateSensorHandler(self):
        """ Create sensor handler and populate it by adding serial sensors """
        if self.sensor_handler is not None:
            self.sensor_handler.closeAll()
        self.sensor_handler = SensorHandler()
        for label in self.labels:
            is_connected = self.cfg.ReadBool("connected" + label, False)
            port = self.cfg.Read("port" + label, "")
            if is_connected and (port != ""):
                self.sensor_handler.add(port, label)

    def updateCameraFrame(self):
        """ Format camera ports as a list ready to be used as CameraFrame's input """
        if self.camera_frame is not None:
            self.camera_frame.close()
        camera_ports = [None, None]
        if self.cfg.ReadBool("connectedcL", False):
            camera_ports[0] = int(self.cfg.Read("portcL", ""))
        if self.cfg.ReadBool("connectedcR", False):
            camera_ports[1] = int(self.cfg.Read("portcR", ""))
        self.camera_frame = CameraFrame(self, camera_ports)
        self.camera_frame.Show(self.camerami.IsChecked())

    def reset(self):
        """ Reset the values of attributes any time a new survey starts """
        self.labels = self.updateLabels()
        self.num_readings = 0
        self.last_record = [0]
