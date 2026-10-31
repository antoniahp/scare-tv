from abc import ABC, abstractmethod


class PersonDetector(ABC):
    """Looks at a frame and says whether there is a person (and, with a pose model, where their eyes are)."""

    kind = "?"          # "yolo" or "motion"
    pose = False        # True if it also returns the 17 body keypoints

    @abstractmethod
    def detect(self, frame):
        """True if there is a person. Leaves the boxes in `last_boxes` and the biggest one in `last_person` (kp, box)."""

    @abstractmethod
    def person(self, frame, conf=0.35):
        """(kp, box) of the biggest person in the frame, or (None, None). Used to track the face frame by frame."""

    @abstractmethod
    def reset(self):
        pass
