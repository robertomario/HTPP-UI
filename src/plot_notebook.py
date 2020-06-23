""" Create tabs with multiple plots """

# Author: Roberto Buelvas

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.lines import Line2D
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

    def refresh(self):
        self.canvas.draw_idle()

    def clear(self):
        self.figure.gca().cla()


class PlotNotebook(wx.Panel):
    """ Class to put together multiple plots in wx """

    def __init__(self, parent, id=-1):
        """ Create new notebook with one empty tab """
        wx.Panel.__init__(self, parent, id=id)
        # mpl.use('WxAgg')
        self.nb = aui.AuiNotebook(self, agwStyle=aui.AUI_NB_WINDOWLIST_BUTTON
                                  | aui.AUI_NB_SCROLL_BUTTONS)
        sizer = wx.BoxSizer()
        sizer.Add(self.nb, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def add(self, name, device_name, scaling, num_sensors):
        """ Add plot in new tab """
        page = Plot(self.nb)
        self.nb.AddPage(page, name)
        ax = page.figure.add_axes([0.1, 0.1, 0.7, 0.85])
        if(scaling):
            legend_elements_L = [Line2D([0], [0], marker='o',
                                        color='C' + str(i),
                                        label=device_name + 'L' + str(i),
                                        markerfacecolor='C' + str(i))
                                 for i in range(num_sensors)]
            legend_elements_R = [Line2D([0], [0], marker='o',
                                        color='C' + str(num_sensors + i),
                                        label=device_name + 'R' + str(i),
                                        markerfacecolor='C' + str(num_sensors
                                                                  + i))
                                 for i in range(num_sensors)]
            legend_elements = legend_elements_L + legend_elements_R
        else:
            legend_elements = [Line2D([0], [0], marker='o', color='C0',
                                      label=device_name + 'L',
                                      markerfacecolor='C0'),
                               Line2D([0], [0], marker='o', color='C1',
                                      label=device_name + 'R',
                                      markerfacecolor='C1')]
        ax.legend(handles=legend_elements, loc='upper left',
                  bbox_to_anchor=(1.04, 1))
        return ax

    def refresh(self):
        """ Redraw all plots """
        for i in range(self.nb.GetPageCount()):
            page = self.nb.GetPage(i)
            page.refresh()

    def clear(self):
        for i in range(self.nb.GetPageCount()):
            page = self.nb.GetPage(i)
            page.clear()
            page.refresh()
