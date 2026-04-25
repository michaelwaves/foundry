from pathlib import Path

import numpy as np
import pandas as pd

from detectors.pipelines.cache import build_feature_cache
from detectors.pipelines.labeled import aggregate_per_design, attach_labels
from detectors.scorers import SCORERS
from detectors.scorers.pipeline import score_all_features


def run_score(config: dict) -> pd.DataFrame:
    out_dir = Path(config["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    cache = build_feature_cache(config, out_dir / "features.npz")
    matrix, labels, _ = aggregate_per_design(cache, config.get("aggregation", "mean"),
                                             attach_labels(cache, config["labels_path"]))

    scorer = SCORERS[config.get("scorer", "auroc")]
    feature_ids = np.arange(matrix.shape[1])
    scores = score_all_features(matrix, feature_ids, labels, scorer,
                                p_value_top_k=int(config.get("p_value_top_k", 200)))
    scores.to_parquet(out_dir / "feature_scores.parquet", index=False)
    _write_top_k_markdown(scores, scorer, out_dir / "feature_scores_top.md", int(config.get("top_k", 50)))
    return scores


def _write_top_k_markdown(scores: pd.DataFrame, scorer, path: Path, top_k: int) -> None:
    null = scorer.null_value
    head = scores.head(top_k)
    lines = [f"# Top {len(head)} features by |{scorer.score_column} - {null}|", ""]
    lines.append(f"| feature_id | {scorer.score_column} | {scorer.p_value_column} | n_samples |")
    lines.append("|---|---|---|---|")
    for _, row in head.iterrows():
        lines.append(
            f"| {int(row['feature_id'])} | {row[scorer.score_column]:.3f} | "
            f"{row[scorer.p_value_column]:.4f} | {int(row['n_samples'])} |"
        )
    path.write_text("\n".join(lines))
