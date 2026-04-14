import json
from itertools import cycle
from pathlib import Path

import hydra
import torch
from omegaconf import DictConfig, OmegaConf

from sae.dataset import ActivationLoaderConfig, build_activation_loader
from sae.trainers import TRAINERS


def run_training(cfg: DictConfig) -> None:
    if cfg.get("activations_path") is None:
        raise ValueError("cfg.activations_path is required")

    save_dir = Path(cfg.out_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    loader, activation_dim = build_activation_loader(
        ActivationLoaderConfig(
            activations_path=cfg.activations_path,
            hook_name=cfg.hook_name,
            batch_size=cfg.batch_size,
            shuffle=cfg.shuffle,
        )
    )
    print(
        f"loaded {len(loader.dataset)} tokens, activation_dim={activation_dim}")

    trainer = _build_trainer(cfg, activation_dim)
    _save_config(save_dir, cfg, trainer)

    run = _init_wandb(cfg, trainer)
    save_steps = _get_save_steps(cfg)

    _train(trainer, loader, cfg.steps, cfg.log_every, save_dir, save_steps, run)

    _save_checkpoint(trainer, save_dir / "final.pt")
    if run is not None:
        run.finish()


def _train(trainer, loader, steps, log_every, save_dir, save_steps, run):
    iterator = cycle(loader)
    for step in range(steps):
        (batch,) = next(iterator)
        loss_value = trainer.update(step, batch)

        if step % log_every == 0:
            _log(step, steps, loss_value, trainer, run)
        if save_steps is not None and step in save_steps:
            _save_checkpoint(trainer, save_dir / f"step_{step}.pt")


def _build_trainer(cfg: DictConfig, activation_dim: int):
    if cfg.architecture not in TRAINERS:
        raise ValueError(
            f"unknown architecture {cfg.architecture}; pick from {list(TRAINERS)}")
    trainer_cls = TRAINERS[cfg.architecture]
    kwargs = OmegaConf.to_container(cfg.trainer, resolve=True)
    kwargs.update(dict(
        activation_dim=activation_dim,
        steps=cfg.steps,
        device=cfg.device,
        seed=cfg.seed,
    ))
    return trainer_cls(**kwargs)


def _save_config(save_dir: Path, cfg: DictConfig, trainer) -> None:
    with open(save_dir / "config.json", "w") as f:
        json.dump({"run": OmegaConf.to_container(cfg, resolve=True),
                  "trainer": trainer.config}, f, indent=2)


def _save_checkpoint(trainer, path: Path) -> None:
    torch.save({"ae": trainer.ae.state_dict(), "config": trainer.config}, path)


def _init_wandb(cfg: DictConfig, trainer):
    if not cfg.use_wandb:
        return None
    import wandb

    return wandb.init(
        project=cfg.wandb_project,
        name=f"{cfg.architecture}_{cfg.hook_name}",
        config={"run": OmegaConf.to_container(
            cfg, resolve=True), "trainer": trainer.config},
    )


def _log(step: int, total_steps: int, loss_value: float, trainer, run) -> None:
    stats = {"step": step, "loss": loss_value,
             "lr": trainer.scheduler.get_last_lr()[0]}
    stats.update(trainer.get_logging_parameters())
    print(f"[{step}/{total_steps}] " + " ".join(f"{k}={v:.4g}" if isinstance(v,
          float) else f"{k}={v}" for k, v in stats.items()))
    if run is not None:
        run.log(stats, step=step)


def _get_save_steps(cfg: DictConfig) -> set[int] | None:
    if not cfg.save_checkpoints:
        return None
    log_fractions = torch.logspace(-3, 0, 7).tolist()
    fractions = sorted({0.0} | set(log_fractions[:-1]))
    return {int(cfg.steps * fraction) for fraction in fractions}


if __name__ == "__main__":
    from sae.cli import app

    app()
