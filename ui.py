
import PySimpleGUI as sg
def make_main_window(default_fps):
    sg.theme("DarkBlue3")
    layout = [
        [sg.Text("DroidCam USB Multi (max 2 devices)", font=("Helvetica", 16))],
        [
            sg.Text("FPS:"),
            sg.InputText(str(default_fps), key="-FPS-", size=(6, 1)),
            sg.Button("Apply FPS", key="-APPLYFPS-"),
            sg.Button("Start All", key="-START_ALL-"),
            sg.Button("Stop All", key="-STOP_ALL-"),
            sg.Button("Start Recording", key="-START_REC-"),
            sg.Button("Stop Recording", key="-STOP_REC-"),
        ],
        [
            sg.Frame(
                "Cam1 (Left)",
                [[sg.Image(key="-IMG1-")]],
                element_justification="center",
            ),
            sg.Frame(
                "Cam2 (Right)",
                [[sg.Image(key="-IMG2-")]],
                element_justification="center",
            ),
        ],
        [
            sg.Text("Cam1 device:"),
            sg.Text("", key="-DEV1-"),
            sg.Text("   Cam2 device:"),
            sg.Text("", key="-DEV2-"),
        ],
        [
            sg.Text("Tap coords Cam1 (x,y) for Start/Stop on device:"),
            sg.InputText("", key="-TAP1-", size=(16, 1)),
            sg.Text("Tap coords Cam2:"),
            sg.InputText("", key="-TAP2-", size=(16, 1)),
        ],
        [
            sg.Text("Package/Activity to start (optional):"),
            sg.InputText("", key="-PKGACT-", size=(60, 1)),
        ],
        [
            sg.Multiline(
                default_text="Status messages will appear here...",
                size=(80, 6),
                key="-LOG-",
            )
        ],
        [sg.Button("Exit")],
    ]
    return sg.Window("DroidCam USB Multi", layout, finalize=True)
