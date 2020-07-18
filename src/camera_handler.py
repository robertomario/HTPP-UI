from datetime import datetime
import threading

import numpy as np
import cv2


class CameraHandler:
    def __init__(self, label, width=640, height=480, fps=30):
        self.label = label
        self.width = width
        self.height = height
        self.fps = fps
        self.resetCamera()

    def connectCamera(self, camera_index):
        name = (
            "data/HTPP" + datetime.now().strftime("%Y-%m-%d") + self.label[1] + ".mp4"
        )
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.out = cv2.VideoWriter(name, fourcc, self.fps, (self.width, self.height))

    def startCameraRecording(self):
        self.is_recording = True
        if self.camera_thread is None:
            self.camera_thread = threading.Thread(target=self.useCamera, daemon=True)
            self.camera_thread.start()

    def useCamera(self):
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

    def stopCameraRecording(self):
        self.is_recording = False

    def disconnectCamera(self):
        self.stopCameraRecording()
        self.cap.release()
        self.out.release()
        cv2.destroyAllWindows()
        self.camera_thread.join()
        self.resetCamera()

    def resetCamera(self):
        self.cap = None
        self.out = None
        self.camera_thread = None


if __name__ == "__main__":
    camL = CameraHandler("cL")
    camR = CameraHandler("cR")
    camL.connectCamera(0)
    camR.connectCamera(1)
    camL.startCameraRecording()
    camR.startCameraRecording()
    while True:
        x = input("Press h to end the test")
        if x == "h":
            break
        elif x == "j":
            camL.stopCameraRecording()
            camR.stopCameraRecording()
        elif x == "k":
            camL.startCameraRecording()
            camR.startCameraRecording()
    camL.disconnectCamera()
    camR.disconnectCamera()
