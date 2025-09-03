import json
import cv2
import gesture_music

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

if __name__ == "__main__":
    config = load_config()
    cam_index = config.get("camera_source", 0)
    frame_w = config.get("frame_width", 640)
    frame_h = config.get("frame_height", 480)

    print(f"[INFO] Starting with camera source {cam_index} ({frame_w}x{frame_h})")

    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print("[ERROR] Could not open camera. Try changing 'camera_source' in config.json.")
        exit()

    # apply resolution if supported
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_h)

    # pass cap into gesture_music
    gesture_music.main(cap)

    cap.release()
    cv2.destroyAllWindows()
