# visuals.py
import cv2, os, time

# preload icons if available
ICON_PATHS = {
    "FIST": "icons/play_pause.png",
    "V-SIGN": "icons/mute.png",
    "INDEX-FINGER": "icons/next.png",
    "THUMB-UP": "icons/vol_up.png",
    "THUMB-DOWN": "icons/vol_down.png",
    "PINKY-FINGER": "icons/prev.png",
    "OK-SIGN": "icons/scrub.png"
}
ICONS = {}

for k, path in ICON_PATHS.items():
    if os.path.exists(path):
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)  # keep alpha
        ICONS[k] = img

def overlay_icon(frame, icon, pos, size=48):
    """overlay PNG icon with transparency"""
    if icon is None: return frame
    ih, iw = icon.shape[:2]
    icon_resized = cv2.resize(icon, (size, size))
    x,y = pos
    h,w = frame.shape[:2]

    if x+size>w or y+size>h: return frame

    alpha_s = icon_resized[:,:,3]/255.0
    alpha_l = 1.0 - alpha_s

    for c in range(3):
        frame[y:y+size, x:x+size, c] = (alpha_s*icon_resized[:,:,c] +
                                        alpha_l*frame[y:y+size, x:x+size, c])
    return frame

def draw_text(frame, text, pos, color=(255,255,255)):
    x,y = pos
    cv2.putText(frame, text, (x+2,y+2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 3)
    cv2.putText(frame, text, (x,y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

def show_gesture(frame, gesture, icon_size=48):
    """show gesture icon + name"""
    if gesture in ICONS:
        overlay_icon(frame, ICONS[gesture], (20,20), size=icon_size)
    draw_text(frame, f"Gesture: {gesture}", (80,50), (0,255,0))

def draw_scrub(frame, direction, midx, midy):
    """draw scrub bar + direction"""
    color = (0,255,0) if direction==">> FORWARD" else (0,0,255)
    cv2.putText(frame, direction, (midx-80, midy-30),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)

def draw_status(frame, fps, active, grace, scrub_mode=False, last_key=""):
    state = "ACTIVE" if active else "IDLE"
    draw_text(frame, f"FPS: {fps:.1f}", (20,160), (200,200,200))
    draw_text(frame, f"Gate:{state}  Grace:{grace}", (20,190),
              (80,230,80) if active else (80,80,230))
    if scrub_mode:
        draw_text(frame, "SCRUB MODE", (20,220), (0,200,255))
    if last_key:
        draw_text(frame, last_key, (20,250), (60,200,255))
