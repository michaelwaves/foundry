import torch

from detectors.features.identity import IdentityExtractor
from detectors.features.pooling import PoolingStrategy, pool_design
from detectors.features.sae_encode import SAEEncodeExtractor


def test_identity_passthrough():
    activations = torch.randn(5, 7)
    extractor = IdentityExtractor(feature_dim=7)
    result = extractor.transform(activations)
    assert torch.equal(result, activations)


def test_pooling_max_reduces_steps_and_tokens():
    # (n_samples, n_steps, n_tokens, dim) → (n_samples, dim) for design-level pooling
    activations = torch.zeros(2, 3, 4, 5)
    activations[0, 1, 2, :] = 9.0
    pooled = pool_design(activations, PoolingStrategy.MAX)
    assert pooled.shape == (2, 5)
    assert (pooled[0] == 9.0).all()


def test_pooling_last_step_picks_final_step():
    activations = torch.arange(2 * 3 * 4 * 5, dtype=torch.float32).reshape(2, 3, 4, 5)
    pooled = pool_design(activations, PoolingStrategy.LAST_STEP)
    assert pooled.shape == (2, 5)
    expected = activations[:, -1, :, :].mean(dim=1)
    torch.testing.assert_close(pooled, expected)


def test_pooling_per_token_keeps_token_axis():
    activations = torch.randn(2, 3, 4, 5)
    pooled = pool_design(activations, PoolingStrategy.PER_TOKEN)
    assert pooled.shape == (2, 4, 5)


def test_sae_encode_round_trip(tmp_path):
    from sae.models.matryoshka_batch_topk import MatryoshkaBatchTopKSAE

    activation_dim, dict_size = 8, 16
    sae = MatryoshkaBatchTopKSAE(activation_dim, dict_size, k=4, group_sizes=[8, 8])
    sae.threshold.fill_(0.0)
    checkpoint_path = tmp_path / "sae.pt"
    torch.save({"ae": sae.state_dict(), "config": {"dict_class": "MatryoshkaBatchTopKSAE",
               "activation_dim": activation_dim, "dict_size": dict_size, "k": 4, "group_sizes": [8, 8]}},
               checkpoint_path)

    extractor = SAEEncodeExtractor.from_checkpoint(str(checkpoint_path), device="cpu")
    activations = torch.randn(10, activation_dim)
    features = extractor.transform(activations)
    assert features.shape == (10, dict_size)
    assert extractor.feature_dim == dict_size
