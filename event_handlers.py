import os
import time
import PySimpleGUI as sg
from utils import log, adb_start_app, adb_input_tap
from camera_client import CameraClient
import urllib.request
import subprocess

CAM_PORTS = [4747, 4748]


def get_camera_url(cam_idx, action):
    # cam_num = cam_idx + 1
    port = CAM_PORTS[cam_idx]
    return f"http://127.0.0.1:{port}/cam/1/{action}"


def get_device_info(serial):
    def adb(cmd):
        return subprocess.check_output(
            ["adb", "-s", serial] + cmd, encoding="utf-8"
        ).strip()

    info = {}
    try:
        info["model"] = adb(["shell", "getprop", "ro.product.model"])
        info["manufacturer"] = adb(["shell", "getprop", "ro.product.manufacturer"])
        info["android_version"] = adb(["shell", "getprop", "ro.build.version.release"])
        info["battery"] = adb(["shell", "dumpsys", "battery"])
        info["storage"] = adb(["shell", "df", "/data"])
        info["cpu"] = adb(["shell", "cat", "/proc/cpuinfo"])
    except subprocess.CalledProcessError as e:
        info["error"] = str(e)
    return info


def handle_led_toggle(window, cam_idx):
    url = get_camera_url(cam_idx, "led_toggle")
    try:
        urllib.request.urlopen(url, timeout=2)
        window["-LOG-"].print(f"LED toggled for cam{cam_idx+1}")
    except Exception as e:
        window["-LOG-"].print(f"Error toggling LED for cam{cam_idx+1}: {e}")


def handle_zoom(window, cam_idx, zoom_in=True):
    """
    cam_idx: 0 hoặc 1
    zoom_in: True để Zoom In, False để Zoom Out
    """
    action = "zoomin" if zoom_in else "zoomout"
    url = get_camera_url(cam_idx, action)
    try:
        urllib.request.urlopen(url, timeout=2)
        window["-LOG-"].print(
            f"{'Zoom In' if zoom_in else 'Zoom Out'} executed for cam{cam_idx+1}"
        )
    except Exception as e:
        window["-LOG-"].print(
            f"Error {'Zoom In' if zoom_in else 'Zoom Out'} for cam{cam_idx+1}: {e}"
        )


def handle_device_added(
    cam_idx,
    serial,
    window,
    cam_clients,
    cam_running,
    cam_save_dirs,
    session_root,
    fps,
    LOCAL_PORTS,
):
    window[f"-DEV{cam_idx+1}-"].update(serial)
    log(window, f"Device assigned to cam{cam_idx+1}: {serial}")
    # create camera client if none
    info = get_device_info(serial)
    log(window, f"Device info: {info}")

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
        log(
            window,
            f"Started capture for cam{cam_idx+1} -> local:{LOCAL_PORTS[cam_idx]} , save_folder={cam_folder}",
        )
    except Exception as e:
        log(window, f"Error starting capture cam{cam_idx+1}: {e}")


def handle_device_removed(cam_idx, serial, window, cam_clients, cam_running):
    window[f"-DEV{cam_idx+1}-"].update("")
    print(f"Device removed from cam{cam_idx+1}: {serial}")
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
