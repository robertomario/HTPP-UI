""" Display main window """

# Author: Roberto Buelvas

from datetime import datetime
import random
import time
import os

import wx

from .plot_notebook import Plot, PlotNotebook
from .repeated_timer import RepeatedTimer
from .layout_dialog import LayoutDialog
from .ports_dialog import PortsDialog, devices
from .sensors import openPort, getSensorReading


# Dict to hold what sensor is the origin for each measured variable
# 0 >> Multispectral
# 1 >> Ultrasonic
# 2 >> GPS
# 3 >> Environmental
variables = {
    'm': ['CI', 'NDRE', 'NDVI', 'proxy Distance', 'proxy LAI', 'proxy CCC',
          'Red-Edge', 'NIR', 'Red'],
    'u': ['Distance'],
    'g': ['Latitude', 'Longitude'],
    'e': ['Canopy Temperature', 'Air Temperature', 'Humidity', 'Reflected PAR',
          'Incident PAR', 'Pressure']
}


class MainWindow(wx.Frame):
    """ Class to define main window """

    def __init__(self, *args, **kwargs):
        """ Create new window """
        super(MainWindow, self).__init__(*args, **kwargs)
        self.cfg = wx.Config('HTPPconfig')
        self.cfg.WriteBool('notEmpty', True)
        self.numReadings = 0
        self.lastRecord = [0]
        self.axes = {}
        self.label_to_device = {}
        self.initUI()
        self.previous_measurements = {}

    def initUI(self):
        """ Define window elements """
        menubar = wx.MenuBar()

        fileMenu = wx.Menu()
        newmi = wx.MenuItem(fileMenu, wx.ID_NEW, '&New')
        fileMenu.Append(newmi)
        self.Bind(wx.EVT_MENU, self.OnNew, newmi)
        savemi = wx.MenuItem(fileMenu, wx.ID_SAVE, '&Save')
        fileMenu.Append(savemi)
        self.Bind(wx.EVT_MENU, self.OnSave, savemi)
        fileMenu.AppendSeparator()
        qmi = wx.MenuItem(fileMenu, wx.ID_EXIT, '&Quit')
        fileMenu.Append(qmi)
        self.Bind(wx.EVT_MENU, self.OnQuit, qmi)
        menubar.Append(fileMenu, '&File')

        settingsMenu = wx.Menu()
        portsmi = wx.MenuItem(settingsMenu, wx.ID_PREFERENCES, '&Ports')
        settingsMenu.Append(portsmi)
        self.Bind(wx.EVT_MENU, self.OnPorts, portsmi)
        layoutmi = wx.MenuItem(settingsMenu, wx.ID_ANY, '&Layout')
        settingsMenu.Append(layoutmi)
        self.Bind(wx.EVT_MENU, self.OnLayout, layoutmi)
        clearmi = wx.MenuItem(settingsMenu, wx.ID_ANY, '&Clear')
        settingsMenu.Append(clearmi)
        self.Bind(wx.EVT_MENU, self.OnClear, clearmi)
        menubar.Append(settingsMenu, '&Settings')

        helpMenu = wx.Menu()
        aboutmi = wx.MenuItem(helpMenu, wx.ID_ABOUT, '&About')
        helpMenu.Append(aboutmi)
        self.Bind(wx.EVT_MENU, self.OnAbout, aboutmi)
        menubar.Append(helpMenu, '&Help')

        self.SetMenuBar(menubar)

        backgroundPanel = wx.Panel(self)
        backgroundPanel.SetBackgroundColour('#ededed')

        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)

        outerBox = wx.BoxSizer(wx.HORIZONTAL)

        leftBox = wx.BoxSizer(wx.VERTICAL)
        st1 = wx.StaticText(backgroundPanel, label='Map:')
        mapPanel = Plot(backgroundPanel)
        self.mapAxes = mapPanel.figure.gca()
        st2 = wx.StaticText(backgroundPanel, label='Log:')
        self.logText = wx.TextCtrl(backgroundPanel, style=wx.TE_MULTILINE
                                   | wx.TE_READONLY)
        self.logSettings()
        leftBox.Add(st1, proportion=0, flag=wx.ALL)
        leftBox.Add(mapPanel, wx.ID_ANY, wx.EXPAND | wx.ALL, 20)
        leftBox.Add(st2, proportion=0, flag=wx.ALL)
        leftBox.Add(self.logText, wx.ID_ANY, wx.EXPAND | wx.ALL, 20)

        middleBox = wx.BoxSizer(wx.VERTICAL)
        st3 = wx.StaticText(backgroundPanel, label='Plot:')
        self.plotter = PlotNotebook(backgroundPanel)
        num_sensors = self.cfg.ReadInt('numSensors', 1)
        for device_name in list(variables.keys()):
            variable_names = variables[device_name]
            scaling = devices[device_name][1]
            for name in variable_names:
                self.axes[name] = self.plotter.add(name, device_name, scaling,
                                                   num_sensors)

        middleBox.Add(st3, proportion=0, flag=wx.ALL)
        middleBox.Add(self.plotter, proportion=7, flag=wx.EXPAND | wx.ALL,
                      border=20)

        rightBox = wx.BoxSizer(wx.VERTICAL)
        btn_connect = wx.ToggleButton(backgroundPanel, label='Connect')
        btn1 = wx.ToggleButton(backgroundPanel, label='Start')
        btn2 = wx.Button(backgroundPanel, label='Measure')
        btn3 = wx.Button(backgroundPanel, label='Erase')
        btn_connect.Bind(wx.EVT_TOGGLEBUTTON, self.OnConnect)
        btn1.Bind(wx.EVT_TOGGLEBUTTON, self.OnStart)
        btn2.Bind(wx.EVT_BUTTON, self.OnMeasure)
        btn3.Bind(wx.EVT_BUTTON, self.OnErase)
        rightBox.Add(btn_connect, proportion=1, flag=wx.EXPAND | wx.ALL,
                     border=20)
        rightBox.Add(btn1, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(btn2, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(btn3, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)

        outerBox.Add(leftBox, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        outerBox.Add(middleBox, proportion=2, flag=wx.EXPAND | wx.ALL,
                     border=20)
        outerBox.Add(rightBox, proportion=1, flag=wx.EXPAND | wx.ALL,
                     border=20)
        backgroundPanel.SetSizer(outerBox)

        self.Maximize()
        self.SetTitle('High-Throughput Plant Phenotyping Platform')
        self.Centre()

    def OnNew(self, e):
        """ Toolbar option to reset log without saving"""
        confirmDiag = wx.MessageDialog(None,
                                       ('Are you sure you want to clear '
                                        + 'the log?'),
                                       'Question',
                                       (wx.YES_NO | wx.NO_DEFAULT
                                        | wx.ICON_QUESTION))
        dialogFlag = confirmDiag.ShowModal()
        if(dialogFlag == wx.ID_YES):
            self.logText.SetValue('')
            self.plotter.clear()
            self.numReadings = 0
            self.logSettings()

    def OnSave(self, e):
        """ Toolbar option to save and reset log """
        rootName = ('HHPLogFile'
                    + datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')
                    + 'X')
        i = 1
        while(os.path.isfile(rootName+str(i) + '.txt')):
            i += 1
        finalFilename = rootName + str(i) + '.txt'
        self.logText.SaveFile(finalFilename)
        self.logText.SetValue('')
        self.plotter.clear()
        self.numReadings = 0

    def OnQuit(self, e):
        """ Toolbar option to exit application """
        self.Close()

    def OnAbout(self, e):
        """ Toolbar option to show About dialog """
        wx.MessageBox(("High-Throughput Plant Phenotyping Platform \n"
                       "Made by Roberto Buelvas\n"
                       "McGill University, 2020\n"
                       "Version 0.1\n"),
                      'About', wx.OK | wx.ICON_INFORMATION)

    def OnPorts(self, e):
        """ Toolbar option to open ports dialog window """
        pDialog = PortsDialog(self.cfg, self)
        dialogFlag = pDialog.ShowModal()
        if(dialogFlag == wx.ID_OK):
            results = pDialog.getSettings()
            labels = self.getLabels()
            for label in labels:
                self.cfg.WriteBool('connected'+label,
                                   results.ReadBool('connected' + label))
                self.cfg.Write('port'+label, results.Read('port' + label))
            self.logSettings()
        pDialog.Destroy()

    def OnLayout(self, e):
        """ Toolbar option to open ports dialog window """
        lDialog = LayoutDialog(self.cfg, self)
        dialogFlag = lDialog.ShowModal()
        if(dialogFlag == wx.ID_OK):
            results = lDialog.getSettings()
            settings_list = lDialog.getSettingsList()
            for setting_key in settings_list:
                if(setting_key[0] == 'D'):
                    self.cfg.WriteFloat(setting_key,
                                        results.ReadFloat(setting_key))
                if(setting_key[0] == 'I'):
                    self.cfg.WriteInt(setting_key,
                                      results.ReadInt(setting_key))
            self.logSettings()
        lDialog.Destroy()

    def OnClear(self, e):
        """ Toolbar option to clear all settings """
        confirmDiag = wx.MessageDialog(None,
                                       ('Are you sure you want to clear '
                                        + 'the settings?'),
                                       'Question',
                                       (wx.YES_NO | wx.NO_DEFAULT
                                        | wx.ICON_QUESTION))
        dialogFlag = confirmDiag.ShowModal()
        if(dialogFlag == wx.ID_YES):
            all_config_keys = []
            more, value, index = self.cfg.GetFirstEntry()
            while(more):
                all_config_keys.append(value)
                more, value, index = self.cfg.GetNextEntry(index)
            all_config_keys.remove('notEmpty')
            for key in all_config_keys:
                self.cfg.DeleteEntry(key)

    def OnConnect(self, e):
        """ Toggle button action to connect/disconnect from sensors """
        btn = e.GetEventObject()
        is_pressed = btn.GetValue()
        if(is_pressed):
            btn.SetLabelText('Disconnect')
            self.label_to_device = {}
            labels = self.getLabels()
            for label in labels:
                if(self.cfg.ReadBool('connected' + label, False)):
                    port = self.cfg.Read('port' + label)
                    if(port == ''):
                        wx.MessageBox(("The port for " + label
                                      + "has not been properly selected"),
                                      'Empty port', wx.OK | wx.ICON_WARNING)
                        break
                    else:
                        device = openPort(port, label)
                        self.label_to_device[label] = device
        else:
            btn.SetLabelText('Connect')
            self.disconnect()

    def OnStart(self, e):
        """ Button action to take measurements periodically """
        # self.rt = RepeatedTimer(1, self.sayHi)
        btn = e.GetEventObject()
        is_pressed = btn.GetValue()
        if(is_pressed):
            btn.SetLabelText('Stop')
            self.rt = RepeatedTimer(1, self.simulateSensorReadings)
        else:
            btn.SetLabelText('Start')
            self.rt.stop()

    def OnMeasure(self, e):
        """ Button action to take one measurement """
        # self.getAllReadings()
        self.simulateSensorReadings()

    def OnErase(self, e):
        """ Button action to delete last measurement from log """
        if(self.logText.GetValue() != ''):
            lastPosition = self.logText.GetLastPosition()
            self.logText.Remove(self.lastRecord[-1], lastPosition)
            if(len(self.lastRecord) > 1):
                del self.lastRecord[-1]

    def sayHi(self):
        """ Display text for debugging the OnStart method """
        self.logText.AppendText("Hi, Roberto \n")

    def simulateSensorReadings(self):
        """ Create random number to pretend behaviour of getAllReadings() """
        self.lastRecord.append(self.logText.GetLastPosition())
        self.logText.AppendText('*****'+str(self.numReadings)+'*****\n')
        labels = self.getLabels()
        for label in labels:
            if(self.cfg.ReadBool('connected' + label, False)):
                reading = []
                for i in range(len(variables[label[0]])):
                    reading.append(random.random())
                self.updateUI(reading, label)
        self.plotter.refresh()
        self.numReadings += 1

    def getAllReadings(self):
        """ Get readings from all sensors """
        self.lastRecord.append(self.logText.GetLastPosition())
        self.logText.AppendText('*****'+str(self.numReadings)+'*****\n')
        labels = self.getLabels()
        for label in labels:
            if(self.cfg.ReadBool('connected' + label, False)):
                reading = getSensorReading(self.label_to_device[label], label)
                self.updateUI(reading, label)
        self.numReadings += 1

    def updateUI(self, someValue, label):
        self.updateLog(someValue, label)
        self.updatePlot(someValue, label)
        if(label[0] == 'g'):
            self.updateMap(someValue, label)

    def updateLog(self, someValue, label):
        """ Update UI after receiving new sensor data """
        if(someValue is not None):
            ts = datetime.fromtimestamp(time.time()) \
                         .strftime('%Y-%m-%d %H:%M:%S')
            self.logText.AppendText((label + ';' + ts + ';'
                                    + str(someValue)[1:-1] + '\n'))
        else:
            pass

    def updatePlot(self, someValue, label):

        sensor_type = label[0]
        if(devices[sensor_type][1]):
            print(label)
            color_number = int(label[2])-1
            if(label[1] == 'R'):
                color_number += self.cfg.ReadInt('numSensors', 1)
        else:
            if(label[1] == 'L'):
                color_number = 0
            else:
                color_number = 1
        measured_properties = variables[sensor_type]
        for i, measured_property in enumerate(measured_properties):
            if(self.numReadings == 0):
                self.axes[measured_property] \
                    .plot(self.numReadings, someValue[i], marker='o',
                          color='C' + str(color_number),
                          markerfacecolor='C' + str(color_number))
            else:
                self.axes[measured_property] \
                    .plot([self.numReadings-1, self.numReadings],
                          [self.previous_measurements[(label + '/'
                                                       + measured_property)],
                          someValue[i]], marker='o',
                          color='C' + str(color_number),
                          markerfacecolor='C' + str(color_number))
            self.previous_measurements[(label + '/'
                                        + measured_property)] = someValue[i]

    def updateMap(self, someValue, label):
        self.mapAxes.plot(someValue, label)
        # TODO

    def logSettings(self):
        self.logText.AppendText('**************Settings-Start**************\n')
        more, value, index = self.cfg.GetFirstEntry()
        while(more):
            initial = value[0]
            if(value != 'notEmpty'):
                if((initial == 'I') or (initial == 'n')):
                    property = str(self.cfg.ReadInt(value))
                if(initial == 'D'):
                    property = str(self.cfg.ReadFloat(value))
                if(initial == 'c'):
                    property = str(self.cfg.ReadBool(value))
                if(initial == 'p'):
                    property = self.cfg.Read(value)
                self.logText.AppendText('{' + value + ': ' + property + '}\n')
            more, value, index = self.cfg.GetNextEntry(index)
        self.logText.AppendText('**************Settings-End****************\n')

    def getLabels(self):
        num_sensors = self.cfg.ReadInt('numSensors', 1)
        labels = []
        device_tuples = list(devices.values())
        for device_tuple in device_tuples:
            name = device_tuple[0]
            scaling = device_tuple[1]
            initial = name[0].lower()
            if(scaling):
                for i in range(num_sensors):
                    labels.append(initial+'L'+str(i+1))
                for i in range(num_sensors):
                    labels.append(initial+'R'+str(i+1))
            else:
                labels.append(initial+'L')
                labels.append(initial+'R')
        return labels

    def disconnect(self):
        all_devices = list(self.label_to_device.values())
        for device in all_devices:
            device.close()
        self.label_to_device = {}
