""" Create tabs with multiple plots """

# Author: Roberto Buelvas

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.lines import Line2D
import wx.lib.agw.aui as aui
import matplotlib as mpl
import numpy as np
import wx


class Map(wx.Panel):
    """ Class to display map in wx from GPS readings 
    
    Attr:
        figure (mpl.figure.Figure): Figure that displays plots
        ax (mpl.axes.Axes): Axes inside figure
        canvas (FigureCanvasWxAgg): Canvas where the figure paints
        point_len (int): Maximum number of points to display at a time
        lines (list<list<mpl.lines.Line2D>>): In each iteration, multiple lines are added:
            some for the vehicle and some others for each sensor. This list of lists
            keeps track of them to be able to delete them later
    """

    def __init__(self, parent, id=-1, point_len=20, dpi=None, **kwargs):
        """ Create empty plot in panel 
        Args:
            parent (wx.Window): Parent object for the panel
            id (int): ID for the panel. -1 takes a random free id.
            point_len (int): Initial values of the point_len attribute
            dpi (int or None): Resolution in dots per inch. None uses a default that
                that seems to be close to 100
        """
        wx.Panel.__init__(self, parent, id=id, **kwargs)
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(2, 2))
        self.ax = self.figure.gca()
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.point_len = point_len
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.clear()

    def refresh(self, line_list):
        """ Tell the Plot to actually implement the latest
            modifications

        line and old_line_list are emptied in the end to make sure no reference remains
        to the line objects and the garbage collector actually removes them

        Documentation for this backend is kinda poor, but basically whenever
        something important needs to be done, it will only work if called from
        the FigureCanvas, not the Figure
        """
        if line_list != []:
            self.lines.append(line_list)
        if len(self.lines) > self.point_len:
            old_line_list = self.lines.pop(0)
            for line in old_line_list:
                self.ax.lines.remove(line)
            line = None
            old_line_list = []
            self.updateLimits()
        self.canvas.draw_idle()

    def clear(self):
        """ Clear the Axes of the Figure """
        self.lines = []
        self.figure.gca().cla()

    def updateLimits(self):
        """ Find the limits of the data to adjust axes """
        x_values = []
        y_values = []
        for line_list in self.lines:
            x_values.append(line_list[0].get_xdata()[0])
            y_values.append(line_list[0].get_ydata()[0])
        min_x = min(x_values) - 1
        max_x = max(x_values) + 1
        min_y = min(y_values) - 1
        max_y = max(y_values) + 1
        self.ax.set_xlim(min_x, max_x)
        self.ax.set_ylim(min_y, max_y)


class Plot(wx.Panel):
    """ Class to display a plot in wx 
        figure (mpl.figure.Figure): Figure that displays plots
        ax (mpl.axes.Axes): Axes inside figure
        canvas (FigureCanvasWxAgg): Canvas where the figure paints
        x_len (int): Maximum number of points to display at a time
        background (BufferRegion): Empty background to leverage blitting
        lines (list<mpl.lines.Line2D>): Each sensor of the same type has a line in this
            list. Used to update them later with different data
    """

    def __init__(self, parent, x_len, id=-1, dpi=100, **kwargs):
        """ Create empty plot """
        wx.Panel.__init__(self, parent, id=id, **kwargs)
        self.x_len = x_len
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(6.5, 6.5))
        self.ax = self.figure.add_axes([0.1, 0.1, 0.7, 0.85])
        self.ax.set_xlim(0, self.x_len)
        self.ax.autoscale(enable=True, axis="y", tight=True)
        self.canvas = FigureCanvas(self, -1, self.figure)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 0, wx.ALL)
        self.SetSizer(sizer)
        self.Fit()
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        self.lines = []

    def updateLines(self, plot_data):
        """ Redefine lines attribute as response to change in notebook """
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
                )[0]
            )
        self.redoLegend(plot_data)

    def refresh(self, plot_data):
        """ Tell the Plot to actually implement the latest
            modifications

        Use canvas.blit() instead of canvas.draw_idle() to save time

        Documentation for this backend is kinda poor, but basically whenever
        something important needs to be done, it will only work if called from
        the FigureCanvas, not the Figure
        """
        self.canvas.restore_region(self.background)
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
    """ Wrapper for y-data of each plots
    
    Instead of having multiple plots, this class holds the information that would be in
    each and just the one that is active is displayed. It also handles trimming the values
    to be of fixed length

    Attr:
        x_len (int): Maximum number of points to display at a time
        sensor_type (str): Initial letter of the sensor, like in the keys of variables
            dict
        scaling (bool): Indicate if there are multiple or only one sensor of its type on
            each side of the vehicle
        num_sensors (int): In case of scaling being True, the number of sensors of its
            type on each side of the vehicle
        data (np.ndarray): Array holding the latest x_len readings for a specific variable
            for all sensors of its type
    """

    def __init__(self, x_len, sensor_type, scaling, num_sensors):
        """ Initialize attributes """
        self.x_len = x_len
        self.sensor_type = sensor_type
        self.scaling = scaling
        self.reset(num_sensors)

    def updateData(self, someValue, label):
        """ Update data attribute with a specific sensor reading """
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
        """ Reset data attribute """
        self.num_sensors = num_sensors
        if self.scaling:
            self.data = -1 * np.ones((2 * self.num_sensors, self.x_len))
        else:
            self.data = -1 * np.ones((2, self.x_len))


class PlotNotebook(wx.Panel):
    """ Put together a plot in wx with a notebook to control it 
    
    The notebook selects which PlotData is directed to the Plot frame

    Attr:
        x_len (int): Maximum number of points to display at a time
        nb (aui.AuiNotebook): Control with tabs
        plot (Plot): Custom panel where plot is displayed
        plot_data (dict<str: PlotData>): Dict to hold all PlotData objects. Keys are the
            measured properties like "NDVI" or "Velocity"
    """

    def __init__(self, parent, id=-1, x_len=20):
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
        """ Modify a specific entry of plot_data
        
        If it is the currently active page, also display the plot
        This is the function called by updatePlot in main_window
        """
        page_name = self.nb.GetPageText(self.nb.GetSelection())
        self.plot_data[measured_property].updateData(some_value, label)
        if measured_property == page_name:
            self.plot.refresh(self.plot_data[page_name])

    def reset(self, num_sensors):
        """ Reset data of all PlotData objects """
        for plot_data in self.plot_data.values():
            plot_data.reset(num_sensors)
        page_name = self.nb.GetPageText(self.nb.GetSelection())
        self.plot.refresh(self.plot_data[page_name])

    def OnPageChange(self, e):
        """ Response to change on pages in the TabControl """
        page_name = self.nb.GetPageText(self.nb.GetSelection())
        self.plot.updateLines(self.plot_data[page_name])
        self.plot.refresh(self.plot_data[page_name])
