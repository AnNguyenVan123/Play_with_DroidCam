import os
import time
import PySimpleGUI as sg
from utils import log, adb_start_app, adb_input_tap
from camera_client import CameraClient
def handle_device_added(cam_idx, serial , window, cam_clients, cam_running, cam_save_dirs, session_root, fps, LOCAL_PORTS):
        window[f'-DEV{cam_idx+1}-'].update(serial)
        log(window, f"Device assigned to cam{cam_idx+1}: {serial}")
        # create camera client if none
    
        if cam_clients[cam_idx] is None:
            client = CameraClient(cam_idx, LOCAL_PORTS[cam_idx], window, fps=fps)
            cam_clients[cam_idx] = client
        # attempt to start captures
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


def handle_device_removed(cam_idx, serial, window, cam_clients, cam_running):
    window[f"-DEV{cam_idx+1}-"].update("")
    log(window, f"Device removed from cam{cam_idx+1}: {serial}")
    if cam_clients[cam_idx]:
        cam_clients[cam_idx].stop_capture()
        cam_clients[cam_idx] = None
        cam_running[cam_idx] = False
        


def handle_start_rec(window, cam_clients, cam_saving, cam_save_dirs, devmgr, values):
    for idx in range(2):
        if cam_clients[idx]:
            cam_clients[idx].set_saving(True)
            cam_saving[idx] = True
            log(window, f"Start recording cam{idx+1} -> {cam_save_dirs[idx]}")

    pkgact = values.get("-PKGACT-", "").strip()
    tap1 = values.get("-TAP1-", "").strip()
    tap2 = values.get("-TAP2-", "").strip()

    with devmgr.lock:
        for cam_idx, serial in devmgr.assigned.items():
            if pkgact:
                ok = adb_start_app(serial, pkgact)
                log(window, f"adb start app for {serial}: {ok}")
                time.sleep(0.5)
            coords = tap1 if cam_idx == 0 else tap2
            if coords:
                try:
                    x, y = coords.split(",")
                    ok = adb_input_tap(serial, int(x), int(y))
                    log(window, f"adb tap for {serial} at ({x},{y}): {ok}")
                except Exception as e:
                    log(window, f"Bad tap coords for cam{cam_idx+1}: {e}")


def handle_stop_rec(window, cam_clients, cam_saving):
    for idx in range(2):
        if cam_clients[idx]:
            cam_clients[idx].set_saving(False)
            cam_saving[idx] = False
            log(window, f"Stop recording cam{idx+1}")
