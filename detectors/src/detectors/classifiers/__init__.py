from detectors.classifiers.base import Detector
from detectors.classifiers.logistic import LogisticDetector
from detectors.classifiers.top_feature import TopFeatureThresholdDetector

DETECTORS = {
    "logistic": LogisticDetector,
    "top_feature": TopFeatureThresholdDetector,
}

__all__ = ["Detector", "LogisticDetector", "TopFeatureThresholdDetector", "DETECTORS"]
