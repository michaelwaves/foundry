"""Shared Hydra plumbing for the rf3 / rfd3 collectors.

`saffron_searchpath_override()` exposes saffron's own Hydra config groups
(hooks, steering) to the underlying model's compose call.

`promote_to_default()` rewrites ad-hoc CLI overrides like `hooks=rf3_default`
to `+hooks=rf3_default`, so users don't have to type the `+` prefix when
the model's inference.yaml doesn't declare hooks/steering as default groups.
"""
from pathlib import Path


def saffron_searchpath_override() -> str:
    configs_dir = Path(__file__).resolve().parent.parent / "configs"
    return f"hydra.searchpath=[file://{configs_dir}]"


def promote_to_default(overrides: list[str], groups: tuple[str, ...]) -> list[str]:
    promoted: list[str] = []
    for arg in overrides:
        if any(arg.startswith(f"{group}=") for group in groups):
            promoted.append(f"+{arg}")
        else:
            promoted.append(arg)
    return promoted
