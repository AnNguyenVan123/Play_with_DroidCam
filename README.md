# 🎥 Play_with_DroidCam

Control your Android phone’s camera from your PC using **Python 3**!  
Supports **USB connection**, **multiple devices**, and **basic camera controls** such as capture and LED toggle.

> 💡 For the original CUI (Command-Line) version, check the `original` branch.

---

## 📱 Requirements

- **Android device** with [DroidCam app](https://play.google.com/store/apps/details?id=com.dev47apps.droidcam)
- **Windows / Linux / macOS** PC
- **Python 3.8+**
- **USB data cable**
- **ADB (Android Debug Bridge)** installed or available via `adbutils`

---

## 🚀 Quick Start

### 1. Clone the repository

git clone https://github.com/AnNguyenVan123/Play_with_DroidCam.git
cd Play_with_DroidCam


### 2. Install dependencies
python -m pip install -r requirements.txt

⚙️ Setup: Connect Android via USB
Step 1. Install DroidCam on your phone

Download the app on your Android device:
👉 https://play.google.com/store/apps/details?id=com.dev47apps.droidcam

Run the app once — it will automatically start a camera server on port 4747 by default.

Step 2. Enable Developer Options & USB Debugging

Open Settings → About phone → Build number

Tap 7 times to enable Developer Mode.

Go to Settings → Developer options

Enable USB debugging.

Connect your phone via USB to your PC.

When prompted on your phone, tap Allow USB debugging.

Verify the connection:

adb devices


✅ You should see your device’s serial number listed.

### Step 3. Forward DroidCam port

The DroidCam server on your phone listens on port 4747.

Forward that port to your local PC:

adb forward tcp:4747 tcp:4747


If using multiple Android devices (e.g., two cameras):

adb forward tcp:4747 tcp:4747
adb forward tcp:4748 tcp:4747

### Step 4. Run the app

Start the camera control program:

python capture.py


Then the app will auto-connect without asking for IP/PORT.

### 🧠 Features

📸 Capture live camera stream from Android to PC

💡 Toggle flashlight (LED)

🔁 Support multiple connected Android devices

💾 Save captured frames locally

⚡ Real-time monitoring with adjustable FPS

🔋 Battery level polling and logging

🔌 Automatic device detection via ADB


