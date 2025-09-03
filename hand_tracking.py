import cv2
import mediapipe as mp

class HandTracker:
    def __init__(self, max_hands=2, detection_conf=0.6, tracking_conf=0.6):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_hands,
            min_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf
        )
        self.drawer = mp.solutions.drawing_utils

    def process(self, frame):
        """
        Process a BGR frame and return hand detection results.
        Returns:
            results.multi_hand_landmarks
            results.multi_handedness
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        return results

    def draw(self, frame, hand_landmarks):
        """
        Draw landmarks and connections on a frame.
        """
        self.drawer.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

    def release(self):
        self.hands.close()


# Quick test (only if you run this file directly)
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    tracker = HandTracker()

    print("[INFO] Running Hand Tracker... Press Q to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        results = tracker.process(frame)

        if results.multi_hand_landmarks:
            for hand in results.multi_hand_landmarks:
                tracker.draw(frame, hand)

        cv2.imshow("Hand Tracking Test", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    tracker.release()
