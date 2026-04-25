import h5py
import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_dataset(tmp_path):
    """Tiny activation h5 + label CSV with a planted toxic-feature signal.

    Designs alternate toxic/benign; toxic designs have elevated activation in dim 3.
    Two hooks: 'block8' (dynamic, 4 steps) and 'token_initializer_outputs' (static, 1 step).
    """
    rng = np.random.default_rng(42)
    activations_path = tmp_path / "activations.h5"
    labels = []
    n_designs, n_samples, n_tokens, activation_dim = 12, 2, 5, 8
    n_steps_dynamic = 4

    with h5py.File(activations_path, "w") as f:
        block8 = f.create_group("block8")
        token_init = f.create_group("token_initializer_outputs")
        for design_index in range(n_designs):
            design_id = f"design_{design_index:03d}"
            label = design_index % 2
            labels.append({"design_id": design_id, "label": label})

            for step in range(n_steps_dynamic):
                array = rng.standard_normal((n_samples, n_tokens, activation_dim)).astype(np.float32)
                if label == 1 and step == n_steps_dynamic - 1:
                    array[:, :, 3] += 4.0
                block8.create_group(design_id).create_dataset(str(step), data=array) \
                    if str(step) == "0" else block8[design_id].create_dataset(str(step), data=array)

            static_array = rng.standard_normal((n_samples, n_tokens, activation_dim)).astype(np.float32)
            if label == 1:
                static_array[:, :, 3] += 4.0
            token_init.create_group(design_id).create_dataset("0", data=static_array)

    labels_path = tmp_path / "labels.csv"
    pd.DataFrame(labels).to_csv(labels_path, index=False)
    return {
        "activations_path": str(activations_path),
        "labels_path": str(labels_path),
        "activation_dim": activation_dim,
        "n_designs": n_designs,
        "n_samples": n_samples,
    }
