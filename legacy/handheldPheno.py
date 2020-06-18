# -*- coding: utf-8 -*-
"""
Created on Mon Jun 24 18:36:56 2019

@author: ROBERTO MARIO
"""
import os
import wx
import sys
import glob
import time
import serial
import os.path
import pynmea2
import datetime
import matplotlib as mpl
from threading import Timer
import wx.lib.agw.aui as aui
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

class PreferencesDialog(wx.Dialog):
    
    def __init__(self, settings, *args, **kw):
        super(PreferencesDialog, self).__init__(*args, **kw)
        self.settings=settings
        self.InitUI()
        self.SetSize((650, 300))
        self.SetTitle('Preferences')
        
        
    def InitUI(self):
        ports=['']+self.GetSerialPorts()
        
        pnl = wx.Panel(self)
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        vbox2 = wx.BoxSizer(wx.VERTICAL)
        
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        st1 = wx.StaticText(pnl, label='Multispectral', size=(120,30))
        hbox1.Add(st1, proportion=0, flag=wx.ALL)
        self.chb1=wx.CheckBox(pnl, label='Connected')
        hbox1.Add(self.chb1, proportion=1, flag=wx.ALL|wx.EXPAND)
        self.chb1.Bind(wx.EVT_CHECKBOX, self.OnChecked1)
        self.cb1=wx.ComboBox(pnl, choices=ports)
        hbox1.Add(self.cb1, proportion=1, flag=wx.ALL|wx.EXPAND)        
        
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        st2 = wx.StaticText(pnl, label='Ultrasonic', size=(120,30))
        hbox2.Add(st2, proportion=0, flag=wx.ALL)
        self.chb2=wx.CheckBox(pnl, label='Connected')
        hbox2.Add(self.chb2, proportion=1, flag=wx.ALL|wx.EXPAND)
        self.chb2.Bind(wx.EVT_CHECKBOX, self.OnChecked2)
        self.cb2=wx.ComboBox(pnl, choices=ports)
        hbox2.Add(self.cb2, proportion=1, flag=wx.ALL|wx.EXPAND)
        
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        st3 = wx.StaticText(pnl, label='GPS', size=(120,30))
        hbox3.Add(st3, proportion=0, flag=wx.ALL)
        self.chb3=wx.CheckBox(pnl, label='Connected')
        hbox3.Add(self.chb3, proportion=1, flag=wx.ALL|wx.EXPAND)
        self.chb3.Bind(wx.EVT_CHECKBOX, self.OnChecked3)
        self.cb3=wx.ComboBox(pnl, choices=ports)
        hbox3.Add(self.cb3, proportion=1, flag=wx.ALL|wx.EXPAND)
        
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
        
        vbox2.Add(hbox1, proportion=1, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM|wx.EXPAND, border=10)
        vbox2.Add(hbox2, proportion=1, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM|wx.EXPAND, border=10)
        vbox2.Add(hbox3, proportion=1, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM|wx.EXPAND, border=10)
        pnl.SetSizer(vbox2)
        
        vbox1.Add(pnl, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)
        vbox1.Add(hbox4, proportion=0, flag=wx.ALIGN_CENTER|wx.ALL, border=10)
        self.SetSizer(vbox1)
        
    def OnOK(self, e):
        self.settings.WriteBool('multispectralConnected', self.chb1.GetValue())
        self.settings.Write('multispectralPort', self.cb1.GetValue())
        self.settings.WriteBool('ultrasonicConnected', self.chb2.GetValue())
        self.settings.Write('ultrasonicPort', self.cb2.GetValue())
        self.settings.WriteBool('GPSConnected', self.chb3.GetValue())
        self.settings.Write('GPSPort', self.cb3.GetValue())
        self.EndModal(wx.ID_OK)
        #self.Destroy()
    
    def OnCancel(self, e):
        self.EndModal(wx.ID_CANCEL)
        #self.Destroy()
    
    def OnChecked1(self, e):
        chb=e.GetEventObject()
        if(chb.GetValue()):
            self.cb1.Enable(True)
        else:
            self.cb1.Enable(False)
    
    def OnChecked2(self, e):
        chb=e.GetEventObject()
        if(chb.GetValue()):
            self.cb2.Enable(True)
        else:
            self.cb2.Enable(False)
            
    def OnChecked3(self, e):
        chb=e.GetEventObject()
        if(chb.GetValue()):
            self.cb3.Enable(True)
        else:
            self.cb3.Enable(False)
            
    def GetSettings(self):
        return self.settings
    
    #https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    def GetSerialPorts(self, maxNum=20):
        """ Lists serial port names
    
            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(maxNum)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
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

class Plot(wx.Panel):
    def __init__(self, parent, id=-1, dpi=None, **kwargs):
        wx.Panel.__init__(self, parent, id=id, **kwargs)
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(2, 2))
        self.canvas = FigureCanvas(self, -1, self.figure)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(sizer)

class PlotNotebook(wx.Panel):
    def __init__(self, parent, id=-1):
        wx.Panel.__init__(self, parent, id=id)
        self.nb = aui.AuiNotebook(self)
        sizer = wx.BoxSizer()
        sizer.Add(self.nb, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def add(self, name="plot"):
        page = Plot(self.nb)
        self.nb.AddPage(page, name)
        return page.figure
    
class MainWindow(wx.Frame):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.cfg = wx.Config('HHPconfig')
        if not self.cfg.Exists('multispectralConnected'):
            self.cfg.WriteBool('multispectralConnected', False)
            self.cfg.Write('multispectralPort', '')
            self.cfg.WriteBool('ultrasonicConnected', False)
            self.cfg.Write('ultrasonicPort', '')
            self.cfg.WriteBool('GPSConnected', False)
            self.cfg.Write('GPSPort', '')
        self.variables=['NDRE','NDVI','Red-Edge','NIR','Red','Distance']
        self.numReadings=0
        self.lastRecord=[0]
        self.axes=[]
        self.InitUI()

    def InitUI(self):
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
        fileMenu.AppendItem(qmi)
        self.Bind(wx.EVT_MENU, self.OnQuit, qmi)
        menubar.Append(fileMenu, '&File')
        
        settingsMenu = wx.Menu()
        preferencesmi = wx.MenuItem(settingsMenu, wx.ID_PREFERENCES, '&Preferences')
        settingsMenu.AppendItem(preferencesmi)
        self.Bind(wx.EVT_MENU, self.OnPreferences, preferencesmi)
        menubar.Append(settingsMenu, '&Settings')
        
        helpMenu = wx.Menu()
        aboutmi = wx.MenuItem(helpMenu, wx.ID_ABOUT, '&About')
        helpMenu.AppendItem(aboutmi)
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
        mapPanel=Plot(backgroundPanel)
        self.mapAxes=mapPanel.figure.gca()
        st2 = wx.StaticText(backgroundPanel, label='Log:')
        self.logText = wx.TextCtrl(backgroundPanel, style=wx.TE_MULTILINE|wx.TE_READONLY)
        leftBox.Add(st1, proportion=0, flag=wx.ALL)
        leftBox.Add(mapPanel, wx.ID_ANY, wx.EXPAND | wx.ALL, 20)
        leftBox.Add(st2, proportion=0, flag=wx.ALL)
        leftBox.Add(self.logText, wx.ID_ANY, wx.EXPAND | wx.ALL, 20)
        
        middleBox = wx.BoxSizer(wx.VERTICAL)
        st3 = wx.StaticText(backgroundPanel, label='Plot:')
        plotter = PlotNotebook(backgroundPanel)
        for i in range(6):
            self.axes.append(plotter.add(self.variables[i]).gca())    
        middleBox.Add(st3, proportion=0, flag=wx.ALL)
        middleBox.Add(plotter, proportion=7, flag=wx.EXPAND | wx.ALL, border=20)
        
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
        outerBox.Add(middleBox, proportion=2, flag=wx.EXPAND | wx.ALL, border=20)
        outerBox.Add(rightBox, proportion=1, flag=wx.EXPAND | wx.ALL, border=20)
        backgroundPanel.SetSizer(outerBox)
        
        self.Maximize()
        self.SetTitle('HandHeld Plant Phenotyping')
        self.Centre()
        
        
    def OnNew(self, e):
        confirmationDiag=wx.MessageDialog(None, 'Are you sure you want to clear log?', 'Question', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        dialogFlag=confirmationDiag.ShowModal()
        print(dialogFlag)
        if(dialogFlag==wx.ID_YES):
            self.logText.SetValue('')
            self.numReadings=0
        #confirmationDiag.Destroy()
    
    def OnSave(self, e):
        rootName='HHPLogFile'+datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')+'X'
        i=1
        while(os.path.isfile(rootName+str(i)+'.txt')):
            i+=1
        finalFilename=rootName+str(i)+'.txt'
        self.logText.SaveFile(finalFilename)
        self.logText.SetValue('')
        self.numReadings=0
        
    def OnQuit(self, e):
        self.Close()
        
    def OnAbout(self, e):
        dial = wx.MessageBox(("HandHeld Plant Phenotyping \n"
                             "Made by Roberto Buelvas\n"
                             "McGill University, 2019\n"
                             "Version 0.02\n"),
                             'About', wx.OK | wx.ICON_INFORMATION)
        dial.Show()
    
    def OnPreferences(self, e):
        pDialog = PreferencesDialog(self.cfg, self)
        dialogFlag=pDialog.ShowModal()
        if(dialogFlag==wx.ID_OK):
            results=pDialog.GetSettings()
            self.cfg.WriteBool('multispectralConnected', results.ReadBool('multispectralConnected'))
            self.cfg.Write('multispectralPort', results.Read('multispectralPort'))
            self.cfg.WriteBool('ultrasonicConnected', results.ReadBool('ultrasonicConnected'))
            self.cfg.Write('ultrasonicPort', results.Read('ultrasonicPort'))
            self.cfg.WriteBool('GPSConnected', results.ReadBool('GPSConnected'))
            self.cfg.Write('GPSPort', results.Read('GPSPort'))
        pDialog.Destroy()
        
    def OnStart(self, e):
        self.rt = RepeatedTimer(1, self.sayHi)
    
    def OnMeasure(self, e):
        self.readAll()
            
    def OnErase(self, e):
        if(self.logText.GetValue()!=''):
            lastPosition=self.logText.GetLastPosition()
            self.logText.Remove(self.lastRecord[-1], lastPosition)
            if(len(self.lastRecord)>1):
                del self.lastRecord[-1]
        
    def OnStop(self, e):
        self.rt.stop()
    
    #for debugging the OnStart method
    def sayHi(self):
        self.logText.AppendText('Hi, Roberto \n')
    
    def readAll(self):
        connected=[self.cfg.ReadBool('multispectralConnected'),self.cfg.ReadBool('ultrasonicConnected'),self.cfg.ReadBool('GPSConnected')]
        if(any(connected)):
            self.lastRecord.append(self.logText.GetLastPosition())
            self.logText.AppendText('*****'+str(self.numReadings)+'*****\n')
            if(connected[0]):
                mr=self.getMultispectralReading()
                self.updateUI(mr)
            if(connected[1]):        
                ur=self.getUltrasonicReading()
                self.updateUI(ur)
            if(connected[2]):        
                gr=self.getGPSReading()
                self.updateUI(gr)
                #updateMap(gr)
            self.numReadings+=1
            
    def getMultispectralReading(self, numValues=10):
        port=self.cfg.Read('multispectralPort')
        print(port)
        serialCropCircle=serial.Serial(port,38400)
        ndre=[]
        ndvi=[]
        redEdge=[]
        nir=[]
        red=[]
        for i in range(numValues):
            message=serialCropCircle.readline().strip().decode()
            measurements=message.split(',')
            measurements=[float(i) for i in measurements]
            ndre.append(measurements[0])
            ndvi.append(measurements[1])
            redEdge.append(measurements[2])
            nir.append(measurements[3])
            red.append(measurements[4])
        finalMeasurement=[sum(ndre),sum(ndvi),sum(redEdge),sum(nir),sum(red)]
        finalMeasurement=[i/numValues for i in finalMeasurement]            
        serialCropCircle.close()
        print(finalMeasurement)
        return finalMeasurement
        
    def getUltrasonicReading(self, numValues=10):
        serialUltrasonic=serial.Serial(self.cfg.Read('ultrasonicPort'),38400)
        count=-1
        finalMeasurement=0
        index=0
        message=b''
        charList=[b'0',b'0',b'0',b'0',b'0']
        while(count<numValues):
            newChar=serialUltrasonic.read()
            if(newChar==b'\r'):
                count+=1
                message=b''.join(charList)
                measurement=0.003384*25.4*int(message)
                finalMeasurement+=measurement
                message=b''
                index=0
            else:
                charList[index]=newChar
                index+=1
                if(index>5):
                    index=0
        serialUltrasonic.close()
        return finalMeasurement/numValues            
        
    def getGPSReading(self, numValues=5):
        serialGPS=serial.Serial(self.cfg.Read('GPSPort'),9600)
        i=0
        while(i<numValues):
            message=serialGPS.readline().strip().decode()
            if(message[0:6]=='$GPGGA' or message[0:6]=='$GPGLL'):
                i+=1
                parsedMessage=pynmea2.parse(message)
                finalMeasurement=[parsedMessage.longitude, parsedMessage.latitude]
        serialGPS.close()
        return finalMeasurement
        
    def updateUI(self, someValue):
        if(someValue!=None):
            ts = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            if(isinstance(someValue, list)):
                if(len(someValue)>=5):
                    #cropCircle
                    self.logText.AppendText('m;'+ts+';'+str(someValue)[1:-1]+'\n')
                    #for i in range(5):
                        #self.axes[i].plot()
                else:
                    #gps
                    self.logText.AppendText('g;'+ts+';'+str(someValue)[1:-1]+'\n')
            else:
                #ultrasonic
                self.logText.AppendText('u;'+ts+';'+str(someValue)+'\n')
        else:
            #None
            pass
    
def main():
    app = wx.App()
    ex = MainWindow(None)
    ex.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()