import cv2
import threading
import time
import os
import datetime


DEFAULT_FPS = 24


class CameraClient(threading.Thread):
    def __init__(self, cam_id, local_port, window, fps=DEFAULT_FPS):
        super().__init__(daemon=True)
        self.cam_id = cam_id  # 0 or 1
        self.local_port = local_port
        self.window = window
        self.fps = fps
        self.running = False
        self.capture = None
        self.last_frame_ts = 0
        self.saving = False
        self.save_folder = None
        self.error_msg = None
        self.lock = threading.Lock()

    def start_capture(self):
        with self.lock:
            if self.running:
                return
            uri = f"http://127.0.0.1:{self.local_port}/video"
            print(f"[cam{self.cam_id+1}] Opening capture: {uri}")
            self.capture = cv2.VideoCapture(uri)
            self.running = True
            self.error_msg = None
            if not self.capture.isOpened():
                self.error_msg = "Cannot open VideoCapture"
                self.running = False
            else:
                # Set some properties if helpful
                self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 2)
                self.last_frame_ts = time.time()
                self.start()

    def stop_capture(self):
        with self.lock:
            self.running = False
            if self.capture:
                try:
                    self.capture.release()
                except:
                    pass
                self.capture = None

    def set_save_folder(self, folder):
        self.save_folder = folder
        os.makedirs(folder, exist_ok=True)

    def set_saving(self, saving: bool):
        self.saving = saving

    def run(self):
        # thread capture loop
        desired_interval = 1.0 / max(1.0, self.fps)
        fail_count = 0
        while True:
            with self.lock:
                if not self.running or self.capture is None:
                    break
                cap = self.capture
            start = time.time()
            try:
                ret, frame = cap.read()
            except Exception as e:
                ret = False
                frame = None
                print(f"[cam{self.cam_id+1}] Exception reading frame: {e}")

            if not ret or frame is None:
                fail_count += 1
                if fail_count >= int(self.fps * 2):  # prolonged failure
                    self.error_msg = "No frames (read failed)"
                    # notify GUI
                    self.window.write_event_value(
                        f"CAM_ERROR", (self.cam_id, self.error_msg)
                    )
                    # stop and attempt to reconnect
                    self.running = False
                    try:
                        cap.release()
                    except:
                        pass
                    break
                time.sleep(0.1)
                continue

            fail_count = 0
            # convert BGR to PNG bytes for GUI
            try:
                _, png = cv2.imencode(".png", frame)
                png_bytes = png.tobytes()
                # push to GUI
                self.window.write_event_value(f"FRAME", (self.cam_id, png_bytes))
            except Exception as e:
                print(f"[cam{self.cam_id+1}] encode error: {e}")

            # save if requested (save every frame or sample at FPS)
            if self.saving and self.save_folder is not None:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                fname = os.path.join(self.save_folder, f"frame_{ts}.png")
                try:
                    cv2.imwrite(fname, frame)
                except Exception as e:
                    print(f"[cam{self.cam_id+1}] save error: {e}")
                    self.window.write_event_value(
                        "CAM_ERROR", (self.cam_id, f"Save error: {e}")
                    )

            elapsed = time.time() - start
            to_sleep = desired_interval - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)
        # end loop
        print(f"[cam{self.cam_id+1}] capture thread ending")
