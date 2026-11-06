"""Tables and figures that analyze walk-forward results: overfitting, errors, importance, stability."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from sklearn.metrics import confusion_matrix

from preprocess_data import BASE_FEATURE_COLUMNS


ROOT = Path(__file__).resolve().parent.parent
MODELS = {
    "logistic": ("Logistic Regression", "#2a78d6"),
    "random_forest": ("Random Forest", "#eb6834"),
    "xgboost": ("XGBoost", "#1baf7a"),
}
BASELINE_COLOR = "#6b6a66"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
CLASS_NAMES = ["Giảm", "Ngang", "Tăng"]
CORE_FEATURES = BASE_FEATURE_COLUMNS[:12]
ROLLING_FOLDS = 5

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "text.color": INK,
        "axes.labelcolor": INK_SECONDARY,
        "xtick.color": INK_SECONDARY,
        "ytick.color": INK_SECONDARY,
    }
)


def overfitting_table(folds: pd.DataFrame) -> pd.DataFrame:
    models = folds[folds["model"].isin(MODELS)]
    metrics = ["accuracy", "f1_macro", "roc_auc"]
    train = models.groupby("model")[[f"train_{m}" for m in metrics]].mean()
    test = models.groupby("model")[metrics].mean()
    table = pd.concat(
        {"train": train.rename(columns=lambda c: c.removeprefix("train_")), "test": test}, axis=1
    )
    for metric in metrics:
        table[("gap", metric)] = table[("train", metric)] - table[("test", metric)]
    return table.loc[list(MODELS)]


def plot_overfitting(table: pd.DataFrame, random_f1: float, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    panels = [("f1_macro", "F1 macro", random_f1), ("roc_auc", "ROC-AUC", 0.5)]
    for ax, (metric, title, reference) in zip(axes, panels):
        for i, (key, (label, color)) in enumerate(MODELS.items()):
            train, test = table.loc[key, ("train", metric)], table.loc[key, ("test", metric)]
            ax.bar(i - 0.2, train, 0.38, color=color, alpha=0.35, hatch="///", edgecolor=color)
            ax.bar(i + 0.2, test, 0.38, color=color)
            ax.text(i - 0.2, train + 0.012, f"{train:.2f}", ha="center", fontsize=9, color=INK)
            ax.text(i + 0.2, test + 0.012, f"{test:.2f}", ha="center", fontsize=9, color=INK)
        ax.axhline(reference, color=BASELINE_COLOR, linestyle="--", linewidth=1)
        ax.set_xticks(range(len(MODELS)), [label for label, _ in MODELS.values()])
        ax.set_ylim(0, 1.08)
        ax.set_title(title, loc="left", fontsize=11)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Giá trị trung bình qua các fold")
    handles = [
        Patch(facecolor="#d9d8d4", edgecolor="#9b9a96", hatch="///", label="Tập huấn luyện"),
        Patch(facecolor="#9b9a96", label="Tập kiểm tra (walk-forward)"),
        Line2D([], [], color=BASELINE_COLOR, linestyle="--", label="Mức ngẫu nhiên"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def pooled_confusion(predictions: pd.DataFrame) -> dict[str, np.ndarray]:
    return {
        key: confusion_matrix(frame["y_true"], frame["y_pred"], labels=[0, 1, 2])
        for key, frame in predictions.groupby("model")
        if key in MODELS
    }


def plot_confusion(matrices: dict[str, np.ndarray], path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, (key, (label, _)) in zip(axes, MODELS.items()):
        counts = matrices[key]
        share = counts / counts.sum(axis=1, keepdims=True)
        ax.imshow(share, cmap="Blues", vmin=0, vmax=0.8)
        for row in range(3):
            for col in range(3):
                ax.text(col, row, f"{share[row, col]:.0%}\n({counts[row, col]})", ha="center", va="center",
                        fontsize=10, color="white" if share[row, col] > 0.5 else INK)
        ax.set_xticks(range(3), CLASS_NAMES)
        ax.set_yticks(range(3), CLASS_NAMES)
        ax.set_xlabel("Nhãn dự đoán")
        ax.set_title(label, loc="left", fontsize=11)
        ax.grid(False)
    axes[0].set_ylabel("Nhãn thật")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def predicted_class_share(predictions: pd.DataFrame) -> pd.DataFrame:
    models = predictions[predictions["model"].isin(MODELS)]
    share = pd.crosstab(models["model"], models["y_pred"], normalize="index")
    truth = predictions[predictions["model"] == "logistic"]["y_true"].value_counts(normalize=True)
    share.loc["thực tế"] = truth.reindex(share.columns)
    return share.rename(columns=dict(enumerate(CLASS_NAMES)))


def importance_table(importances: pd.DataFrame) -> pd.DataFrame:
    return importances.groupby(["model", "feature"])["importance"].mean().unstack("model")


def plot_importance(table: pd.DataFrame, path: Path, top: int = 10) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, key in zip(axes, ["random_forest", "xgboost"]):
        label, color = MODELS[key]
        best = table[key].nlargest(top).sort_values()
        ax.barh(best.index, best.values, color=color, height=0.65)
        for y, value in enumerate(best.values):
            ax.text(value + 0.0015, y, f"{value:.3f}", va="center", fontsize=8, color=INK)
        ax.set_title(label, loc="left", fontsize=11)
        ax.set_xlabel("Độ quan trọng trung bình (qua các fold và mã)")
        ax.grid(axis="y", visible=False)
        ax.set_xlim(0, best.max() * 1.15)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def feature_group_share(table: pd.DataFrame) -> pd.DataFrame:
    is_core = table.index.isin(CORE_FEATURES)
    return pd.DataFrame(
        {"nhóm lõi (12)": table[is_core].sum(), "nhóm bổ trợ (13)": table[~is_core].sum()}
    ).loc[["random_forest", "xgboost"]]


def plot_learning_curve(folds: pd.DataFrame, path: Path) -> None:
    random_f1 = folds[folds["model"] == "random"]["f1_macro"].mean()
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, (key, (label, color)) in zip(axes, MODELS.items()):
        by_fold = folds[folds["model"] == key].groupby("train_size")[["train_f1_macro", "f1_macro"]].mean()
        smooth = by_fold.rolling(ROLLING_FOLDS, min_periods=1, center=True).mean()
        ax.plot(smooth.index, smooth["train_f1_macro"], color=color, linestyle="--", linewidth=2, label="Huấn luyện")
        ax.plot(smooth.index, smooth["f1_macro"], color=color, linewidth=2, label="Kiểm tra")
        ax.axhline(random_f1, color=BASELINE_COLOR, linestyle=":", linewidth=1.2, label="Ngẫu nhiên")
        ax.set_title(label, loc="left", fontsize=11)
        ax.set_xlabel("Số phiên trong tập huấn luyện")
        ax.legend(frameon=False, fontsize=8, loc="center right")
    axes[0].set_ylabel(f"F1 macro (trung bình trượt {ROLLING_FOLDS} fold)")
    axes[0].set_ylim(0.2, 1.02)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def yearly_f1(folds: pd.DataFrame) -> pd.DataFrame:
    keep = folds[folds["model"].isin([*MODELS, "random"])]
    years = pd.to_datetime(keep["test_start"]).dt.year
    return keep.groupby([years.rename("year"), "model"])["f1_macro"].mean().unstack("model")


def plot_yearly_f1(table: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    for key, (label, color) in MODELS.items():
        ax.plot(table.index, table[key], color=color, marker="o", linewidth=2, markersize=6, label=label)
    ax.plot(table.index, table["random"], color=BASELINE_COLOR, linestyle="--", linewidth=1.5, label="Ngẫu nhiên")
    ax.set_xlabel("Năm của khối kiểm tra")
    ax.set_ylabel("F1 macro trung bình (gộp 4 mã)")
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution", default="1D")
    parser.add_argument("--results-root", type=Path, default=ROOT / "results")
    parser.add_argument(
        "--figure-dir", type=Path, default=ROOT / "docs" / "project-report" / "bao-cao" / "images"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = args.results_root / args.resolution
    folds = pd.read_csv(results / "fold_metrics.csv")
    predictions = pd.read_csv(results / "predictions.csv")
    importances = pd.read_csv(results / "feature_importance.csv")
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 200)

    overfit = overfitting_table(folds)
    plot_overfitting(overfit, folds[folds["model"] == "random"]["f1_macro"].mean(),
                     args.figure_dir / "overfitting.png")
    print("== Train vs test (trung bình qua fold, gộp 4 mã) ==")
    print(overfit.round(3).to_string())

    matrices = pooled_confusion(predictions)
    plot_confusion(matrices, args.figure_dir / "confusion_matrix.png")
    print("\n== Ma trận nhầm lẫn gộp 4 mã (hàng: thật; cột: dự đoán; Giảm, Ngang, Tăng) ==")
    for key, counts in matrices.items():
        print(key)
        print(counts)
    print("\n== Tỷ lệ nhãn dự đoán ==")
    print(predicted_class_share(predictions).round(3).to_string())

    importance = importance_table(importances)
    plot_importance(importance, args.figure_dir / "feature_importance.png")
    print("\n== Top 10 feature importance ==")
    for key in ["random_forest", "xgboost"]:
        print(key)
        print(importance[key].nlargest(10).round(4).to_string())
    print("\n== Tỷ trọng importance theo nhóm đặc trưng ==")
    print(feature_group_share(importance).round(3).to_string())

    plot_learning_curve(folds, args.figure_dir / "learning_curve.png")

    yearly = yearly_f1(folds)
    plot_yearly_f1(yearly, args.figure_dir / "f1_by_year.png")
    print("\n== F1 macro theo năm của khối kiểm tra ==")
    print(yearly.round(3).to_string())


if __name__ == "__main__":
    main()
