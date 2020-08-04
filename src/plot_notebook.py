""" Create tabs with multiple plots """

# Author: Roberto Buelvas

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.lines import Line2D
import wx.lib.agw.aui as aui
import matplotlib as mpl
import numpy as np
import wx


class Map(wx.Panel):
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
        """ Function to tell the Plot to actually implement the latest
            modifications

        Documentation for this backend is kinda poor, but basically whenever
        something important needs to be done, it will only work if called from
        the FigureCanvas, not the Figure
        """
        self.canvas.draw_idle()

    def clear(self):
        """ Function to clear the Axes of the Figure """
        self.figure.gca().cla()


class Plot(wx.Panel):
    """ Class to display a plot in wx """

    def __init__(self, parent, x_len, id=-1, dpi=100, **kwargs):
        """ Create empty plot """
        wx.Panel.__init__(self, parent, id=id, **kwargs)
        self.x_len = x_len
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(6.5, 6.5))
        self.ax = self.figure.add_axes([0.1, 0.1, 0.7, 0.85])
        self.ax.set_xlim(0, self.x_len)
        self.canvas = FigureCanvas(self, -1, self.figure)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 0, wx.ALL)
        self.SetSizer(sizer)
        self.Fit()
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        self.lines = []

    def updateLines(self, plot_data):
        self.clear()
        self.lines = []
        for i in range(plot_data.data.shape[0]):
            self.lines.append(
                self.ax.plot(
                    range(self.x_len),
                    plot_data.data[i, :],
                    marker="o",
                    color="C" + str(i),
                    markerfacecolor="C" + str(i),
                    animated=True,
                )[0]
            )
        self.redoLegend(plot_data)
        self.updateYLim(plot_data)

    def updateYLim(self, plot_data):
        limits_change = False
        current_max = np.max(plot_data.data)
        current_min = np.min(plot_data.data)
        if current_max > plot_data.max_data:
            plot_data.max_data = current_max
            limits_change = True
        if current_min < plot_data.min_data:
            plot_data.min_data = current_min
            limits_change = True
        if limits_change:
            self.ax.set_ylim(plot_data.min_data, plot_data.max_data)
            self.canvas.draw_idle()

    def refresh(self, plot_data):
        """ Function to tell the Plot to actually implement the latest
            modifications

        Documentation for this backend is kinda poor, but basically whenever
        something important needs to be done, it will only work if called from
        the FigureCanvas, not the Figure
        """
        self.canvas.restore_region(self.background)
        self.updateYLim(plot_data)
        for line, data in zip(self.lines, plot_data.data):
            line.set_ydata(data)
            self.ax.add_line(line)
            self.ax.draw_artist(line)
        self.canvas.blit(self.ax.bbox)

    def clear(self):
        """ Function to clear the Axes of the Figure """
        self.ax.cla()
        self.canvas.draw_idle()

    def redoLegend(self, plot_data):
        """ Remove legend and create a new one

        Used when the number of sensors changes (from Ports dialog)
        """
        legend = self.ax.get_legend()
        if legend is not None:
            legend.remove()
        self.addCustomLegend(plot_data)

    def addCustomLegend(self, plot_data):
        """ Create legend for each variable

        Legend elements are defined for as many sensors as there are.
        The colors are given with the C0, C1, etc format, which allows to
        cycle. I suspect the current colormap goes up to 10 before repeating
        itself.
        The label is in the form of mL1, gR, etc.
        The legend will appear to the right of the Axes, outside the box,
        aligned with its top.
        """
        if plot_data.scaling:
            legend_elements_L = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="C" + str(i),
                    label=plot_data.sensor_type + "L" + str(i + 1),
                    markerfacecolor="C" + str(i),
                )
                for i in range(plot_data.num_sensors)
            ]
            legend_elements_R = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="C" + str(plot_data.num_sensors + i),
                    label=plot_data.sensor_type + "R" + str(i + 1),
                    markerfacecolor="C" + str(plot_data.num_sensors + i),
                )
                for i in range(plot_data.num_sensors)
            ]
            legend_elements = legend_elements_L + legend_elements_R
        else:
            legend_elements = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="C0",
                    label=plot_data.sensor_type + "L",
                    markerfacecolor="C0",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="C1",
                    label=plot_data.sensor_type + "R",
                    markerfacecolor="C1",
                ),
            ]
        self.ax.legend(
            handles=legend_elements, loc="upper left", bbox_to_anchor=(1.04, 1)
        )


class PlotData:
    def __init__(self, x_len, sensor_type, scaling, num_sensors):
        self.x_len = x_len
        self.sensor_type = sensor_type
        self.scaling = scaling
        self.reset(num_sensors)

    def updateData(self, someValue, label):
        if self.scaling:
            index = int(label[2]) - 1
            if label[1] == "R":
                index += self.num_sensors
        else:
            if label[1] == "L":
                index = 0
            else:
                index = 1
        self.data[index, :-1] = self.data[index, 1:]
        if np.isnan(someValue):
            self.data[index, -1] = -1
        else:
            self.data[index, -1] = someValue

    def reset(self, num_sensors):
        self.num_sensors = num_sensors
        if self.scaling:
            self.data = -1 * np.ones((2 * self.num_sensors, self.x_len))
        else:
            self.data = -1 * np.ones((2, self.x_len))
        self.min_data = 0
        self.max_data = 1


class PlotNotebook(wx.Panel):
    """ Class to put together multiple plots in wx """

    def __init__(self, parent, id=-1, x_len=30):
        """ Create new notebook with one empty tab """
        wx.Panel.__init__(self, parent, id=id)
        self.x_len = x_len
        self.nb = aui.AuiNotebook(
            self, agwStyle=aui.AUI_NB_WINDOWLIST_BUTTON | aui.AUI_NB_SCROLL_BUTTONS
        )
        self.plot = Plot(self, self.x_len)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.nb, 1, wx.EXPAND)
        sizer.Add(self.plot, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.plot_data = {}
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnPageChange)

    def add(self, name, device_name, scaling, num_sensors):
        """ Add plot in new tab """
        page = wx.Panel(self)
        self.plot_data[name] = PlotData(self.x_len, device_name, scaling, num_sensors)
        self.nb.AddPage(page, name, select=True)

    def update(self, some_value, label, measured_property):
        page_name = self.nb.GetPageText(self.nb.GetSelection())
        self.plot_data[measured_property].updateData(some_value, label)
        if measured_property == page_name:
            self.plot.refresh(self.plot_data[page_name])

    def reset(self, num_sensors):
        for plot_data in self.plot_data.values():
            plot_data.reset(num_sensors)
        page_name = self.nb.GetPageText(self.nb.GetSelection())
        self.plot.refresh(self.plot_data[page_name])

    def OnPageChange(self, e):
        page_name = self.nb.GetPageText(self.nb.GetSelection())
        self.plot.updateLines(self.plot_data[page_name])
        self.plot.refresh(self.plot_data[page_name])
