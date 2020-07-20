""" Define how to use cameras """

# Author: Roberto Buelvas

from datetime import datetime
import threading
import os

import numpy as np
import cv2
import wx


class CameraHandler:
    """ Class to use cameras

    This class follows the structure of OpenCV examples

    Attr:
        label (str): Label of the format cL or cR
        width (int): Width in pixels of pictures taken by camera
        height (int): Heigt in pixels of pictures taken by camera
        fps (float): Frames per second taken by camera
        is_recording (boolean): Flag to indicate if current frame should be stored as
            video file. If False, the video is just displayed
        cap (cv2.VideoCapture): Device that actually reads the video
        out (cv2.VideoWriter): Object that saves frames into video file
        camera_thread (threading.Thread): Creates new thread to focus on cameras only
    """

    def __init__(self, label, width=640, height=480, fps=15):
        """ Initialize constant attributes """
        self.label = label
        self.width = width
        self.height = height
        self.fps = fps
        self.is_recording = False
        self.reset()

    def connect(self, camera_index):
        """ Define cap and out attributes """
        root_name = "data/HTPP" + datetime.now().strftime("%Y-%m-%d") + self.label[1]
        i = 1
        while os.path.isfile(root_name + str(i) + ".mp4"):
            i += 1
        final_name = root_name + str(i) + ".mp4"
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.out = cv2.VideoWriter(
            final_name, fourcc, self.fps, (self.width, self.height)
        )

    def startRecording(self, new_thread=False):
        """ 
        If new_thread is True, create a new thread (assuming a previous one doesn't
        exist already) and start its operation. If False, just set is_recording flag to
        True 
        """
        self.is_recording = True
        if new_thread and self.camera_thread is None:
            self.camera_thread = threading.Thread(target=self.preview, daemon=True)
            self.camera_thread.start()

    def preview(self):
        """ Use cv2.imshow() to display video from cameras
        
        When is_recording is True, store video as video file. Add timestamp to it.
        Used for debugging
        """
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1).copy()
                timestamp = datetime.now().strftime("%H:%M:%S")
                timed_frame = frame.copy()
                if self.is_recording:
                    cv2.putText(
                        timed_frame,
                        timestamp,
                        (0, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255, 255, 255),
                        3,
                        cv2.LINE_AA,
                        False,
                    )
                    self.out.write(timed_frame)
                    cv2.putText(
                        frame,
                        "Recording",
                        (450, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255, 255, 255),
                        3,
                        cv2.LINE_AA,
                        False,
                    )
                cv2.imshow(self.label, frame)
                if cv2.waitKey(1) == ord("q"):
                    break
            else:
                break

    def stopRecording(self):
        """ Video is no longer saved in file, but it is still displayed """
        self.is_recording = False

    def disconnect(self):
        """ Release and destroy cap, out and camera_thread attributes """
        self.stopRecording()
        if self.cap is not None:
            self.cap.release()
        if self.out is not None:
            self.out.release()
        cv2.destroyAllWindows()
        if self.camera_thread is not None:
            self.camera_thread.join()
        self.reset()

    def reset(self):
        """ Set attributes to None to be ready to redefine them """
        self.cap = None
        self.out = None
        self.camera_thread = None


class CameraPanel(wx.Panel):
    """ Embed CameraHandler object into a wx.Panel
    
    Attr:
        camera (CameraHandler): Camera object to embed
        timer (wx.Timer): Used to update frames periodically
        bmp (wx.Bitmap): Actual image displayed on panel
    """

    def __init__(self, parent, label):
        """ Initialize attributes """
        wx.Panel.__init__(self, parent)
        self.camera = CameraHandler(label)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_TIMER, self.NextFrame)
        self.bmp = None

    def connect(self, camera_index):
        """ Connect camera handler
        
        Get a first frame and populate bmp based on it
        Start timer
        """
        self.camera.connect(camera_index)
        ret, frame = self.camera.cap.read()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.bmp = wx.Bitmap.FromBuffer(self.camera.width, self.camera.height, frame)
        self.Refresh()
        self.timer.Start(1000.0 / self.camera.fps)

    def disconnect(self):
        """ Stop video """
        self.timer.Stop()
        self.camera.disconnect()
        self.bmp = None

    def pauseRecording(self):
        """ Video is no longer saved as video file, but it is still displayed """
        self.camera.stopRecording()

    def resumeRecording(self):
        """ (Re)starts saving video as file """
        self.camera.startRecording()

    def OnPaint(self, event):
        """ Responds to Refresh() by updating bmp """
        dc = wx.BufferedPaintDC(self)
        if self.bmp is not None:
            dc.DrawBitmap(self.bmp, 0, 0)

    def NextFrame(self, event):
        """ Responds to timer by getting next frame """
        if self.camera.cap.isOpened():
            ret, frame = self.camera.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                timestamp = datetime.now().strftime("%H:%M:%S")
                timed_frame = frame.copy()
                if self.camera.is_recording:
                    cv2.putText(
                        timed_frame,
                        timestamp,
                        (0, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255, 255, 255),
                        3,
                        cv2.LINE_AA,
                        False,
                    )
                    self.camera.out.write(timed_frame)
                    cv2.putText(
                        frame,
                        "Recording",
                        (450, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255, 255, 255),
                        3,
                        cv2.LINE_AA,
                        False,
                    )
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.bmp.CopyFromBuffer(frame)
                self.Refresh()


class CameraFrame(wx.Frame):
    """ Combine 2 CameraPanel side by side for left and right camera
    
    Add 2 ToggleButton for connect/disconnect and record/pause
    Attr:
        camera_ports (list): List of length 2 to indicate which camera to use for which
            side. If any side doesn't have any camera, use None
        camL (CameraPanel): Panel showing video from left camera
        camR (CameraPanel): Panel showing video from right camera
    """

    def __init__(self, parent, camera_ports):
        """ Define attributes
        
        Destroy itself if no camera ports are available
        """
        wx.Frame.__init__(self, parent=parent, title="Camera frame")
        if (camera_ports[0] is not None) or (camera_ports[1] is not None):
            self.camera_ports = camera_ports
            self.InitUI(parent)
        else:
            wx.MessageBox(
                ("No camera ports have been defined \n" + "Camera frame will close"),
                "Warning",
                wx.OK | wx.ICON_ERROR,
            )
            self.DestroyLater()

    def InitUI(self, parent):
        """ Populate frame with elements """
        mainPanel = wx.Panel(self)
        outerBox = wx.BoxSizer(wx.VERTICAL)
        upBox = wx.BoxSizer(wx.HORIZONTAL)
        if self.camera_ports[0] is not None:
            self.camL = CameraPanel(mainPanel, "cL")
            upBox.Add(self.camL, proportion=1, flag=wx.EXPAND)
            cam_width = self.camL.camera.width
            cam_height = self.camL.camera.height
        else:
            self.camL = None
            st = wx.StaticText(
                mainPanel,
                label="Undefined port for left camera",
                style=wx.ALIGN_CENTER_HORIZONTAL,
            )
            upBox.Add(st, proportion=1, flag=wx.EXPAND)
        if self.camera_ports[1] is not None:
            self.camR = CameraPanel(mainPanel, "cR")
            upBox.Add(self.camR, proportion=1, flag=wx.EXPAND)
            cam_width = self.camR.camera.width
            cam_height = self.camR.camera.height
        else:
            self.camR = None
            st = wx.StaticText(
                mainPanel,
                label="Undefined port for right camera",
                style=wx.ALIGN_CENTER_HORIZONTAL,
            )
            upBox.Add(st, proportion=1, flag=wx.EXPAND)
        downBox = wx.BoxSizer(wx.HORIZONTAL)
        connect_btn = wx.ToggleButton(mainPanel, label="Connect")
        connect_btn.Bind(wx.EVT_TOGGLEBUTTON, self.OnConnect)
        record_btn = wx.ToggleButton(mainPanel, label="Record")
        record_btn.Bind(wx.EVT_TOGGLEBUTTON, self.OnResume)
        downBox.Add(connect_btn, proportion=0)
        downBox.Add(record_btn, proportion=0)
        outerBox.Add(upBox, proportion=1, flag=wx.EXPAND)
        outerBox.Add(downBox, proportion=0, flag=wx.ALIGN_CENTER)
        mainPanel.SetSizer(outerBox)
        self.SetSize(2 * cam_width + 15, cam_height + 70)
        self.Center()

    def OnConnect(self, event):
        """ Define response to connect/disconnect toggle button """
        btn = event.GetEventObject()
        is_pressed = btn.GetValue()
        if is_pressed:
            btn.SetLabelText("Disconnect")
            if self.camL is not None:
                self.camL.connect(self.camera_ports[0])
            if self.camR is not None:
                self.camR.connect(self.camera_ports[1])
        else:
            btn.SetLabelText("Connect")
            if self.camL is not None:
                self.camL.disconnect()
            if self.camR is not None:
                self.camR.disconnect()

    def OnResume(self, event):
        """ Define response to resume/pause toggle button """
        btn = event.GetEventObject()
        is_pressed = btn.GetValue()
        if is_pressed:
            btn.SetLabelText("Pause")
            if self.camL is not None:
                self.camL.resumeRecording()
            if self.camR is not None:
                self.camR.resumeRecording()
        else:
            btn.SetLabelText("Record")
            if self.camL is not None:
                self.camL.pauseRecording()
            if self.camR is not None:
                self.camR.pauseRecording()

    def close(self):
        """ Safely close frame by disconnecting from cameras first """
        if self.camL is not None:
            self.camL.pauseRecording()
            self.camL.disconnect()
        if self.camR is not None:
            self.camR.pauseRecording()
            self.camR.disconnect()
        self.Destroy()


# For debugging
if __name__ == "__main__":
    app = wx.App()
    frame = CameraFrame(None, [0, 1])
    frame.Show()
    app.MainLoop()
