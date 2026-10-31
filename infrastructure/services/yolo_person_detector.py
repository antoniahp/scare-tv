"""Detects people with YOLO (open-weight, local). With a pose model it also returns the 17 body keypoints.
Without YOLO it falls back to a motion detector (anything that moves)."""
import os

import cv2
import numpy as np

from domain.services.person_detector import PersonDetector


def best_person(result):
    """From a YOLO-pose result, the biggest person (the one closest to the TV): (kp, box)."""
    if result is None or result.boxes is None or len(result.boxes) == 0:
        return None, None
    boxes = result.boxes.xyxy.cpu().numpy()
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    i = int(np.argmax(areas))
    kp = None
    if getattr(result, "keypoints", None) is not None and result.keypoints.data is not None and len(result.keypoints.data) > i:
        kp = result.keypoints.data[i].cpu().numpy()
    return kp, tuple(boxes[i])


class YoloPersonDetector(PersonDetector):
    def __init__(self, mode="auto", model="yolo11n-pose.pt", conf=0.5, motion=0.02, base_dir="."):
        self.kind = "motion"
        self.pose = False
        self.conf = conf
        self.motion = motion
        self.last_boxes = []
        self.last_person = (None, None)
        self.model = None
        if mode in ("auto", "yolo"):
            try:
                from ultralytics import YOLO

                if not os.path.isabs(str(model)) and os.sep not in str(model):
                    model = os.path.join(base_dir, model)   # downloaded automatically the first time (~6 MB)
                self.model = YOLO(str(model))
                self.model(np.zeros((320, 320, 3), np.uint8), classes=[0], imgsz=320, verbose=False)  # calentar
                self.kind = "yolo"
                self.pose = getattr(self.model, "task", "") == "pose"
            except Exception as e:  # noqa: BLE001
                if mode == "yolo":
                    raise
                print(f"[warning] YOLO not available ({e}). Using motion detection.")
        self.reset()

    def reset(self):
        self.bg = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=32, detectShadows=False)
        self.warmup = 30

    def detect(self, frame):
        if self.kind == "yolo":
            r = self.model(frame, classes=[0], conf=self.conf, imgsz=320, verbose=False)[0]
            self.last_boxes = [tuple(map(int, b)) for b in r.boxes.xyxy.tolist()]
            self.last_person = best_person(r) if self.pose else (None, None)
            return len(self.last_boxes) > 0
        small = cv2.resize(frame, (320, 180))
        mask = cv2.medianBlur(self.bg.apply(small), 5)
        if self.warmup > 0:
            self.warmup -= 1
            return False
        return cv2.countNonZero(mask) / mask.size > self.motion

    def person(self, frame, conf=0.35, imgsz=320):
        if self.kind != "yolo":
            return None, None
        r = self.model(frame, classes=[0], conf=conf, imgsz=imgsz, verbose=False)[0]
        return best_person(r)
