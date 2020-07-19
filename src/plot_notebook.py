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

    def redoLegend(self, device_name, scaling, num_sensors):
        """ Remove legend and create a new one

        Used when the number of sensors changes (from Ports dialog)
        """
        ax = self.figure.gca()
        legend = ax.get_legend()
        if legend is not None:
            legend.remove()
        self.addCustomLegend(device_name, scaling, num_sensors)

    def addCustomLegend(self, device_name, scaling, num_sensors):
        """ Create legend for each variable

        Legend elements are defined for as many sensors as there are.
        The colors are given with the C0, C1, etc format, which allows to
        cycle. I suspect the current colormap goes up to 10 before repeating
        itself.
        The label is in the form of mL1, gR, etc.
        The legend will appear to the right of the Axes, outside the box,
        aligned with its top.
        """
        ax = self.figure.gca()
        if scaling:
            legend_elements_L = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="C" + str(i),
                    label=device_name + "L" + str(i + 1),
                    markerfacecolor="C" + str(i),
                )
                for i in range(num_sensors)
            ]
            legend_elements_R = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="C" + str(num_sensors + i),
                    label=device_name + "R" + str(i + 1),
                    markerfacecolor="C" + str(num_sensors + i),
                )
                for i in range(num_sensors)
            ]
            legend_elements = legend_elements_L + legend_elements_R
        else:
            legend_elements = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="C0",
                    label=device_name + "L",
                    markerfacecolor="C0",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="C1",
                    label=device_name + "R",
                    markerfacecolor="C1",
                ),
            ]
        ax.legend(handles=legend_elements, loc="upper left", bbox_to_anchor=(1.04, 1))


class PlotNotebook(wx.Panel):
    """ Class to put together multiple plots in wx """

    def __init__(self, parent, id=-1):
        """ Create new notebook with one empty tab """
        wx.Panel.__init__(self, parent, id=id)
        self.nb = aui.AuiNotebook(
            self, agwStyle=aui.AUI_NB_WINDOWLIST_BUTTON | aui.AUI_NB_SCROLL_BUTTONS
        )
        sizer = wx.BoxSizer()
        sizer.Add(self.nb, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def add(self, name, device_name, scaling, num_sensors):
        """ Add plot in new tab """
        page = Plot(self.nb)
        self.nb.AddPage(page, name)
        ax = page.figure.add_axes([0.1, 0.1, 0.7, 0.85])
        page.addCustomLegend(device_name, scaling, num_sensors)
        return ax

    def refresh(self):
        """ Redraw all plots """
        for i in range(self.nb.GetPageCount()):
            page = self.nb.GetPage(i)
            page.refresh()

    def clear(self):
        """ Clear all plots """
        for i in range(self.nb.GetPageCount()):
            page = self.nb.GetPage(i)
            page.clear()

    def redoLegend(self, variables, devices, num_sensors):
        """ Redo legends for all plots

        Args:
            variables (dict): Connects sensors with the variables they measure
            devices (dict): Connects sensors with their full names and how they
                            scale
            num_sensors (int): Number of scaling sensors on each side of the
                               platform as defined in the Ports dialog
        This loop leverages that the same order was used when originally
        populating the notebook with pages.
        Still, I suspect there is an easier way to do it.
        """
        i = 0
        for device_name in list(variables.keys()):
            variable_names = variables[device_name]
            scaling = devices[device_name][1]
            for name in variable_names:
                page = self.nb.GetPage(i)
                page.redoLegend(device_name, scaling, num_sensors)
                page.refresh()
                i += 1
