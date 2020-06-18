""" Create tabs with multiple plots """

# Author: Roberto Buelvas

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
import wx.lib.agw.aui as aui
import matplotlib as mpl
import wx


class Plot(wx.Panel):
    """ Class to display a plot in wx """

    def __init__(self, parent, id=-1, dpi=None, **kwargs):
        """ Create empty plot """
        wx.Panel.__init__(self, parent, id=id, **kwargs)
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(2, 2))
        self.canvas = FigureCanvas(self, -1, self.figure)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(sizer)


class PlotNotebook(wx.Panel):
    """ Class to put together multiple plots in wx """

    def __init__(self, parent, id=-1):
        """ Create new notebook with one empty tab """
        wx.Panel.__init__(self, parent, id=id)
        self.nb = aui.AuiNotebook(self)
        sizer = wx.BoxSizer()
        sizer.Add(self.nb, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def add(self, name="plot"):
        """ Add plot in new tab """
        page = Plot(self.nb)
        self.nb.AddPage(page, name)
        return page.figure
