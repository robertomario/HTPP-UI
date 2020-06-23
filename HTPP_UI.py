#!/usr/bin/env python
""" Start the UI app by calling the main window """

# Author: Roberto Buelvas

import wx

from src.main_window import MainWindow

if __name__ == '__main__':
    try:
        app = wx.App()
        mw = MainWindow(None)
        mw.Show()
        app.MainLoop()
    except Exception as e:
        print(str(e))
    finally:
        mw.disconnect()
