
import threading
import time

LOCAL_PORTS = [4747, 4748]
DEVICE_REMOTE_PORT = 4747
RECONNECT_INTERVAL = 2.0  # seconds between device checks
CAPTURE_TIMEOUT = 5.0  # seconds
BATTERY_POLL_INTERVAL = 5.0  # typical DroidCam server port on device
from utils import (
    list_adb_devices,
    adb_forward_for_device,
    adb_kill_forward_for_device,
    get_battery_via_adb
)


class DeviceManager(threading.Thread):
    def __init__(self, window):
        super().__init__(daemon=True)
        self.window = window
        self.assigned = {}  # cam_index -> serial
        self.lock = threading.Lock()
        self.running = True
        self._last_battery_poll = 0.0

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            try:
                devices = list_adb_devices()  # list of (serial, status)
                serials = [s for s, st in devices if st == "device"]

                removed = []
                added = []

                # --------------- Lock chỉ khi thao tác dữ liệu ---------------
                with self.lock:
                    # xử lý thiết bị bị rút
                    for cam_idx, serial in list(self.assigned.items()):
                        if serial not in serials:
                            removed.append((cam_idx, serial))
                            try:
                                adb_kill_forward_for_device(serial, LOCAL_PORTS[cam_idx])
                            except Exception:
                                pass
                            del self.assigned[cam_idx]

                    # tìm các cam trống
                    free_cam_indices = [0, 1]
                    for idx in list(self.assigned.keys()):
                        if idx in free_cam_indices:
                            free_cam_indices.remove(idx)

                    # assign thiết bị mới
                    for s in serials:
                        if s in self.assigned.values():
                            continue
                        if not free_cam_indices:
                            break
                        cam_idx = free_cam_indices.pop(0)
                        ok = adb_forward_for_device(s, LOCAL_PORTS[cam_idx], DEVICE_REMOTE_PORT)
                        if ok:
                            self.assigned[cam_idx] = s
                            added.append((cam_idx, s))
                        else:
                            print(f"[DeviceManager] Forward failed for {s} -> local {LOCAL_PORTS[cam_idx]}")

                    # poll battery nếu đủ thời gian
                    now = time.time()
                    battery_updates = []
                    if now - self._last_battery_poll >= BATTERY_POLL_INTERVAL:
                        for cam_idx, serial in self.assigned.items():
                            try:
                                print(f"[DeviceManager] Polling battery for cam{cam_idx+1} ({serial})")
                                info = get_battery_via_adb(serial,self.window)
                                print(f"[DeviceManager] Battery for cam{cam_idx+1} ({serial}): {info}")
                                battery_updates.append((cam_idx, serial, info))
                            except Exception:
                                pass
                        self._last_battery_poll = now

                # --------------- Push event ra ngoài lock ---------------
                for cam_idx, serial in removed:
                    self.window.write_event_value('DEVICE_REMOVED', (cam_idx, serial))
                for cam_idx, serial in added:
                    self.window.write_event_value('DEVICE_ADDED', (cam_idx, serial))
                for cam_idx, serial, info in battery_updates:
                    self.window.write_event_value('BATTERY_UPDATE', (cam_idx, serial, info))

            except Exception as e:
                print(f"[DeviceManager] Error in run loop: {e}")

            time.sleep(RECONNECT_INTERVAL)