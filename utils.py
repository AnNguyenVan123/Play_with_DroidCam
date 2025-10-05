
import datetime
import subprocess
import uuid
import time
DEVICE_REMOTE_PORT = 4747
def now_timestamp_str():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

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
    # Nếu args là str, convert thành list
    if isinstance(args, str):
        args = args.split()
    elif not isinstance(args, list):
        raise TypeError(f"args must be list or str, got {type(args)}")

    cmd = ["adb"] + args
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
        )
        return p.stdout.strip(), p.stderr.strip(), p.returncode
    except Exception as e:
        return "", str(e), -1
def adb_toggle_led(serial):
    """
    Toggle camera LED (flashlight) on device via ADB.
    Returns True if command executed without error, False otherwise.
    """
    try:
        # Bật torch 
        print("[ADB] Toggling LED...")
        stdout, stderr, code = run_adb(serial, "shell settings put system torch_enabled 1")
        if code != 0:
            print(f"[ADB ERROR] Failed to turn ON LED on {serial}: {stderr}")
            return False

        time.sleep(0.1)  # giữ LED bật trong 0.1s

        # Tắt torch
        stdout, stderr, code = run_adb(serial, "shell settings put system torch_enabled 0")
        if code != 0:
            print(f"[ADB ERROR] Failed to turn OFF LED on {serial}: {stderr}")
            return False

        return True

    except Exception as e:
        print(f"[EXCEPTION] adb_toggle_led for {serial}: {e}")
        return False


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

def adb_toggle_led(serial):
    """Toggle camera LED (flashlight) if supported."""
    # Example: use camera2 torch command
    # May vary per device; here is a common adb shell trick:
    output = run_adb(serial, ["shell", "settings", "put", "system", "torch_enabled", "1"])
    time.sleep(0.1)
    output = run_adb(serial, ["shell", "settings", "put", "system", "torch_enabled", "0"])
    return output is not None

def get_battery_via_adb(serial):
    """Trả về dict thông tin pin qua adb dumpsys battery"""
    out, err, code = run_adb(["-s", serial, "shell", "dumpsys", "battery"])
    if code != 0 or not out:
        return None
    info = {}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("level:"):
            try:
                info["level"] = int(line.split(":")[1].strip())
            except:
                pass
        elif line.startswith("status:"):
            try:
                st = int(line.split(":")[1].strip())
                m = {
                    1: "UNKNOWN",
                    2: "CHARGING",
                    3: "DISCHARGING",
                    4: "NOT CHARGING",
                    5: "FULL",
                }
                info["status"] = m.get(st, f"status_{st}")
            except:
                info["status"] = line.split(":")[1].strip()
    return info


def adb_forward_for_device(serial, local_port, remote_port=DEVICE_REMOTE_PORT):
    # adb -s <serial> forward tcp:<local_port> tcp:<remote_port>
    out, err, code = run_adb(
        ["-s", serial, "forward", f"tcp:{local_port}", f"tcp:{remote_port}"]
    )
    return code == 0


def adb_kill_forward_for_device(serial, local_port):
    out, err, code = run_adb(["-s", serial, "forward", "--remove", f"tcp:{local_port}"])
    return code == 0


def adb_start_app(serial, package_activity):

    out, err, code = run_adb(
        ["-s", serial, "shell", "am", "start", "-n", package_activity]
    )
    return code == 0


def adb_input_tap(serial, x, y):
    out, err, code = run_adb(["-s", serial, "shell", "input", "tap", str(x), str(y)])
    return code == 0


def log(window, msg):
    try:
        cur = window['-LOG-'].get()
        new = cur + "\n" + f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
        window['-LOG-'].update(new)
    except:
        pass
def adb_set_exposure(serial, value):
    """Set exposure, value can be 'auto', 'lock', numeric level etc."""
    # Device-specific: placeholder, may need camera2 API or app
    print(f"[ADB] Set exposure {value} on {serial}")
    return True


def adb_set_wb_mode(serial, mode):
    """Set white balance mode: auto, daylight, cloudy, etc."""
    print(f"[ADB] Set WB mode {mode} on {serial}")
    return True


def adb_set_resolution(serial, width, height):
    """Set camera resolution."""
    print(f"[ADB] Set resolution {width}x{height} on {serial}")
    return True


def adb_set_zoom(serial, level):
    """Set zoom level."""
    print(f"[ADB] Set zoom {level} on {serial}")
    return True


def adb_set_focus(serial, autofocus=True):
    """Set autofocus on/off."""
    print(f"[ADB] Set autofocus={autofocus} on {serial}")
    return True