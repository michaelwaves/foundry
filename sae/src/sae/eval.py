import json
from dataclasses import asdict
from pathlib import Path
import torch
from omegaconf import DictConfig

from sae.dataset import ActivationLoaderConfig, build_activation_loader
from sae.evaluation import (
    build_feature_stats,
    compute_metrics,
    iter_design_activations,
    pick_interesting_features,
    render_feature_on_structure,
)
from sae.evaluation.feature_stats import top_firing_tokens
from sae.models.autoencoder import AutoEncoder
from sae.models.matryoshka_batch_topk import MatryoshkaBatchTopKSAE


DICT_CLASSES = {
    "MatryoshkaBatchTopKSAE": MatryoshkaBatchTopKSAE,
    "AutoEncoder": AutoEncoder,
}


def run_eval(cfg: DictConfig) -> None:
    output_dir = Path(cfg.out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sae = _load_sae(cfg.checkpoint_path, cfg.device)
    tokens, _ = _load_tokens(cfg)
    metrics = compute_metrics(sae, tokens, batch_size=cfg.eval_batch_size)
    _save_json(output_dir / "metrics.json", asdict(metrics))
    print(f"metrics: {asdict(metrics)}")

    designs = list(iter_design_activations(
        cfg.activations_path, cfg.hook_name, cfg.metadata_dir))
    stats = build_feature_stats(sae, designs, batch_size=cfg.eval_batch_size)
    feature_ids = pick_interesting_features(
        stats, num_features=cfg.num_features, min_fires=cfg.min_fires)
    _save_json(output_dir / "interesting_features.json",
               _feature_report(stats, feature_ids, designs))

    script_dir = output_dir / "pymol_scripts"
    for feature_id in feature_ids:
        hits_per_design = top_firing_tokens(
            stats, feature_id, top_k=cfg.top_residues)
        for design in designs:
            sample_hits = hits_per_design.get(design.design_id, [])
            if not sample_hits:
                continue
            best_sample = max(sample_hits, key=lambda h: h[2])[0]
            token_hits = [(token_idx, activation)
                          for s, token_idx, activation in sample_hits if s == best_sample]
            render_feature_on_structure(
                design_id=design.design_id,
                feature_id=feature_id,
                sample_idx=best_sample,
                pdb_path=design.generated_pdb_paths[best_sample],
                token_hits=token_hits,
                atom_array=design.atom_array,
                output_dir=script_dir,
            )

    print(f"wrote {len(feature_ids)} features to {script_dir}")


def _load_sae(checkpoint_path: str, device: str) -> torch.nn.Module:
    checkpoint = torch.load(
        checkpoint_path, map_location="cpu", weights_only=False)
    config = checkpoint["config"]
    cls = DICT_CLASSES[config["dict_class"]]
    if cls is MatryoshkaBatchTopKSAE:
        sae = cls(config["activation_dim"], config["dict_size"],
                  k=config["k"], group_sizes=config["group_sizes"])
    else:
        sae = cls(config["activation_dim"], config["dict_size"])
    sae.load_state_dict(checkpoint["ae"])
    return sae.to(device).eval()


def _load_tokens(cfg: DictConfig):
    loader, activation_dim = build_activation_loader(
        ActivationLoaderConfig(
            activations_path=cfg.activations_path,
            hook_name=cfg.hook_name,
            batch_size=cfg.eval_batch_size,
            shuffle=False,
        )
    )
    return loader.dataset.tensors[0], activation_dim


def _feature_report(stats, feature_ids, designs) -> dict:
    report: dict = {}
    for feature_id in feature_ids:
        hits = top_firing_tokens(stats, feature_id, top_k=5)
        serializable = {
            design_id: [{"sample": s, "token": t, "activation": a} for s, t, a in design_hits]
            for design_id, design_hits in hits.items()
        }
        report[str(feature_id)] = {
            "max_activation": float(stats.max_activation[feature_id].item()),
            "fire_rate": float(stats.fire_count[feature_id].item() / max(stats.token_count, 1)),
            "top_tokens": serializable,
        }
    return report


def _save_json(path: Path, payload) -> None:
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


if __name__ == "__main__":
    from sae.cli import app

    app()
