import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from detectors.classifiers import DETECTORS, Detector
from detectors.features import EXTRACTORS, FeatureExtractor


@dataclass
class Bundle:
    extractor: FeatureExtractor
    detector: Detector
    config: dict


def save_bundle(bundle_dir: Path, extractor: FeatureExtractor, detector: Detector, config: dict) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    extractor.save(bundle_dir / "extractor")
    detector.save(bundle_dir / "detector")
    (bundle_dir / "config.yaml").write_text(yaml.safe_dump(config))


def load_bundle(bundle_dir: Path) -> Bundle:
    bundle_dir = Path(bundle_dir)
    config = yaml.safe_load((bundle_dir / "config.yaml").read_text())
    extractor_kind = json.loads((bundle_dir / "extractor" / "extractor.json").read_text())["kind"]
    detector_kind = json.loads((bundle_dir / "detector" / "detector.json").read_text())["kind"]
    extractor = EXTRACTORS[extractor_kind].load(bundle_dir / "extractor")
    detector = DETECTORS[detector_kind].load(bundle_dir / "detector")
    return Bundle(extractor=extractor, detector=detector, config=config)
