from datetime import datetime
import threading

import numpy as np
import cv2


def connectCamera(label, camera_index, width=640, height=480, fps=30):
    name = "data/HTPP" + datetime.now().strftime("%Y-%m-%d") + label[1] + ".mp4"
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(name, fourcc, fps, (width, height))
    return cap, out


def startCameraRecording(video_capture, video_writer, label):
    camera_thread = threading.Thread(
        target=useCamera, args=(video_capture, video_writer, label), daemon=True
    )
    camera_thread.start()
    return camera_thread


def useCamera(video_capture, video_writer, label):
    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if ret:
            frame = cv2.flip(frame, 1).copy()
            timestamp = datetime.now().strftime("%H:%M:%S")
            cv2.putText(
                frame,
                timestamp,
                (0, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                3,
                cv2.LINE_AA,
                False,
            )
            video_writer.write(frame)
            cv2.imshow(label, frame)
            if cv2.waitKey(1) == ord("q"):
                break
        else:
            break


def disconnectCamera(video_capture, video_writer):
    video_capture.release()
    video_writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    capL, outL = connectCamera("cL", 0)
    capR, outR = connectCamera("cR", 1)
    threads = []
    threads.append(startCameraRecording(capL, outL, "cL"))
    threads.append(startCameraRecording(capR, outR, "cR"))
    while True:
        x = input("Press h to end the test")
        if x == "h":
            break
    disconnectCamera(capL, outL)
    disconnectCamera(capR, outR)
    for t in threads:
        t.join()
