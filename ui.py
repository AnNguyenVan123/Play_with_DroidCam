
import PySimpleGUI as sg 
def make_camera_frame(cam_idx):
    return [
        [sg.Image(key=f"-IMG{cam_idx+1}-")],
        [sg.Button('LED ON/OFF', key=f'-LED{cam_idx+1}-', size=(12,2)),
         sg.Button('AutoFocus', key=f'-AF{cam_idx+1}-', size=(12,2)),
         sg.Button('Zoom +', key=f'-ZOOMIN{cam_idx+1}-', size=(12,2)),
         sg.Button('Zoom -', key=f'-ZOOMOUT{cam_idx+1}-', size=(12,2)),
         sg.Button('Exp.Lock ON', key=f'-EXPLON{cam_idx+1}-', size=(12,2)),
         sg.Button('Exp.Lock OFF', key=f'-EXPLOFF{cam_idx+1}-', size=(12,2))]
    ]

# ---------- Main Window ----------
def make_main_window(default_fps):
    sg.theme("DarkBlue3")
    
    cam1_frame = sg.Frame("Cam1 (Left)", make_camera_frame(0), element_justification="center")
    cam2_frame = sg.Frame("Cam2 (Right)", make_camera_frame(1), element_justification="center")
    
    layout = [
        [sg.Text("DroidCam USB Multi (max 2 devices)", font=("Helvetica", 16))],
        [
            sg.Text("FPS:"), sg.InputText(str(default_fps), key="-FPS-", size=(6,1)),
            sg.Button("Apply FPS", key="-APPLYFPS-"),
            sg.Button("Start All", key="-START_ALL-"),
            sg.Button("Stop All", key="-STOP_ALL-"),
            sg.Button("Start Recording", key="-START_REC-"),
            sg.Button("Stop Recording", key="-STOP_REC-"),
        ],
        [cam1_frame, cam2_frame],
        [sg.Text("Cam1 device:"), sg.Text("", key="-DEV1-"),
         sg.Text("   Cam2 device:"), sg.Text("", key="-DEV2-")],
        [sg.Text("Tap coords Cam1 (x,y):"), sg.InputText("", key="-TAP1-", size=(16,1)),
         sg.Text("Tap coords Cam2:"), sg.InputText("", key="-TAP2-", size=(16,1))],
        [sg.Text("Package/Activity to start (optional):"), sg.InputText("", key="-PKGACT-", size=(60,1))],
        [sg.Multiline(default_text="Status messages will appear here...", size=(80,6), key="-LOG-")],
        [sg.Button("Exit")]
    ]
    
    return sg.Window("DroidCam USB Multi", layout, finalize=True)