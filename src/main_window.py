""" Display main window """

# Author: Roberto Buelvas

from datetime import datetime
import time
import os

import pynmea2
import serial
import wx

from .plot_notebook import Plot, PlotNotebook
from .repeated_timer import RepeatedTimer
from .layout_dialog import LayoutDialog
from .ports_dialog import PortsDialog


# Dict to hold what sensor is the origin for each measured variable
# 0 >> Multispectral
# 1 >> Ultrasonic
# 2 >> GPS
# 3 >> Environmental
variables = {
    'CI': 0,
    'NDRE': 0,
    'NDVI': 0,
    'proxy Distance': 0,
    'proxy LAI': 0,
    'proxy CCC': 0,
    'Red-Edge': 0,
    'NIR': 0,
    'Red': 0,
    'Distance': 1,
    'Latitude': 2,
    'Longitude': 2,
    'Canopy Temperature': 3,
    'Air Temperature': 3,
    'Humidity': 3,
    'Reflected PAR': 3,
    'Incident PAR': 3,
    'Pressure': 3
}


class MainWindow(wx.Frame):
    """ Class to define main window """

    def __init__(self, *args, **kwargs):
        """ Create new window """
        super(MainWindow, self).__init__(*args, **kwargs)
        self.cfg = wx.Config('HHPconfig')
        if not self.cfg.Exists('multispectralConnected'):
            self.cfg.WriteBool('multispectralConnected', False)
            self.cfg.Write('multispectralPort', '')
            self.cfg.WriteBool('ultrasonicConnected', False)
            self.cfg.Write('ultrasonicPort', '')
            self.cfg.WriteBool('GPSConnected', False)
            self.cfg.Write('GPSPort', '')
        self.numReadings = 0
        self.lastRecord = [0]
        self.axes = []
        self.initUI()

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
        leftBox.Add(st1, proportion=0, flag=wx.ALL)
        leftBox.Add(mapPanel, wx.ID_ANY, wx.EXPAND | wx.ALL, 20)
        leftBox.Add(st2, proportion=0, flag=wx.ALL)
        leftBox.Add(self.logText, wx.ID_ANY, wx.EXPAND | wx.ALL, 20)

        middleBox = wx.BoxSizer(wx.VERTICAL)
        st3 = wx.StaticText(backgroundPanel, label='Plot:')
        plotter = PlotNotebook(backgroundPanel)
        variable_names = list(variables.keys())
        for name in variable_names:
            self.axes.append(plotter.add(name).gca())
        middleBox.Add(st3, proportion=0, flag=wx.ALL)
        middleBox.Add(plotter, proportion=7, flag=wx.EXPAND | wx.ALL,
                      border=20)

        rightBox = wx.BoxSizer(wx.VERTICAL)
        panel4 = wx.Panel(backgroundPanel)
        panel4.SetBackgroundColour('#000049')
        btn1 = wx.Button(backgroundPanel, label='Start')
        btn2 = wx.Button(backgroundPanel, label='Measure')
        btn3 = wx.Button(backgroundPanel, label='Erase')
        btn4 = wx.Button(backgroundPanel, label='Stop')
        btn1.Bind(wx.EVT_BUTTON, self.OnStart)
        btn2.Bind(wx.EVT_BUTTON, self.OnMeasure)
        btn3.Bind(wx.EVT_BUTTON, self.OnErase)
        btn4.Bind(wx.EVT_BUTTON, self.OnStop)
        rightBox.Add(panel4, proportion=3, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(btn1, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(btn2, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(btn3, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        rightBox.Add(btn4, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)

        outerBox.Add(leftBox, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        outerBox.Add(middleBox, proportion=2, flag=wx.EXPAND | wx.ALL,
                     border=20)
        outerBox.Add(rightBox, proportion=1, flag=wx.EXPAND | wx.ALL,
                     border=20)
        backgroundPanel.SetSizer(outerBox)

        self.Maximize()
        self.SetTitle('HandHeld Plant Phenotyping')
        self.Centre()

    def OnNew(self, e):
        """ Toolbar option to reset log without saving"""
        confirmDiag = wx.MessageDialog(None,
                                       'Are you sure you want to clear the log?',
                                       'Question',
                                       wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        dialogFlag = confirmDiag.ShowModal()
        print(dialogFlag)
        if(dialogFlag == wx.ID_YES):
            self.logText.SetValue('')
            self.numReadings = 0
        # confirmDiag.Destroy()

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
            self.cfg.WriteBool('multispectralConnected',
                               results.ReadBool('multispectralConnected'))
            self.cfg.Write('multispectralPort',
                           results.Read('multispectralPort'))
            self.cfg.WriteBool('ultrasonicConnected',
                               results.ReadBool('ultrasonicConnected'))
            self.cfg.Write('ultrasonicPort', results.Read('ultrasonicPort'))
            self.cfg.WriteBool('GPSConnected',
                               results.ReadBool('GPSConnected'))
            self.cfg.Write('GPSPort', results.Read('GPSPort'))
        pDialog.Destroy()

    def OnLayout(self, e):
        """ Toolbar option to open ports dialog window """
        lDialog = LayoutDialog(self.cfg, self)
        dialogFlag = lDialog.ShowModal()
        if(dialogFlag == wx.ID_OK):
            results = lDialog.getSettings()
            self.cfg.WriteBool('multispectralConnected',
                               results.ReadBool('multispectralConnected'))
            self.cfg.Write('multispectralPort',
                           results.Read('multispectralPort'))
            self.cfg.WriteBool('ultrasonicConnected',
                               results.ReadBool('ultrasonicConnected'))
            self.cfg.Write('ultrasonicPort', results.Read('ultrasonicPort'))
            self.cfg.WriteBool('GPSConnected',
                               results.ReadBool('GPSConnected'))
            self.cfg.Write('GPSPort', results.Read('GPSPort'))
        lDialog.Destroy()

    def OnStart(self, e):
        """ Button action to take measurements periodically """
        self.rt = RepeatedTimer(1, self.sayHi)

    def OnMeasure(self, e):
        """ Button action to take one measurement """
        self.readAll()

    def OnErase(self, e):
        """ Button action to delete last measurement from log """
        if(self.logText.GetValue() != ''):
            lastPosition = self.logText.GetLastPosition()
            self.logText.Remove(self.lastRecord[-1], lastPosition)
            if(len(self.lastRecord) > 1):
                del self.lastRecord[-1]

    def OnStop(self, e):
        """ Button action to measurements after OnStart """
        self.rt.stop()

    def sayHi(self):
        """ Display text for debugging the OnStart method """
        self.logText.AppendText("Hi, Roberto \n")

    def readAll(self):
        """ Get readings from all sensors """
        connected = [self.cfg.ReadBool('multispectralConnected'),
                     self.cfg.ReadBool('ultrasonicConnected'),
                     self.cfg.ReadBool('GPSConnected')]
        if(any(connected)):
            self.lastRecord.append(self.logText.GetLastPosition())
            self.logText.AppendText('*****'+str(self.numReadings)+'*****\n')
            if(connected[0]):
                mr = self.getMultispectralReading()
                self.updateUI(mr)
            if(connected[1]):
                ur = self.getUltrasonicReading()
                self.updateUI(ur)
            if(connected[2]):
                gr = self.getGPSReading()
                self.updateUI(gr)
                # updateMap(gr)
            self.numReadings += 1

    def getMultispectralReading(self, numValues=10):
        """ Get reading from multispectral sensor """
        port = self.cfg.Read('multispectralPort')
        print(port)
        serialCropCircle = serial.Serial(port, 38400)
        ndre = []
        ndvi = []
        redEdge = []
        nir = []
        red = []
        for i in range(numValues):
            message = serialCropCircle.readline().strip().decode()
            measurements = message.split(',')
            measurements = [float(i) for i in measurements]
            ndre.append(measurements[0])
            ndvi.append(measurements[1])
            redEdge.append(measurements[2])
            nir.append(measurements[3])
            red.append(measurements[4])
        finalMeasurement = [sum(ndre), sum(ndvi), sum(redEdge), sum(nir),
                            sum(red)]
        finalMeasurement = [i/numValues for i in finalMeasurement]
        serialCropCircle.close()
        print(finalMeasurement)
        return finalMeasurement

    def getUltrasonicReading(self, numValues=10):
        """ Get reading from ultrasonic sensor """
        serialUltrasonic = serial.Serial(self.cfg.Read('ultrasonicPort'),
                                         38400)
        count = -1
        finalMeasurement = 0
        index = 0
        message = b''
        charList = [b'0', b'0', b'0', b'0', b'0']
        while(count < numValues):
            newChar = serialUltrasonic.read()
            if(newChar == b'\r'):
                count += 1
                message = b''.join(charList)
                measurement = 0.003384*25.4*int(message)
                finalMeasurement += measurement
                message = b''
                index = 0
            else:
                charList[index] = newChar
                index += 1
                if(index > 5):
                    index = 0
        serialUltrasonic.close()
        return finalMeasurement/numValues

    def getGPSReading(self, numValues=5):
        """ Get reading from GPS sensor """
        serialGPS = serial.Serial(self.cfg.Read('GPSPort'), 9600)
        i = 0
        while(i < numValues):
            message = serialGPS.readline().strip().decode()
            if(message[0:6] == '$GPGGA' or message[0:6] == '$GPGLL'):
                i += 1
                parsedMessage = pynmea2.parse(message)
                finalMeasurement = [parsedMessage.longitude,
                                    parsedMessage.latitude]
        serialGPS.close()
        return finalMeasurement

    def updateUI(self, someValue):
        """ Update UI after receiving new sensor data """
        if(someValue is not None):
            ts = datetime.fromtimestamp(time.time()) \
                         .strftime('%Y-%m-%d %H:%M:%S')
            if(isinstance(someValue, list)):
                if(len(someValue) >= 5):
                    # CropCircle
                    self.logText.AppendText(('m;' + ts + ';'
                                            + str(someValue)[1:-1] + '\n'))
                    # for i in range(5):
                    #   self.axes[i].plot()
                else:
                    # GPS
                    self.logText.AppendText(('g;' + ts + ';'
                                            + str(someValue)[1:-1] + '\n'))
            else:
                # Ultrasonic
                self.logText.AppendText('u;'+ts+';'+str(someValue)+'\n')
        else:
            # None
            pass
