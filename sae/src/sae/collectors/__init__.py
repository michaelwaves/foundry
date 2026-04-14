from sae.collectors.rfd3 import collect as _rfd3_collect

_REGISTRY = {"rfd3": _rfd3_collect}


def dispatch(model: str, overrides: list[str]) -> None:
    if model not in _REGISTRY:
        choices = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"unknown model '{model}'. choices: {choices}")
    _REGISTRY[model](overrides)
