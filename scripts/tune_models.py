"""Feature-set ablation, class weighting and per-fold hyperparameter tuning on the walk-forward folds."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, make_scorer
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from preprocess_data import (
    CORE_FEATURE_COLUMNS,
    RESOLUTION_CONFIG,
    SYMBOLS,
    TIME_FEATURE_COLUMNS,
    feature_columns_for,
    walk_forward_splits,
)
from train_models import CLASSES, RANDOM_STATE, backtest, score_fold


ROOT = Path(__file__).resolve().parent.parent
VALIDATION_FRACTION = 0.2
ESTIMATOR_THREADS = 4
VARIANTS = {
    "all_default": {"features": "all", "balanced": False, "tuned": False},
    "core_default": {"features": "core", "balanced": False, "tuned": False},
    "all_balanced": {"features": "all", "balanced": True, "tuned": False},
    "core_tuned": {"features": "core", "balanced": False, "tuned": True},
    "all_tuned": {"features": "all", "balanced": False, "tuned": True},
}
MODEL_NAMES = ("logistic", "random_forest", "xgboost")
PARAM_GRIDS = {
    "logistic": {"model__C": [0.01, 0.1, 1.0, 10.0]},
    "random_forest": {"max_depth": [3, 5, 8], "min_samples_leaf": [5, 20]},
    "xgboost": {"max_depth": [2, 3, 5], "learning_rate": [0.03, 0.1]},
}
MACRO_F1 = make_scorer(f1_score, average="macro", labels=CLASSES, zero_division=0)


def select_features(resolution: str, feature_set: str) -> list[str]:
    columns = feature_columns_for(resolution)
    if feature_set == "all":
        return list(columns)
    keep = {*CORE_FEATURE_COLUMNS, *TIME_FEATURE_COLUMNS}
    return [column for column in columns if column in keep]


def make_estimator(name: str, balanced: bool):
    class_weight = "balanced" if balanced else None
    if name == "logistic":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1000, class_weight=class_weight, random_state=RANDOM_STATE
                    ),
                ),
            ]
        )
    if name == "random_forest":
        return RandomForestClassifier(
            n_estimators=300, class_weight=class_weight,
            random_state=RANDOM_STATE, n_jobs=ESTIMATOR_THREADS,
        )
    return XGBClassifier(
        n_estimators=300, objective="multi:softprob", eval_metric="mlogloss",
        random_state=RANDOM_STATE, n_jobs=ESTIMATOR_THREADS,
    )


def fit_kwargs(name: str, balanced: bool, y: np.ndarray) -> dict:
    if name == "xgboost" and balanced:
        return {"sample_weight": compute_sample_weight("balanced", y)}
    return {}


def tune(name: str, estimator, features: np.ndarray, y: np.ndarray, gap: int):
    split_at = len(features) - int(len(features) * VALIDATION_FRACTION)
    single_split = [(np.arange(split_at - gap), np.arange(split_at, len(features)))]
    search = GridSearchCV(
        estimator, PARAM_GRIDS[name], scoring=MACRO_F1, cv=single_split, refit=True
    )
    search.fit(features, y)
    return search.best_estimator_, search.best_params_


def run_symbol(symbol: str, resolution: str, processed_root: Path):
    data = pd.read_csv(processed_root / resolution / f"{symbol}.csv")
    y = data["label"].to_numpy() + 1
    r_next = data["r_next"].to_numpy()
    times = data["time"].to_numpy()
    gap = RESOLUTION_CONFIG[resolution]["gap"]
    splits = list(walk_forward_splits(len(data), resolution))
    fold_rows, param_rows, prediction_frames = [], [], []

    for variant, config in VARIANTS.items():
        features = data[select_features(resolution, config["features"])].to_numpy()
        for fold, (train_idx, test_idx) in enumerate(splits, start=1):
            for name in MODEL_NAMES:
                estimator = make_estimator(name, config["balanced"])
                started = time.perf_counter()
                if config["tuned"]:
                    estimator, params = tune(name, estimator, features[train_idx], y[train_idx], gap)
                    param_rows.append(
                        {
                            "symbol": symbol, "variant": variant, "fold": fold, "model": name,
                            "params": json.dumps(params, sort_keys=True),
                        }
                    )
                else:
                    estimator.fit(
                        features[train_idx], y[train_idx],
                        **fit_kwargs(name, config["balanced"], y[train_idx]),
                    )
                fit_seconds = time.perf_counter() - started
                proba = estimator.predict_proba(features[test_idx])
                y_pred = CLASSES[proba.argmax(axis=1)]
                train_proba = estimator.predict_proba(features[train_idx])
                train_scores = score_fold(y[train_idx], CLASSES[train_proba.argmax(axis=1)], train_proba)
                fold_rows.append(
                    {
                        "symbol": symbol, "variant": variant, "fold": fold, "model": name,
                        "test_start": times[test_idx[0]], "test_end": times[test_idx[-1]],
                        **score_fold(y[test_idx], y_pred, proba),
                        **{f"train_{key}": value for key, value in train_scores.items()},
                        "fit_seconds": fit_seconds,
                    }
                )
                prediction_frames.append(
                    pd.DataFrame(
                        {
                            "symbol": symbol, "variant": variant, "model": name,
                            "time": times[test_idx], "y_true": y[test_idx], "y_pred": y_pred,
                            "p_down": proba[:, 0], "p_flat": proba[:, 1], "p_up": proba[:, 2],
                            "r_next": r_next[test_idx],
                        }
                    )
                )
        print(f"{symbol} {variant} done", flush=True)

    predictions = pd.concat(prediction_frames, ignore_index=True)
    backtest_rows = [
        {"symbol": symbol, "variant": variant, "model": name,
         **backtest(frame["y_pred"].to_numpy(), frame["r_next"].to_numpy())}
        for (variant, name), frame in predictions.groupby(["variant", "model"])
    ]
    return pd.DataFrame(fold_rows), predictions, pd.DataFrame(backtest_rows), pd.DataFrame(param_rows)


def summarize(fold_metrics: pd.DataFrame) -> pd.DataFrame:
    pooled = fold_metrics.assign(symbol="ALL")
    return (
        pd.concat([fold_metrics, pooled])
        .groupby(["symbol", "variant", "model"])[
            ["accuracy", "f1_macro", "roc_auc", "train_f1_macro", "fit_seconds"]
        ]
        .agg(["mean", "std"])
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution", default="1D")
    parser.add_argument("--symbols", nargs="+", default=list(SYMBOLS))
    parser.add_argument("--processed-root", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    worker = partial(run_symbol, resolution=args.resolution, processed_root=args.processed_root)
    with ProcessPoolExecutor(max_workers=len(args.symbols)) as pool:
        results = list(pool.map(worker, args.symbols))

    output_dir = args.output_root / args.resolution / "tuning"
    output_dir.mkdir(parents=True, exist_ok=True)
    names = ("fold_metrics", "predictions", "backtest", "best_params")
    for index, name in enumerate(names):
        pd.concat([r[index] for r in results], ignore_index=True).to_csv(
            output_dir / f"{name}.csv", index=False
        )
    fold_metrics = pd.read_csv(output_dir / "fold_metrics.csv")
    summary = summarize(fold_metrics)
    summary.to_csv(output_dir / "summary.csv")

    pd.set_option("display.width", 200)
    print(summary.loc["ALL"].round(4).to_string())


if __name__ == "__main__":
    main()
