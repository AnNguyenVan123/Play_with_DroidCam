"""
droidcam_usb_multi.py
- Kết nối tối đa 2 Android devices qua cáp USB (ADB)
- Forward mỗi device local tcp ports 4747, 4748 --> device:4747
- Hiển thị realtime 2 camera (cam1, cam2)
- Cho phép điều khiển app trên Android (adb start app, adb input tap)
- Lưu frames vào folder OUTPUT_ROOT/<timestamp>_<MAC>/cam1 and cam2
"""

import threading
import subprocess
import time
import os
import cv2
import uuid
import datetime
import PySimpleGUI as sg

# --------------- Config mặc định ---------------
DEFAULT_FPS = 24
LOCAL_PORTS = [4747, 4748]   # local ports for cam1, cam2
DEVICE_REMOTE_PORT = 4747    # typical DroidCam server port on device
OUTPUT_ROOT = "recordings"
RECONNECT_INTERVAL = 2.0     # seconds between device checks
CAPTURE_TIMEOUT = 5.0        # seconds

# --------------- Helper functions ---------------
def mac_address_hex():
    """Trả về địa chỉ MAC thật (ưu tiên psutil, fallback uuid) ở dạng hex không có dấu :"""
    try:
        import psutil
        addrs = psutil.net_if_addrs()
        for iface, addr_list in addrs.items():
            for addr in addr_list:
                if getattr(addr, 'family', None) in ('AF_LINK', getattr(psutil, 'AF_LINK', None)):
                    mac = addr.address
                    if mac and mac != "00:00:00:00:00:00":
                        return mac.replace(":", "")
    except Exception:
        pass

    node = uuid.getnode()
    mac = ''.join(f'{(node >> ele) & 0xff:02x}' for ele in range(40, -1, -8))
    first_octet = (node >> 40) & 0xff
    if first_octet & 0x01:
        print("⚠️  uuid.getnode() trả về giá trị ngẫu nhiên (không phải MAC thật).")
    return mac
def now_timestamp_str():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def run_adb(args, timeout=5):
    cmd = ["adb"] + args
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, text=True)
        return p.stdout.strip(), p.stderr.strip(), p.returncode
    except Exception as e:
        return "", str(e), -1

def list_adb_devices():
    out, err, code = run_adb(["devices"])
    if code != 0:
        return []
    lines = out.splitlines()
    res = []
    for l in lines[1:]:
        l = l.strip()
        if not l:
            continue
        parts = l.split()
        if len(parts) >= 2:
            serial, status = parts[0], parts[1]
            if status in ("device", "unauthorized", "offline"):
                res.append((serial, status))
    return res

def adb_forward_for_device(serial, local_port, remote_port=DEVICE_REMOTE_PORT):
    # adb -s <serial> forward tcp:<local_port> tcp:<remote_port>
    out, err, code = run_adb(["-s", serial, "forward", f"tcp:{local_port}", f"tcp:{remote_port}"])
    return code == 0

def adb_kill_forward_for_device(serial, local_port):
    out, err, code = run_adb(["-s", serial, "forward", "--remove", f"tcp:{local_port}"])
    return code == 0

def adb_start_app(serial, package_activity):

    out, err, code = run_adb(["-s", serial, "shell", "am", "start", "-n", package_activity])
    return code == 0

def adb_input_tap(serial, x, y):
    out, err, code = run_adb(["-s", serial, "shell", "input", "tap", str(x), str(y)])
    return code == 0

# --------------- Camera client (thread per cam) ---------------
class CameraClient(threading.Thread):
    def __init__(self, cam_id, local_port, window, fps=DEFAULT_FPS):
        super().__init__(daemon=True)
        self.cam_id = cam_id      # 0 or 1
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
                if fail_count >= int(self.fps*2):  # prolonged failure
                    self.error_msg = "No frames (read failed)"
                    # notify GUI
                    self.window.write_event_value(f'CAM_ERROR', (self.cam_id, self.error_msg))
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
                _, png = cv2.imencode('.png', frame)
                png_bytes = png.tobytes()
                # push to GUI
                self.window.write_event_value(f'FRAME', (self.cam_id, png_bytes))
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
                    self.window.write_event_value('CAM_ERROR', (self.cam_id, f"Save error: {e}"))

            elapsed = time.time() - start
            to_sleep = desired_interval - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)
        # end loop
        print(f"[cam{self.cam_id+1}] capture thread ending")

# --------------- Device Manager to handle adb devices and forwards ---------------
class DeviceManager(threading.Thread):
    def __init__(self, window):
        super().__init__(daemon=True)
        self.window = window
        self.assigned = {}  # cam_index -> serial
        self.lock = threading.Lock()
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            devices = list_adb_devices()  # list of (serial, status)
            serials = [s for s, st in devices if st == "device"]
            # keep first two devices (order from adb)
            with self.lock:
                # remove assigned that no longer present
                removed = []
                for cam_idx, serial in list(self.assigned.items()):
                    if serial not in serials:
                        removed.append((cam_idx, serial))
                        # remove forward
                        try:
                            adb_kill_forward_for_device(serial, LOCAL_PORTS[cam_idx])
                        except:
                            pass
                        self.window.write_event_value('DEVICE_REMOVED', (cam_idx, serial))
                        del self.assigned[cam_idx]
                # assign free cams
                free_cam_indices = [0,1]
                for idx in list(self.assigned.keys()):
                    if idx in free_cam_indices:
                        free_cam_indices.remove(idx)
                for s in serials:
                    if s in self.assigned.values():
                        continue
                    if not free_cam_indices:
                        break
                    cam_idx = free_cam_indices.pop(0)
                    ok = adb_forward_for_device(s, LOCAL_PORTS[cam_idx], DEVICE_REMOTE_PORT)
                    if ok:
                        self.assigned[cam_idx] = s
                        self.window.write_event_value('DEVICE_ADDED', (cam_idx, s))
                    else:
                        print(f"[DeviceManager] Forward failed for {s} -> local {LOCAL_PORTS[cam_idx]}")
            time.sleep(RECONNECT_INTERVAL)

# --------------- GUI and main ---------------
def make_main_window(default_fps):
    sg.theme("DarkBlue3")
    layout = [
        [sg.Text("DroidCam USB Multi (max 2 devices)", font=("Helvetica", 16))],
        [sg.Text("FPS:"), sg.InputText(str(default_fps), key='-FPS-', size=(6,1)),
         sg.Button("Apply FPS", key='-APPLYFPS-'),
         sg.Button("Start All", key='-START_ALL-'), sg.Button("Stop All", key='-STOP_ALL-'),
         sg.Button("Start Recording", key='-START_REC-'), sg.Button("Stop Recording", key='-STOP_REC-')],
        [sg.Frame("Cam1 (Left)", [[sg.Image(key='-IMG1-')]], element_justification='center'),
         sg.Frame("Cam2 (Right)", [[sg.Image(key='-IMG2-')]], element_justification='center')],
        [sg.Text("Cam1 device:"), sg.Text("", key='-DEV1-'),
         sg.Text("   Cam2 device:"), sg.Text("", key='-DEV2-')],
        [sg.Text("Tap coords Cam1 (x,y) for Start/Stop on device:"), sg.InputText("", key='-TAP1-', size=(16,1)),
         sg.Text("Tap coords Cam2:"), sg.InputText("", key='-TAP2-', size=(16,1))],
        [sg.Text("Package/Activity to start (optional):"), sg.InputText("", key='-PKGACT-', size=(60,1))],
        [sg.Multiline(default_text="Status messages will appear here...", size=(80,6), key='-LOG-')],
        [sg.Button("Exit")]
    ]
    return sg.Window("DroidCam USB Multi", layout, finalize=True)

def log(window, msg):
    try:
        cur = window['-LOG-'].get()
        new = cur + "\n" + f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
        window['-LOG-'].update(new)
    except:
        pass

def main():
    window = make_main_window(DEFAULT_FPS)
    # state
    cam_clients = [None, None]
    cam_running = [False, False]
    cam_saving = [False, False]
    cam_save_dirs = [None, None]
    fps = DEFAULT_FPS

    # prepare root output folder
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    # create session folder with timestamp + mac
    session_name = f"{now_timestamp_str()}_{mac_address_hex()}"
    session_root = os.path.join(OUTPUT_ROOT, session_name)
    os.makedirs(session_root, exist_ok=True)
    log(window, f"Session root: {session_root}")

    # start device manager
    devmgr = DeviceManager(window)
    devmgr.start()

    # handlers for device events:
    def handle_device_added(cam_idx, serial):
        window[f'-DEV{cam_idx+1}-'].update(serial)
        log(window, f"Device assigned to cam{cam_idx+1}: {serial}")
        # create camera client if none
        nonlocal cam_clients
        if cam_clients[cam_idx] is None:
            client = CameraClient(cam_idx, LOCAL_PORTS[cam_idx], window, fps=fps)
            cam_clients[cam_idx] = client
        # attempt to start capture
        try:
            cam_clients[cam_idx].start_capture()
            cam_running[cam_idx] = True
            # set save folder for this cam
            cam_folder = os.path.join(session_root, f"cam{cam_idx+1}")
            cam_clients[cam_idx].set_save_folder(cam_folder)
            cam_save_dirs[cam_idx] = cam_folder
            log(window, f"Started capture for cam{cam_idx+1} -> local:{LOCAL_PORTS[cam_idx]} , save_folder={cam_folder}")
        except Exception as e:
            log(window, f"Error starting capture cam{cam_idx+1}: {e}")

    def handle_device_removed(cam_idx, serial):
        window[f'-DEV{cam_idx+1}-'].update("")
        log(window, f"Device removed from cam{cam_idx+1}: {serial}")
        if cam_clients[cam_idx]:
            cam_clients[cam_idx].stop_capture()
            cam_clients[cam_idx] = None
            cam_running[cam_idx] = False

    # event loop
    try:
        while True:
            event, values = window.read(timeout=200)
            if event == sg.WIN_CLOSED or event == "Exit":
                break
            if event == '-APPLYFPS-':
                try:
                    newfps = float(values['-FPS-'])
                    fps = max(1.0, newfps)
                    # apply to existing clients
                    for c in cam_clients:
                        if c:
                            c.fps = fps
                    log(window, f"Applied FPS = {fps}")
                except Exception as e:
                    log(window, f"Bad FPS value: {e}")

            if event == '-START_ALL-':
                # attempt to start capture on any assigned device
                with devmgr.lock:
                    for cam_idx, serial in devmgr.assigned.items():
                        handle_device_added(cam_idx, serial)

            if event == '-STOP_ALL-':
                for idx in range(2):
                    if cam_clients[idx]:
                        cam_clients[idx].stop_capture()
                        cam_clients[idx] = None
                        window[f'-DEV{idx+1}-'].update("")
                        log(window, f"Stopped cam{idx+1}")

            if event == '-START_REC-':
                # start saving frames
                for idx in range(2):
                    if cam_clients[idx]:
                        cam_clients[idx].set_saving(True)
                        cam_saving[idx] = True
                        log(window, f"Start recording cam{idx+1} -> {cam_save_dirs[idx]}")
                # optional: start recording on device via adb if configured (tap or start app)
                pkgact = values.get('-PKGACT-', "").strip()
                tap1 = values.get('-TAP1-', "").strip()
                tap2 = values.get('-TAP2-', "").strip()
                # handle devices
                with devmgr.lock:
                    for cam_idx, serial in devmgr.assigned.items():
                        if pkgact:
                            ok = adb_start_app(serial, pkgact)
                            log(window, f"adb start app for {serial}: {ok}")
                            time.sleep(0.5)
                        # if tap configured for this cam, send tap
                        coords = tap1 if cam_idx == 0 else tap2
                        if coords:
                            try:
                                x,y = coords.split(',')
                                ok = adb_input_tap(serial, int(x), int(y))
                                log(window, f"adb tap for {serial} at ({x},{y}): {ok}")
                            except Exception as e:
                                log(window, f"Bad tap coords for cam{cam_idx+1}: {e}")

            if event == '-STOP_REC-':
                for idx in range(2):
                    if cam_clients[idx]:
                        cam_clients[idx].set_saving(False)
                        cam_saving[idx] = False
                        log(window, f"Stop recording cam{idx+1}")

            # frames/events from camera threads
            if event == 'FRAME':
                cam_idx, png_bytes = values[event]
                key = '-IMG1-' if cam_idx == 0 else '-IMG2-'
                try:
                    window[key].update(data=png_bytes)
                except Exception as e:
                    log(window, f"Error updating GUI image {cam_idx+1}: {e}")

            if event == 'CAM_ERROR':
                cam_idx, errstr = values[event]
                log(window, f"ERROR cam{cam_idx+1}: {errstr}")
                sg.popup_ok(f"Camera {cam_idx+1} error: {errstr}")

            if event == 'DEVICE_ADDED':
                cam_idx, serial = values[event]
                handle_device_added(cam_idx, serial)

            if event == 'DEVICE_REMOVED':
                cam_idx, serial = values[event]
                handle_device_removed(cam_idx, serial)

    finally:
        # cleanup
        devmgr.stop()
        for idx in range(2):
            if cam_clients[idx]:
                cam_clients[idx].stop_capture()
        window.close()

if __name__ == "__main__":
    main()
