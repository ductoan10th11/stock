"""Fit the final pooled ensemble3 on all labeled rows and save a self-contained model bundle."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from xgboost import XGBClassifier

from panel_data import FEATURE_SETS, THRESHOLD, build_panel, load_index, load_universe
from panel_experiments import DEFAULT_MODELS, DOWN, FLAT, RANDOM_STATE, UP, make_model


ROOT = Path(__file__).resolve().parent.parent
FEATURE_SET = "full"
LABEL_COLUMN = "label_abs"
LABEL_OFFSET = 1
VERIFY_ROWS = 500


def git_state() -> dict:
    def run(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False).stdout.strip()

    return {"git_commit": run("rev-parse", "HEAD"), "git_dirty": bool(run("status", "--porcelain", "--untracked-files=no"))}


def save_models(models: dict, output_dir: Path) -> None:
    joblib.dump(models["logistic"], output_dir / "logistic.joblib", compress=3)
    joblib.dump(models["random_forest"], output_dir / "random_forest.joblib", compress=3)
    models["xgboost"].save_model(output_dir / "xgboost.json")


def load_bundle(directory: Path) -> dict:
    metadata = json.loads((directory / "metadata.json").read_text())
    xgb = XGBClassifier(device="cpu")
    xgb.load_model(directory / "xgboost.json")
    models = {
        "logistic": joblib.load(directory / "logistic.joblib"),
        "random_forest": joblib.load(directory / "random_forest.joblib"),
        "xgboost": xgb,
    }
    return {"models": models, "metadata": metadata}


def ensemble_probabilities(bundle: dict, frame: pd.DataFrame) -> pd.DataFrame:
    features = frame[bundle["metadata"]["feature_columns"]].to_numpy()
    averaged = np.mean([model.predict_proba(features) for model in bundle["models"].values()], axis=0)
    result = pd.DataFrame(averaged, columns=["p_down", "p_flat", "p_up"], index=frame.index)
    result["score"] = result["p_up"] - result["p_down"]
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "models" / "ensemble3_pooled_1D")
    parser.add_argument("--no-gpu", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    panel = build_panel(load_universe(), load_index())
    columns = list(FEATURE_SETS[FEATURE_SET])
    features = panel[columns].to_numpy()
    labels = panel[LABEL_COLUMN].to_numpy() + LABEL_OFFSET
    print(f"{len(panel)} rows, {panel['symbol'].nunique()} symbols, {panel['time'].min().date()} to {panel['time'].max().date()}")

    models = {}
    for name in DEFAULT_MODELS:
        started = time.perf_counter()
        models[name] = make_model(name, n_jobs=-1, gpu=not args.no_gpu).fit(features, labels)
        print(f"{name} fitted in {time.perf_counter() - started:.1f}s", flush=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_models(models, args.output_dir)
    metadata = {
        "model": "ensemble3_pooled_1D",
        "members": list(DEFAULT_MODELS),
        "combination": "mean of class probabilities",
        "score": "p_up - p_down",
        "feature_set": FEATURE_SET,
        "feature_columns": columns,
        "class_order": {"down": DOWN, "flat": FLAT, "up": UP},
        "label_column": LABEL_COLUMN,
        "label_offset": LABEL_OFFSET,
        "label_threshold": THRESHOLD,
        "symbols": sorted(panel["symbol"].unique()),
        "train_rows": len(panel),
        "trained_from": str(panel["time"].min().date()),
        "trained_until": str(panel["time"].max().date()),
        "random_state": RANDOM_STATE,
        "xgboost_trained_on_gpu": not args.no_gpu,
        "versions": {
            "python": platform.python_version(), "scikit_learn": sklearn.__version__,
            "xgboost": xgboost.__version__, "numpy": np.__version__, "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
        **git_state(),
    }
    (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

    sample = panel.tail(VERIFY_ROWS)
    live = pd.DataFrame(
        np.mean([model.predict_proba(sample[columns].to_numpy()) for model in models.values()], axis=0),
        columns=["p_down", "p_flat", "p_up"],
    )
    reloaded = ensemble_probabilities(load_bundle(args.output_dir), sample).reset_index(drop=True)
    gap = (live[["p_down", "p_flat", "p_up"]] - reloaded[["p_down", "p_flat", "p_up"]]).abs().max().max()
    print(f"max probability difference after reload on {VERIFY_ROWS} rows: {gap:.2e}")
    for path in sorted(args.output_dir.iterdir()):
        print(f"{path.name}: {path.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
