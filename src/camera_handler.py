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
    def __init__(self, parent):
        wx.Frame.__init__(self, parent=parent, title="Camera frame")
        mainPanel = wx.Panel(self)
        outerBox = wx.BoxSizer(wx.VERTICAL)
        upBox = wx.BoxSizer(wx.HORIZONTAL)
        self.camL = CameraPanel(mainPanel, "cL")
        self.camR = CameraPanel(mainPanel, "cR")
        cam_width, cam_height = self.camL.camera.getSize()
        self.camL.SetSize(cam_width, cam_height)
        self.camR.SetSize(cam_width, cam_height)
        upBox.Add(self.camL, proportion=1, flag=wx.EXPAND)
        upBox.Add(self.camR, proportion=1, flag=wx.EXPAND)
        downBox = wx.BoxSizer(wx.HORIZONTAL)
        connect_btn = wx.Button(mainPanel, label="Connect")
        connect_btn.Bind(wx.EVT_BUTTON, self.OnConnect)
        disconnect_btn = wx.Button(mainPanel, label="Disconnect")
        disconnect_btn.Bind(wx.EVT_BUTTON, self.OnDisconnect)
        pause_btn = wx.Button(mainPanel, label="Pause")
        pause_btn.Bind(wx.EVT_BUTTON, self.OnPause)
        resume_btn = wx.Button(mainPanel, label="Resume")
        resume_btn.Bind(wx.EVT_BUTTON, self.OnResume)
        downBox.Add(connect_btn, proportion=0)
        downBox.Add(disconnect_btn, proportion=0)
        downBox.Add(pause_btn, proportion=0)
        downBox.Add(resume_btn, proportion=0)
        outerBox.Add(upBox, proportion=1, flag=wx.EXPAND)
        outerBox.Add(downBox, proportion=0, flag=wx.ALIGN_CENTER)
        mainPanel.SetSizer(outerBox)
        self.SetSize(2 * cam_width + 15, cam_height + 70)

    def OnConnect(self, event):
        self.camL.connect(0)
        self.camR.connect(1)

    def OnDisconnect(self, event):
        self.camL.disconnect()
        self.camR.disconnect()

    def OnPause(self, event):
        self.camL.pauseRecording()
        self.camR.pauseRecording()

    def OnResume(self, event):
        self.camL.resumeRecording()
        self.camR.resumeRecording()


if __name__ == "__main__":
    app = wx.App()
    frame = CameraFrame(None)
    frame.Show()
    app.MainLoop()
