import numpy as np

from detectors.classifiers.logistic import LogisticDetector
from detectors.classifiers.top_feature import TopFeatureThresholdDetector


def _separable_dataset(seed: int = 0):
    rng = np.random.default_rng(seed)
    n = 200
    target = rng.integers(0, 2, n).astype(np.int64)
    features = rng.standard_normal((n, 5)).astype(np.float32)
    features[:, 0] += 3.0 * target
    return features, target


def test_logistic_separable_high_accuracy():
    features, target = _separable_dataset()
    detector = LogisticDetector(epochs=300, lr=0.1)
    detector.fit(features, target)
    probabilities = detector.predict_proba(features)
    assert probabilities.shape == (len(features), 2)
    accuracy = (probabilities.argmax(axis=1) == target).mean()
    assert accuracy > 0.85


def test_logistic_save_load_round_trip(tmp_path):
    features, target = _separable_dataset(seed=1)
    detector = LogisticDetector(epochs=100, lr=0.1)
    detector.fit(features, target)
    detector.save(tmp_path)
    loaded = LogisticDetector.load(tmp_path)
    np.testing.assert_allclose(detector.predict_proba(features), loaded.predict_proba(features), atol=1e-5)


def test_top_feature_threshold_picks_best_feature():
    features, target = _separable_dataset(seed=2)
    detector = TopFeatureThresholdDetector()
    detector.fit(features, target)
    assert detector.feature_index == 0
    probabilities = detector.predict_proba(features)
    accuracy = (probabilities.argmax(axis=1) == target).mean()
    assert accuracy > 0.7


def test_top_feature_threshold_save_load(tmp_path):
    features, target = _separable_dataset(seed=3)
    detector = TopFeatureThresholdDetector()
    detector.fit(features, target)
    detector.save(tmp_path)
    loaded = TopFeatureThresholdDetector.load(tmp_path)
    np.testing.assert_allclose(detector.predict_proba(features), loaded.predict_proba(features))
