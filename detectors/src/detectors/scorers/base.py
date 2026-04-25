from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class Scorer:
    score_all: Callable[[np.ndarray, np.ndarray], np.ndarray]
    compute_p_value: Callable[[np.ndarray, np.ndarray], float]
    null_value: float
    score_column: str
    p_value_column: str
