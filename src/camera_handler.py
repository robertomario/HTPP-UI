from datetime import datetime
import threading

import numpy as np
import cv2
import wx


class CameraHandler:
    def __init__(self, label, width=640, height=480, fps=15):
        self.label = label
        self.width = width
        self.height = height
        self.fps = fps
        self.is_recording = False
        self.reset()

    def connect(self, camera_index):
        name = (
            "data/HTPP" + datetime.now().strftime("%Y-%m-%d") + self.label[1] + ".mp4"
        )
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.out = cv2.VideoWriter(name, fourcc, self.fps, (self.width, self.height))

    def startRecording(self, new_thread=False):
        self.is_recording = True
        if new_thread and self.camera_thread is None:
            self.camera_thread = threading.Thread(target=self.preview, daemon=True)
            self.camera_thread.start()

    def preview(self):
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
        self.is_recording = False

    def disconnect(self):
        self.stopRecording()
        if self.cap is not None:
            self.cap.release()
        if self.out is not None:
            self.out.release()
        cv2.destroyAllWindows()
        if self.camera_thread is not None:
            self.camera_thread.join()
        self.reset()

    def getSize(self):
        return self.width, self.height

    def reset(self):
        self.cap = None
        self.out = None
        self.camera_thread = None

    @classmethod
    def findPorts(cls, initial_number=0, final_number=10):
        available_ports = []
        for i in range(initial_number, final_number):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                ret, frame = cap.read()
            except Exception as e:
                pass
            else:
                cap.release()
                if ret:
                    available_ports.append(i)
        return available_ports


class CameraPanel(wx.Panel):
    def __init__(self, parent, label):
        # Initialize panel
        wx.Panel.__init__(self, parent)
        # Attach CameraHandler
        self.camera = CameraHandler(label)
        # Bind event handlers
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_TIMER, self.NextFrame)
        # Define other attributes
        self.bmp = None

    def connect(self, camera_index):
        self.camera.connect(camera_index)
        ret, frame = self.camera.cap.read()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.bmp = wx.Bitmap.FromBuffer(self.camera.width, self.camera.height, frame)
        self.Refresh()
        self.timer.Start(1000.0 / self.camera.fps)

    def disconnect(self):
        self.timer.Stop()
        self.camera.disconnect()
        self.bmp = None

    def pauseRecording(self):
        self.camera.stopRecording()

    def resumeRecording(self):
        self.camera.startRecording()

    def getCapSize(self):
        return self.camera.getSize()

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        if self.bmp is not None:
            dc.DrawBitmap(self.bmp, 0, 0)

    def NextFrame(self, event):
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
    def __init__(self, parent, camera_ports):
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


if __name__ == "__main__":
    app = wx.App()
    frame = CameraFrame(None, [None, None])
    frame.Show()
    app.MainLoop()
