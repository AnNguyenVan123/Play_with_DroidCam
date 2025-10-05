"""
droidcam_usb_multi.py
- Kết nối tối đa 2 Android devices qua cáp USB (ADB)
- Forward mỗi device local tcp ports 4747, 4748 --> device:4747
- Hiển thị realtime 2 camera (cam1, cam2)
- Cho phép điều khiển app trên Android (adb start app, adb input tap)
- Lưu frames vào folder OUTPUT_ROOT/<timestamp>_<MAC>/cam1 and cam2
"""

import threading
import time
import os
import datetime
import PySimpleGUI as sg
from camera_client import CameraClient  # tránh circular import
from utils import (
    adb_start_app,
    adb_input_tap,
    now_timestamp_str,
    mac_address_hex,
    adb_toggle_led,
    adb_set_zoom,
)
from device_manager import DeviceManager
from ui import make_main_window
from event_handlers import handle_device_added, handle_device_removed
from event_handlers import handle_start_rec, handle_device_added, handle_device_removed


# --------------- Config mặc định ---------------
DEFAULT_FPS = 24
LOCAL_PORTS = [4747, 4748]  # local ports for cam1, cam2
DEVICE_REMOTE_PORT = 4747  # typical DroidCam server port on device
OUTPUT_ROOT = "recordings"
RECONNECT_INTERVAL = 2.0  # seconds between device checks
CAPTURE_TIMEOUT = 5.0  # seconds


def log(window, msg):
    try:
        cur = window["-LOG-"].get()
        new = cur + "\n" + f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
        window["-LOG-"].update(new)
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

    # event loop
    try:
        while True:
            event, values = window.read(timeout=200)
            if event == sg.WIN_CLOSED or event == "Exit":
                break
            if event == "-APPLYFPS-":
                try:
                    newfps = float(values["-FPS-"])
                    fps = max(1.0, newfps)
                    # apply to existing clients
                    for c in cam_clients:
                        if c:
                            c.fps = fps
                    log(window, f"Applied FPS = {fps}")
                except Exception as e:
                    log(window, f"Bad FPS value: {e}")

            if event == "-START_ALL-":
                print(f"[Main] Currently assigned devices: {devmgr.assigned}")
                # attempt to start capture on any assigned device
                for cam_idx, serial in devmgr.assigned.items():
                    print(f"[Main] Starting cam{cam_idx+1} for device {serial}")
                    handle_device_added(
                        cam_idx,
                        serial,
                        window,
                        cam_clients,
                        cam_running,
                        cam_save_dirs,
                        session_root,
                        fps,
                        LOCAL_PORTS,
                    )

            if event == "-STOP_ALL-":
                for idx in range(2):
                    if cam_clients[idx]:
                        cam_clients[idx].stop_capture()
                        cam_clients[idx] = None
                        window[f"-DEV{idx+1}-"].update("")
                        log(window, f"Stopped cam{idx+1}")

            if event == "-START_REC-":
                # start saving frames
                for idx in range(2):
                    if cam_clients[idx]:
                        cam_clients[idx].set_saving(True)
                        cam_saving[idx] = True
                        log(
                            window,
                            f"Start recording cam{idx+1} -> {cam_save_dirs[idx]}",
                        )
                # optional: start recording on device via adb if configured (tap or start app)
                pkgact = values.get("-PKGACT-", "").strip()
                tap1 = values.get("-TAP1-", "").strip()
                tap2 = values.get("-TAP2-", "").strip()
                # handle devices

                for cam_idx, serial in devmgr.assigned.items():
                    if pkgact:
                        ok = adb_start_app(serial, pkgact)
                        log(window, f"adb start app for {serial}: {ok}")
                        time.sleep(0.5)
                    # if tap configured for this cam, send tap
                    coords = tap1 if cam_idx == 0 else tap2
                    if coords:
                        try:
                            x, y = coords.split(",")
                            ok = adb_input_tap(serial, int(x), int(y))
                            log(window, f"adb tap for {serial} at ({x},{y}): {ok}")
                        except Exception as e:
                            log(window, f"Bad tap coords for cam{cam_idx+1}: {e}")

            if event == "-STOP_REC-":
                for idx in range(2):
                    if cam_clients[idx]:
                        cam_clients[idx].set_saving(False)
                        cam_saving[idx] = False
                        log(window, f"Stop recording cam{idx+1}")
            if event == "-LED_TOGGLE-":
                    log(window, "Toggled LED ON/OFF on both cameras")
                    print("[Main] Toggling LED on all assigned devices...", flush=True)

                    for cam_idx, serial in devmgr.assigned.items():
                      def led_thread(serial, cam_idx):
                          print(f"[ADB] Toggling LED cam{cam_idx+1} ({serial})...", flush=True)
                          ok = adb_toggle_led(serial)
                          log(window, f"adb toggle LED cam{cam_idx+1} ({serial}): {ok}")

                      threading.Thread(target=led_thread, args=(serial, cam_idx), daemon=True).start()

            if event == "-ZOOM_IN-":
                for cam_idx, serial in devmgr.assigned.items():
                    try:
                        # Lưu ý: bạn có thể track zoom hiện tại trong dict riêng nếu muốn
                        ok = adb_set_zoom(serial, "in")  # hoặc level = hiện tại + 1
                        log(window, f"Zoom + cam{cam_idx+1} ({serial}): {ok}")
                    except Exception as e:
                        log(window, f"Error zoom cam{cam_idx+1}: {e}")
            if event == "-ZOOM_OUT-":
                for cam_idx, serial in devmgr.assigned.items():
                    try:
                        ok = adb_set_zoom(serial, "out")  # hoặc level = hiện tại - 1
                        log(window, f"Zoom - cam{cam_idx+1} ({serial}): {ok}")
                    except Exception as e:
                        log(window, f"Error zoom cam{cam_idx+1}: {e}")
            if event == "-WB_SETTINGS-":
                sg.popup(
                    "WB Settings placeholder",
                    "Chức năng này sẽ mở menu White Balance...",
                )

            # frames/events from camera threads
            if event == "FRAME":
                cam_idx, png_bytes = values[event]
                key = "-IMG1-" if cam_idx == 0 else "-IMG2-"
                try:
                    window[key].update(data=png_bytes)
                except Exception as e:
                    log(window, f"Error updating GUI image {cam_idx+1}: {e}")

            if event == "CAM_ERROR":
                cam_idx, errstr = values[event]
                log(window, f"ERROR cam{cam_idx+1}: {errstr}")
                sg.popup_ok(f"Camera {cam_idx+1} error: {errstr}")

            if event == "DEVICE_ADDED":
                cam_idx, serial = values[event]
                handle_device_added(
                    cam_idx,
                    serial,
                    window,
                    cam_clients,
                    cam_running,
                    cam_save_dirs,
                    session_root,
                    fps,
                    LOCAL_PORTS,
                )

            if event == "DEVICE_REMOVED":
                cam_idx, serial = values[event]
                handle_device_removed(
                    cam_idx, serial, window, cam_clients, cam_running
                )

    finally:
        # cleanup
        devmgr.stop()
        for idx in range(2):
            if cam_clients[idx]:
                cam_clients[idx].stop_capture()
        window.close()


if __name__ == "__main__":
    main()
