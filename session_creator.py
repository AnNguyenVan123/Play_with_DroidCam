OUTPUT_ROOT = "recordings"
import os
import datetime
import uuid
def now_timestamp_str():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def mac_address_hex():
    """Trả về địa chỉ MAC thật (ưu tiên psutil, fallback uuid) ở dạng hex không có dấu :"""
    try:
        import psutil

        addrs = psutil.net_if_addrs()
        for iface, addr_list in addrs.items():
            for addr in addr_list:
                if getattr(addr, "family", None) in (
                    "AF_LINK",
                    getattr(psutil, "AF_LINK", None),
                ):
                    mac = addr.address
                    if mac and mac != "00:00:00:00:00:00":
                        return mac.replace(":", "")
    except Exception:
        pass

    node = uuid.getnode()
    mac = "".join(f"{(node >> ele) & 0xff:02x}" for ele in range(40, -1, -8))
    first_octet = (node >> 40) & 0xFF
    if first_octet & 0x01:
        print("⚠️  uuid.getnode() trả về giá trị ngẫu nhiên (không phải MAC thật).")
    return mac
def create_session_folder():
    # create session folder with timestamp + mac
    session_name = f"{now_timestamp_str()}_{mac_address_hex()}"
    session_root = os.path.join(OUTPUT_ROOT, session_name)
    os.makedirs(session_root, exist_ok=True)
    return session_root