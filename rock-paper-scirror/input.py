import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
from mediapipe.tasks.python.vision import HandLandmarkerOptions, RunningMode

# Download once: https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
model_path = "hand_landmarker.task"

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    num_hands=2,
    running_mode=RunningMode.VIDEO
)
landmarker = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
timestamp = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    timestamp += 1
    result = landmarker.detect_for_video(mp_image, timestamp)

    if result.hand_landmarks:
        for hand_landmarks in result.hand_landmarks:
            h, w, _ = frame.shape
            for lm in hand_landmarks:
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)
                
            # index fingertip is landmark 8
            tip = hand_landmarks[8]
            tx, ty = int(tip.x * w), int(tip.y * h)
            cv2.circle(frame, (tx, ty), 10, (0, 0, 255), -1)

    cv2.imshow("Hand Tracking", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()