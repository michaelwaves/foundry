import pytest
import torch

from sae.activation_buffer import _apply_steering
from sae.steering.compose import _make_callback
from sae.steering.config import SteeringSpec, parse_specs


# ---------- _apply_steering ----------

def test_no_direction_returns_input_unchanged():
    out = torch.randn(2, 5, 8)
    result = _apply_steering(out, (None, None))
    assert torch.equal(result, out)


def test_add_broadcasts_across_batch_and_length():
    out = torch.zeros(2, 5, 8)
    direction = torch.arange(8).float()
    result = _apply_steering(out, (direction, "add"))
    assert torch.allclose(result, direction.expand_as(out))


def test_ablate_zeros_projection_along_direction():
    direction = torch.tensor([1.0, 0.0, 0.0, 0.0])
    out = torch.tensor([[3.0, 4.0, 0.0, 0.0]]).reshape(1, 1, 4)
    result = _apply_steering(out, (direction, "ablate"))
    projection = (result @ direction).item()
    assert projection == pytest.approx(0.0, abs=1e-6)
    assert result[0, 0, 1].item() == pytest.approx(4.0)


def test_unknown_kind_raises():
    out = torch.zeros(1, 1, 4)
    with pytest.raises(ValueError):
        _apply_steering(out, (torch.ones(4), "boost"))


def test_dtype_preserved():
    out = torch.zeros(1, 1, 4, dtype=torch.bfloat16)
    direction = torch.ones(4, dtype=torch.float32)
    result = _apply_steering(out, (direction, "add"))
    assert result.dtype == torch.bfloat16


# ---------- compose / _make_callback ----------

def test_steer_specs_sum_when_both_fire():
    s1 = SteeringSpec(mode="raw_diff", vector_path="ignored", coeff=1.0)
    s2 = SteeringSpec(mode="raw_diff", vector_path="ignored", coeff=1.0)
    d1 = torch.tensor([1.0, 0.0])
    d2 = torch.tensor([0.0, 1.0])
    cb = _make_callback([s1, s2], [d1, d2], [], None)
    direction, kind = cb(0)
    assert kind == "add"
    assert torch.equal(direction, torch.tensor([1.0, 1.0]))


def test_skipped_step_returns_none():
    s = SteeringSpec(mode="raw_diff", vector_path="ignored", coeff=1.0, apply_at_steps=[5])
    cb = _make_callback([s], [torch.ones(2)], [], None)
    assert cb(0) == (None, None)
    assert cb(5)[1] == "add"


def test_ablate_takes_priority_over_steer():
    steer_spec = SteeringSpec(mode="raw_diff", vector_path="ignored", coeff=1.0)
    ablate_spec = SteeringSpec(mode="raw_diff", vector_path="ignored", coeff=1.0, type="ablate")
    cb = _make_callback([steer_spec], [torch.ones(2)], [ablate_spec], torch.tensor([1.0, 0.0]))
    direction, kind = cb(0)
    assert kind == "ablate"
    assert torch.equal(direction, torch.tensor([1.0, 0.0]))


# ---------- parse_specs ----------

def test_parse_specs_round_trips_from_dict():
    parsed = parse_specs({
        "block12": [
            {"mode": "sae_feature", "sae_path": "x.pt", "feature_id": 7, "alpha": 2.0},
            {"mode": "raw_diff", "vector_path": "v.pt", "coeff": 0.5, "type": "ablate"},
        ]
    })
    assert list(parsed) == ["block12"]
    assert parsed["block12"][0].mode == "sae_feature"
    assert parsed["block12"][0].alpha == 2.0
    assert parsed["block12"][1].type == "ablate"


def test_parse_specs_rejects_missing_required_fields():
    with pytest.raises(ValueError):
        parse_specs({"b": [{"mode": "sae_feature", "feature_id": 1}]})  # no sae_path
    with pytest.raises(ValueError):
        parse_specs({"b": [{"mode": "raw_diff"}]})  # no vector_path
    with pytest.raises(ValueError):
        parse_specs({"b": [{"mode": "garbage"}]})


def test_parse_empty_returns_empty():
    assert parse_specs(None) == {}
    assert parse_specs({}) == {}
