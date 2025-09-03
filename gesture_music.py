import cv2, time, math, json
from collections import deque
from hand_tracking import HandTracker
import visuals  # overlay/visuals module

# ---------- optional backends ----------
try:
    import keyboard
    HAVE_KEYBOARD = True
except Exception:
    HAVE_KEYBOARD = False

try:
    import pyautogui
    HAVE_PYAUTO = True
except Exception:
    HAVE_PYAUTO = False


# ================== LOAD CONFIG ==================
def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"camera_source": 0, "frame_width": 640, "frame_height": 480}

CONFIG   = load_config()
CAM_SRC  = CONFIG.get("camera_source", 0)
FRAME_W  = CONFIG.get("frame_width", 640)
FRAME_H  = CONFIG.get("frame_height", 480)


# ================== KNOBS ==================
EMA_ALPHA          = 0.55
VOTE_WINDOW        = 5
VOTE_MIN_OK        = 3

OK_FACTOR_MAIN     = 0.35   # thumb+index for scrub
SCRUB_DEADZONE     = 0.015
SCRUB_COOLDOWN     = 6
SCRUB_GRACE_FR     = 45

TOUCH_FACTOR_BASE  = 0.22   # base palm width factor for taps
TAP_HYST           = 1.25   # release threshold factor
TAP_COOLDOWN_FR    = 6

ACTIVE_GATE        = True
SPEED_ACTIVATE     = 0.12
ACTIVE_FRAMES      = 30

USE_YT_LJ          = True   # True = YouTube hotkeys j/l (±10s)


# ================== BACKENDS ==================
def send_keypress(key):
    sent = False
    if HAVE_KEYBOARD:
        try:
            keyboard.press(key); time.sleep(0.02); keyboard.release(key)
            sent = True
        except: pass
    if (not sent) and HAVE_PYAUTO:
        try:
            pyautogui.press(key); sent = True
        except: pass
    return sent

def send_combo(keys):
    sent = False
    if HAVE_KEYBOARD:
        try:
            for k in keys: keyboard.press(k)
            time.sleep(0.02)
            for k in reversed(keys): keyboard.release(k)
            sent = True
        except: pass
    if (not sent) and HAVE_PYAUTO:
        try:
            pyautogui.hotkey(*keys); sent = True
        except: pass
    return sent


# ================== HELPERS ==================
def _L(lm): return lm.landmark if hasattr(lm,"landmark") else lm
def dxy(a,b): return math.hypot(a.x-b.x, a.y-b.y)

def palm_center(L):
    idxs=[0,5,9,13,17]
    x = sum(L[i].x for i in idxs)/len(idxs)
    y = sum(L[i].y for i in idxs)/len(idxs)
    return (x,y)

def fingers_up(L):
    def up(tip,pip): return L[tip].y < L[pip].y
    thumb = L[4].x > L[3].x
    idx   = up(8,6)
    mid   = up(12,10)
    ring  = up(16,14)
    pink  = up(20,18)
    return thumb, idx, mid, ring, pink


# ---------- smoothing ----------
class EmaLandmarks:
    def __init__(self, alpha=EMA_ALPHA):
        self.alpha = alpha
        self.prev = None
    def apply(self, lm):
        L = _L(lm)
        if self.prev is None:
            self.prev = [(p.x,p.y,getattr(p,"z",0.0)) for p in L]
            return L
        out = []
        a = self.alpha
        for i,p in enumerate(L):
            px,py,pz = self.prev[i]
            nx = a*px + (1-a)*p.x
            ny = a*py + (1-a)*p.y
            nz = a*pz + (1-a)*getattr(p,"z",0.0)
            self.prev[i] = (nx,ny,nz)
            class P: pass
            q = P(); q.x, q.y, q.z = nx, ny, nz
            out.append(q)
        return out


# ---------- temporal vote ----------
class Vote:
    def __init__(self, w=VOTE_WINDOW): self.buf = deque(maxlen=w)
    def mark(self, is_true): self.buf.append(1 if is_true else 0)
    def ok(self, min_true=VOTE_MIN_OK): return sum(self.buf) >= min_true


# ================== CLASSIFY ==================
def ok_index_only(L):
    """Strict OK detection: thumb(4)+index(8) only."""
    palm_w = dxy(L[5], L[17])
    if palm_w <= 1e-6: return False, palm_w
    return (dxy(L[4], L[8]) < OK_FACTOR_MAIN * palm_w), palm_w

def classify(L):
    thumb, idx, mid, ring, pink = fingers_up(L)

    # Fist
    if not idx and not mid and not ring and not pink and not thumb:
        return "FIST"

    # V-sign
    if idx and mid and not ring and not pink and dxy(L[8], L[12]) > 0.1:
        return "V-SIGN"

    # OK sign (strict index+thumb only)
    is_ok,_ = ok_index_only(L)
    if is_ok:
        return "OK-SIGN"

    # Index = next track
    if idx and not mid and not ring and not pink and not thumb:
        return "INDEX-FINGER"

    # Pinky = previous track
    if pink and not idx and not mid and not ring and not thumb:
        return "PINKY-FINGER"

    # Thumb up/down
    if thumb and not idx and not mid and not ring and not pink:
        wrist = L[0]
        return "THUMB-UP" if L[4].y < wrist.y else "THUMB-DOWN"

    return "UNKNOWN"


# ================== TAP STATE ==================
def empty_tap_state():
    return {"mid_touch": False, "ring_touch": False, "cooldown": 0}


# ================== MAIN ==================
def main(cap=None):
    if cap is None:
        cap = cv2.VideoCapture(CAM_SRC)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    tracker = HandTracker(max_hands=2)
    smoother = {"Left": EmaLandmarks(), "Right": EmaLandmarks()}

    ok_vote = {"Left": Vote(), "Right": Vote()}
    tap_state = {"Left": empty_tap_state(), "Right": empty_tap_state()}

    # state vars
    last_gesture, last_key_status = "NONE", ""
    in_scrub, scrub_text, last_dist = False, "", None
    scrub_cooldown, scrub_grace, gesture_cooldown = 0,0,0
    active_cooldown, fps_hist, last_t = 0, deque(maxlen=30), time.time()

    print("[INFO] Q=quit")

    def overlay(msg): nonlocal last_key_status; last_key_status = "sent: "+msg

    while True:
        ok, frame = cap.read()
        if not ok: break
        frame = cv2.flip(frame, 1)
        h,w = frame.shape[:2]
        results = tracker.process(frame)

        gesture_label, ok_palms = "UNKNOWN", {}

        # detect hands
        if results.multi_hand_landmarks:
            hands_info = []
            if results.multi_handedness:
                for handed,lm in zip(results.multi_handedness, results.multi_hand_landmarks):
                    hands_info.append((handed.classification[0].label, lm))
            else:
                for lm in results.multi_hand_landmarks: hands_info.append(("Unknown", lm))

            for label,lm in hands_info:
                L = smoother.get(label,EmaLandmarks()).apply(lm)
                smoother[label]=smoother.get(label,EmaLandmarks())
                tracker.draw(frame,lm)

                g = classify(L); gesture_label = g
                cx,cy = palm_center(L)

                # OK vote
                if label in ok_vote:
                    is_ok,_ = ok_index_only(L)
                    ok_vote[label].mark(is_ok)
                    if ok_vote[label].ok(): ok_palms[label]=(cx,cy)

                # taps (4+12 = up, 4+16 = down)
                if label in tap_state and g!="FIST":
                    palm_w = max(dxy(L[5], L[17]), 1e-6)
                    touch_th   = TOUCH_FACTOR_BASE * palm_w
                    release_th = touch_th * TAP_HYST
                    mid_gap  = dxy(L[4], L[12])  # vol up
                    ring_gap = dxy(L[4], L[16])  # vol down
                    gate_ok = (not ACTIVE_GATE) or (active_cooldown>0)
                    taps_enabled = gate_ok and (not in_scrub) and (scrub_grace==0)
                    st=tap_state[label]
                    if st["cooldown"]>0: st["cooldown"]-=1

                    if taps_enabled:
                        if (not st["mid_touch"]) and mid_gap<touch_th and st["cooldown"]==0:
                            overlay("vol up" if send_keypress("volume up") else "FAILED")
                            st["mid_touch"]=True; st["cooldown"]=TAP_COOLDOWN_FR
                        elif st["mid_touch"] and mid_gap>release_th: st["mid_touch"]=False
                        if (not st["ring_touch"]) and ring_gap<touch_th and st["cooldown"]==0:
                            overlay("vol down" if send_keypress("volume down") else "FAILED")
                            st["ring_touch"]=True; st["cooldown"]=TAP_COOLDOWN_FR
                        elif st["ring_touch"] and ring_gap>release_th: st["ring_touch"]=False
                    tap_state[label]=st

            # active gate
            speeds=[]
            for label in ok_vote:
                pass # kept minimal, only scrub needs gate

        # scrub mode (both strict OK)
        both_ok=("Left" in ok_palms) and ("Right" in ok_palms)
        if both_ok:
            in_scrub=True; scrub_grace=SCRUB_GRACE_FR
            if ACTIVE_GATE: active_cooldown=ACTIVE_FRAMES
            (x1,y1),(x2,y2)=ok_palms["Left"],ok_palms["Right"]
            p1=(int(x1*w),int(y1*h)); p2=(int(x2*w),int(y2*h))
            cv2.line(frame,p1,p2,(0,255,0),4)
            midx,midy=((p1[0]+p2[0])//2,(p1[1]+p2[1])//2)
            cv2.circle(frame,(midx,midy),15,(255,0,0),-1)
            cur_dist=abs(x2-x1)
            if last_dist is not None:
                delta=cur_dist-last_dist
                if abs(delta)>SCRUB_DEADZONE:
                    fwd,back=("l","j") if USE_YT_LJ else ("right","left")
                    if delta>0:
                        scrub_text=">> FORWARD"
                        if scrub_cooldown<=0: overlay(fwd if send_keypress(fwd) else "FAILED"); scrub_cooldown=SCRUB_COOLDOWN
                    else:
                        scrub_text="<< REWIND"
                        if scrub_cooldown<=0: overlay(back if send_keypress(back) else "FAILED"); scrub_cooldown=SCRUB_COOLDOWN
            last_dist=cur_dist
            visuals.draw_scrub(frame,scrub_text,midx,midy)
            gesture_label="OK-SIGN (SCRUB)"
        else:
            last_dist=None; scrub_text=""; in_scrub=False

        # normal actions
        gate_ok=(not ACTIVE_GATE) or (active_cooldown>0)
        if (not in_scrub) and (scrub_grace==0) and gate_ok:
            if gesture_label in ["FIST","V-SIGN","INDEX-FINGER","PINKY-FINGER"]:
                if gesture_label!=last_gesture and gesture_cooldown<=0:
                    if gesture_label=="FIST": overlay("play/pause" if send_keypress("play/pause media") else "FAILED")
                    elif gesture_label=="V-SIGN": overlay("mute" if send_keypress("volume mute") else "FAILED")
                    elif gesture_label=="INDEX-FINGER": overlay("next" if (send_combo(["shift","n"]) or send_keypress("next track")) else "FAILED")
                    elif gesture_label=="PINKY-FINGER": overlay("prev" if (send_combo(["shift","p"]) or send_keypress("previous track")) else "FAILED")
                    gesture_cooldown=15; last_gesture=gesture_label

        # cooldowns
        if gesture_cooldown>0: gesture_cooldown-=1
        if scrub_cooldown>0:   scrub_cooldown-=1
        if scrub_grace>0:      scrub_grace-=1

        # visuals HUD
        visuals.show_gesture(frame,gesture_label,icon_size=48)
        now=time.time()
        fps_hist.append(1.0/max(now-last_t,1e-6)); last_t=now
        fps=sum(fps_hist)/len(fps_hist)
        visuals.draw_status(frame,fps,(not ACTIVE_GATE) or (active_cooldown>0),scrub_grace,in_scrub,last_key_status)

        cv2.imshow("Gesture Music", frame)
        if cv2.waitKey(1) & 0xFF==ord('q'): break

    cap.release(); cv2.destroyAllWindows(); tracker.release()


if __name__=="__main__":
    main()
