🎶 Gesture Music Player

A Python-based gesture-controlled music player that uses your webcam to detect hand gestures and control playback, volume, and track navigation.  
Built with OpenCV and Media Pipe, it turns your hands into a controller — no keyboard needed.  

---------------------------------------------------------------------------------------

✨ Features
- 👊 Fist → Play / Pause  
- ✌️ V-Sign** → Mute / Unmute  
- ☝️ Index Finger** → Next Track  
- 🤙 Pinky Finger** → Previous Track  
- 👍 Tap Thumb + Middle Finger Tip → Volume Up
- 👎 Tap Thumb + Middle Finger Tip → Volume Down  
- 👌 OK-Sign with both hands → Scrub through track (forward/rewind)  
- 🎨 Visual overlay with icons for gesture feedback  

---------------------------------------------------------------------------------------

⚡ Requirements
Make sure you have Python 3.10+ installed.  
Install the following tools/libraries before running:

```bash
pip install opencv-python
pip install mediapipe
pip install keyboard
pip install pyautogui

---------------------------------------------------------------------------------------

// How to Run:-

1. Clone this Repository:

git clone https://github.com/Siddhant13421/gesture-music-player.git
cd gesture-music-player

2. Create and activate a virtual environment:

python -m venv .venv
.venv\Scripts\activate   # On Windows

3. Run the Program:

python main.py

-------------------------------------------------------------------------------------

// Notes:-

1. Works best in Good lighting

2. Default camera is 0 (laptop webcam). Change "config.json" to use another source 
(e.g., DroidCam )

3. Icons must be placed in the icons/ folder with the exact filenames mentioned in "visuals.py".