from detectors.features.base import FeatureExtractor
from detectors.features.identity import IdentityExtractor
from detectors.features.pooling import PoolingStrategy, pool_design
from detectors.features.sae_encode import SAEEncodeExtractor

EXTRACTORS = {
    "identity": IdentityExtractor,
    "sae_encode": SAEEncodeExtractor,
}

__all__ = ["FeatureExtractor", "IdentityExtractor", "SAEEncodeExtractor",
           "PoolingStrategy", "pool_design", "EXTRACTORS"]
