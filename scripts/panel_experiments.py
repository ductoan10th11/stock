"""Walk-forward experiments on the daily panel: pooled vs per-symbol, labels, models, two-stage, portfolio."""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from panel_data import FEATURE_SETS, ROOT


RANDOM_STATE = 42
TRAIN_INITIAL = 750
TEST_SIZE = 63
GAP = 1
MIN_SYMBOL_TRAIN_ROWS = 500
CONFIRM_START = pd.Timestamp("2025-01-01")
CLASSES = np.array([0, 1, 2])
DOWN, FLAT, UP = 0, 1, 2
BASELINE_DRAWS = 50
TOP_FRACTION = 0.2
STICKY_BUFFER = 2.0
MIN_HOLDINGS = 3
BUY_FEE = 0.0015
SELL_FEE = 0.0015 + 0.001
TRADING_DAYS = 252
BOOTSTRAP_RUNS = 2000
BOOTSTRAP_BLOCK = 10
MODEL_NAMES = ("logistic", "random_forest", "xgboost", "mlp")
DEFAULT_MODELS = ("logistic", "random_forest", "xgboost")
ENSEMBLES = {"ensemble3": ("logistic", "random_forest", "xgboost"), "ensemble4": MODEL_NAMES}


class TorchMLP:
    def __init__(self, seeds: int = 3, hidden: int = 128, max_epochs: int = 40, patience: int = 5,
                 validation_fraction: float = 0.15):
        self.seeds, self.hidden, self.max_epochs = seeds, hidden, max_epochs
        self.patience, self.validation_fraction = patience, validation_fraction

    def fit(self, features: np.ndarray, y: np.ndarray):
        import torch
        from torch import nn

        self.torch, self.device = torch, "cuda"
        self.mean, self.std = features.mean(axis=0), features.std(axis=0) + 1e-9
        self.n_classes = int(y.max()) + 1
        scaled = self._scale(features)
        split = len(scaled) - int(len(scaled) * self.validation_fraction)
        x_train = torch.tensor(scaled[:split], device=self.device)
        y_train = torch.tensor(y[:split], device=self.device)
        x_valid = torch.tensor(scaled[split:], device=self.device)
        y_valid = torch.tensor(y[split:], device=self.device)
        self.networks = []
        for seed in range(self.seeds):
            torch.manual_seed(RANDOM_STATE + seed)
            network = nn.Sequential(
                nn.Linear(features.shape[1], self.hidden), nn.ReLU(), nn.Dropout(0.3),
                nn.Linear(self.hidden, self.hidden // 2), nn.ReLU(), nn.Dropout(0.3),
                nn.Linear(self.hidden // 2, self.n_classes),
            ).to(self.device)
            optimizer = torch.optim.AdamW(network.parameters(), lr=1e-3, weight_decay=1e-2)
            best, best_state, stale = np.inf, None, 0
            for _ in range(self.max_epochs):
                network.train()
                order = torch.randperm(len(x_train), device=self.device)
                for start in range(0, len(order), 512):
                    batch = order[start:start + 512]
                    optimizer.zero_grad()
                    nn.functional.cross_entropy(network(x_train[batch]), y_train[batch]).backward()
                    optimizer.step()
                network.eval()
                with torch.no_grad():
                    loss = nn.functional.cross_entropy(network(x_valid), y_valid).item()
                if loss < best:
                    best, stale = loss, 0
                    best_state = {k: v.clone() for k, v in network.state_dict().items()}
                else:
                    stale += 1
                    if stale >= self.patience:
                        break
            network.load_state_dict(best_state)
            network.eval()
            self.networks.append(network)
        return self

    def _scale(self, features: np.ndarray) -> np.ndarray:
        return np.clip((features - self.mean) / self.std, -5, 5).astype(np.float32)

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        torch = self.torch
        data = torch.tensor(self._scale(features), device=self.device)
        with torch.no_grad():
            probabilities = [torch.softmax(net(data), dim=1).cpu().numpy() for net in self.networks]
        return np.mean(probabilities, axis=0)


def make_model(name: str, n_jobs: int, gpu: bool):
    if name == "logistic":
        return Pipeline(
            [("scaler", StandardScaler()),
             ("model", LogisticRegression(C=0.1, max_iter=500, random_state=RANDOM_STATE))]
        )
    if name == "random_forest":
        return RandomForestClassifier(
            n_estimators=300, min_samples_leaf=50, n_jobs=n_jobs, random_state=RANDOM_STATE
        )
    if name == "xgboost":
        return XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
            min_child_weight=20, tree_method="hist", device="cuda" if gpu else "cpu",
            n_jobs=n_jobs, random_state=RANDOM_STATE,
        )
    if name == "mlp":
        return TorchMLP()
    raise ValueError(name)


def class_probabilities(model, features: np.ndarray) -> np.ndarray:
    proba = model.predict_proba(features)
    present = getattr(model, "classes_", None)
    if present is None or len(present) == proba.shape[1] and list(present) == list(range(proba.shape[1])):
        return proba
    full = np.zeros((len(features), proba.shape[1]))
    full[:, present] = proba
    return full


def fit_predict(name: str, task: str, x_train, y_train, x_test, n_jobs: int, gpu: bool) -> np.ndarray:
    if task == "direct":
        model = make_model(name, n_jobs, gpu).fit(x_train, y_train)
        proba = model.predict_proba(x_test)
        classes = getattr(model, "classes_", np.arange(proba.shape[1]))
        out = np.zeros((len(x_test), 3))
        out[:, np.asarray(classes, dtype=int)] = proba
        return out
    flat_model = make_model(name, n_jobs, gpu).fit(x_train, (y_train == FLAT).astype(int))
    directional = y_train != FLAT
    up_model = make_model(name, n_jobs, gpu).fit(x_train[directional], (y_train[directional] == UP).astype(int))
    p_flat = flat_model.predict_proba(x_test)[:, 1]
    q_up = up_model.predict_proba(x_test)[:, 1]
    return np.column_stack([(1 - p_flat) * (1 - q_up), p_flat, (1 - p_flat) * q_up])


def date_folds(panel: pd.DataFrame, gap: int = GAP):
    dates = np.sort(panel["time"].unique())
    for fold, start in enumerate(range(TRAIN_INITIAL + gap, len(dates) - TEST_SIZE + 1, TEST_SIZE), start=1):
        yield fold, dates[start - gap - 1], dates[start], dates[start + TEST_SIZE - 1]


def collect(frame: pd.DataFrame, fold: int, test_start, name: str, proba, y_train, y_test, train_prior):
    return pd.DataFrame(
        {
            "fold": fold, "test_start": test_start, "time": frame["time"].to_numpy(),
            "symbol": frame["symbol"].to_numpy(), "model": name, "y": y_test,
            "p_down": proba[:, DOWN], "p_flat": proba[:, FLAT], "p_up": proba[:, UP],
            "r_next": frame["r_next"].to_numpy(), "r_rel": frame["r_rel"].to_numpy(),
            "prior_down": train_prior[DOWN], "prior_flat": train_prior[FLAT], "prior_up": train_prior[UP],
        }
    )


def run_pooled(panel, label_column, columns, model_names, task, gpu, gap=GAP) -> pd.DataFrame:
    outputs = []
    for fold, train_end, test_start, test_end in date_folds(panel, gap):
        train = panel[panel["time"] <= train_end]
        test = panel[(panel["time"] >= test_start) & (panel["time"] <= test_end)]
        y_train = train[label_column].to_numpy() + 1
        y_test = test[label_column].to_numpy() + 1
        prior = np.bincount(y_train, minlength=3) / len(y_train)
        x_train, x_test = train[columns].to_numpy(), test[columns].to_numpy()
        for name in model_names:
            started = time.perf_counter()
            proba = fit_predict(name, task, x_train, y_train, x_test, n_jobs=-1, gpu=gpu)
            outputs.append(collect(test, fold, test_start, name, proba, y_train, y_test, prior))
            print(f"fold {fold} {name} {time.perf_counter() - started:.1f}s", flush=True)
    return pd.concat(outputs, ignore_index=True)


def run_one_symbol(symbol, frame, folds, label_column, columns, model_names, task) -> pd.DataFrame:
    outputs = []
    for fold, train_end, test_start, test_end in folds:
        train = frame[frame["time"] <= train_end]
        test = frame[(frame["time"] >= test_start) & (frame["time"] <= test_end)]
        if len(train) < MIN_SYMBOL_TRAIN_ROWS or test.empty:
            continue
        y_train = train[label_column].to_numpy() + 1
        if len(np.unique(y_train)) < 3:
            continue
        y_test = test[label_column].to_numpy() + 1
        prior = np.bincount(y_train, minlength=3) / len(y_train)
        for name in model_names:
            proba = fit_predict(name, task, train[columns].to_numpy(), y_train, test[columns].to_numpy(),
                                n_jobs=1, gpu=False)
            outputs.append(collect(test, fold, test_start, name, proba, y_train, y_test, prior))
    return pd.concat(outputs, ignore_index=True) if outputs else pd.DataFrame()


def run_per_symbol(panel, label_column, columns, model_names, task, gap=GAP) -> pd.DataFrame:
    folds = list(date_folds(panel, gap))
    worker = partial(run_one_symbol, folds=folds, label_column=label_column, columns=columns,
                     model_names=model_names, task=task)
    symbols = sorted(panel["symbol"].unique())
    with ProcessPoolExecutor(max_workers=len(symbols)) as pool:
        results = list(pool.map(worker, symbols, [panel[panel["symbol"] == s] for s in symbols]))
    return pd.concat([r for r in results if len(r)], ignore_index=True)


def add_ensembles(oof: pd.DataFrame) -> pd.DataFrame:
    present = set(oof["model"].unique())
    extra = []
    probability_columns = ["p_down", "p_flat", "p_up"]
    keys = ["fold", "time", "symbol"]
    for name, members in ENSEMBLES.items():
        members = [m for m in members if m in present]
        if len(members) < 2 or (name == "ensemble4" and members == list(ENSEMBLES["ensemble3"])):
            continue
        subset = oof[oof["model"].isin(members)]
        averaged = subset.groupby(keys, sort=False)[probability_columns].mean().reset_index()
        meta = subset.drop_duplicates(keys).drop(columns=probability_columns + ["model"])
        merged = meta.merge(averaged, on=keys)
        merged["model"] = name
        extra.append(merged[oof.columns])
    return pd.concat([oof, *extra], ignore_index=True)


def daily_rank_ic(frame: pd.DataFrame, target: str) -> pd.Series:
    ranked = frame.assign(
        rank_score=frame.groupby("time")["score"].rank(), rank_target=frame.groupby("time")[target].rank()
    )
    grouped = ranked.groupby("time")
    covariance = grouped.apply(lambda g: np.corrcoef(g["rank_score"], g["rank_target"])[0, 1], include_groups=False)
    return covariance.dropna()


def tercile_spread_bps(frame: pd.DataFrame) -> float:
    pct = frame.groupby("time")["score"].rank(pct=True)
    top = frame[pct > 2 / 3].groupby("time")["r_next"].mean()
    bottom = frame[pct <= 1 / 3].groupby("time")["r_next"].mean()
    return float((top - bottom).dropna().mean() * 1e4)


def sticky_selection(rank: pd.DataFrame, holdings: pd.Series, buffer: float) -> pd.DataFrame:
    selected = pd.DataFrame(False, index=rank.index, columns=rank.columns)
    held: list[str] = []
    for date, row in rank.iterrows():
        target = int(holdings[date])
        keep = sorted((s for s in held if row[s] <= buffer * target), key=lambda s: row[s])[:target]
        entrants = [s for s in row.dropna().sort_values().index if s not in keep][: target - len(keep)]
        held = keep + entrants
        selected.loc[date, held] = True
    return selected


def top_k_portfolio(frame: pd.DataFrame, buffer: float = 1.0) -> pd.DataFrame:
    scores = frame.pivot(index="time", columns="symbol", values="score")
    returns = np.expm1(frame.pivot(index="time", columns="symbol", values="r_next"))
    holdings = np.maximum(MIN_HOLDINGS, (scores.notna().sum(axis=1) * TOP_FRACTION).round().astype(int))
    rank = scores.rank(axis=1, ascending=False, method="first")
    if buffer > 1.0:
        selected = sticky_selection(rank, holdings, buffer) & scores.notna()
    else:
        selected = rank.le(holdings, axis=0) & scores.notna()
    weights = selected.div(selected.sum(axis=1), axis=0).fillna(0.0)
    change = weights.diff().fillna(weights)
    buy_turnover, sell_turnover = change.clip(lower=0).sum(axis=1), (-change).clip(lower=0).sum(axis=1)
    cost = BUY_FEE * buy_turnover + SELL_FEE * sell_turnover
    gross = (weights * returns.fillna(0.0)).sum(axis=1)
    return pd.DataFrame(
        {"gross": gross, "net": gross - cost, "benchmark": returns.mean(axis=1),
         "buy_turnover": buy_turnover, "sell_turnover": sell_turnover}
    )


def alpha_beta(strategy: np.ndarray, benchmark: np.ndarray, periods_per_year: float) -> tuple[float, float]:
    beta, alpha = np.polyfit(benchmark, strategy, 1)
    return alpha * periods_per_year, beta


def bootstrap_alpha_ci(strategy: np.ndarray, benchmark: np.ndarray, periods_per_year: float) -> tuple[float, float]:
    n = len(strategy)
    rng = np.random.default_rng(RANDOM_STATE)
    blocks = int(np.ceil(n / BOOTSTRAP_BLOCK))
    starts = rng.integers(0, n - BOOTSTRAP_BLOCK + 1, (BOOTSTRAP_RUNS, blocks))
    index = (starts[:, :, None] + np.arange(BOOTSTRAP_BLOCK)).reshape(BOOTSTRAP_RUNS, -1)[:, :n]
    x, y = benchmark[index], strategy[index]
    beta = ((x - x.mean(axis=1, keepdims=True)) * (y - y.mean(axis=1, keepdims=True))).sum(axis=1) / (
        (x - x.mean(axis=1, keepdims=True)) ** 2
    ).sum(axis=1)
    alpha = (y.mean(axis=1) - beta * x.mean(axis=1)) * periods_per_year
    low, high = np.percentile(alpha, [2.5, 97.5])
    return float(low), float(high)


def fold_scores(frame: pd.DataFrame, rng: np.random.Generator) -> tuple[float, float, float]:
    f1s, aucs, baselines = [], [], []
    for _, fold_frame in frame.groupby("fold"):
        y = fold_frame["y"].to_numpy()
        proba = fold_frame[["p_down", "p_flat", "p_up"]].to_numpy()
        f1s.append(f1_score(y, proba.argmax(axis=1), average="macro", labels=CLASSES, zero_division=0))
        aucs.append(roc_auc_score(y, proba / proba.sum(axis=1, keepdims=True), multi_class="ovr",
                                  average="macro", labels=CLASSES))
        prior = fold_frame[["prior_down", "prior_flat", "prior_up"]].iloc[0].to_numpy()
        draws = rng.choice(CLASSES, size=(BASELINE_DRAWS, len(y)), p=prior)
        baselines.append(np.mean([f1_score(y, d, average="macro", labels=CLASSES, zero_division=0) for d in draws]))
    return float(np.mean(f1s)), float(np.mean(aucs)), float(np.mean(baselines))


def fold_spread(frame: pd.DataFrame) -> dict:
    accuracies, majority_accuracies, majority_f1s, f1s, aucs = [], [], [], [], []
    for _, fold_frame in frame.groupby("fold"):
        y = fold_frame["y"].to_numpy()
        proba = fold_frame[["p_down", "p_flat", "p_up"]].to_numpy()
        majority = fold_frame[["prior_down", "prior_flat", "prior_up"]].iloc[0].to_numpy().argmax()
        accuracies.append((proba.argmax(axis=1) == y).mean())
        majority_accuracies.append((y == majority).mean())
        majority_f1s.append(f1_score(y, np.full(len(y), majority), average="macro", labels=CLASSES, zero_division=0))
        f1s.append(f1_score(y, proba.argmax(axis=1), average="macro", labels=CLASSES, zero_division=0))
        aucs.append(roc_auc_score(y, proba / proba.sum(axis=1, keepdims=True), multi_class="ovr",
                                  average="macro", labels=CLASSES))
    return {
        "accuracy": np.mean(accuracies), "accuracy_std": np.std(accuracies, ddof=1),
        "accuracy_majority": np.mean(majority_accuracies), "f1_std": np.std(f1s, ddof=1),
        "f1_majority": np.mean(majority_f1s), "auc_std": np.std(aucs, ddof=1),
    }


def evaluate(oof: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
    periods_per_year = TRADING_DAYS / horizon
    oof = oof.assign(period=np.where(oof["test_start"] >= CONFIRM_START, "confirm", "dev"))
    oof["score"] = oof["p_up"] - oof["p_down"]
    rows = []
    for model, model_frame in oof.groupby("model"):
        for period, frame in (*model_frame.groupby("period"), ("all", model_frame)):
            rng = np.random.default_rng(RANDOM_STATE)
            f1, auc, baseline = fold_scores(frame, rng)
            directional = frame["y"] != FLAT
            sampled = frame[frame["time"].isin(np.sort(frame["time"].unique())[::horizon])]
            ic_abs = daily_rank_ic(sampled, "r_next")
            ic_rel = daily_rank_ic(sampled, "r_rel")
            book = top_k_portfolio(sampled)
            alpha_gross, _ = alpha_beta(book["gross"].to_numpy(), book["benchmark"].to_numpy(), periods_per_year)
            alpha, beta = alpha_beta(book["net"].to_numpy(), book["benchmark"].to_numpy(), periods_per_year)
            low, high = bootstrap_alpha_ci(book["net"].to_numpy(), book["benchmark"].to_numpy(), periods_per_year)
            sticky = top_k_portfolio(sampled, STICKY_BUFFER)
            sticky_alpha, _ = alpha_beta(sticky["net"].to_numpy(), sticky["benchmark"].to_numpy(), periods_per_year)
            sticky_gross, _ = alpha_beta(sticky["gross"].to_numpy(), sticky["benchmark"].to_numpy(), periods_per_year)
            sticky_low, sticky_high = bootstrap_alpha_ci(
                sticky["net"].to_numpy(), sticky["benchmark"].to_numpy(), periods_per_year
            )
            rows.append(
                {
                    "model": model, "period": period, "folds": frame["fold"].nunique(), "rows": len(frame),
                    "f1": f1, "f1_random": baseline, "auc": auc, **fold_spread(frame),
                    "auc_up_vs_down": roc_auc_score(frame["y"][directional] == UP, frame["score"][directional]),
                    "auc_flat": roc_auc_score(frame["y"] == FLAT, frame["p_flat"]),
                    "ic_next": ic_abs.mean(), "ic_next_t": ic_abs.mean() / ic_abs.std() * np.sqrt(len(ic_abs)),
                    "ic_rel": ic_rel.mean(), "ic_rel_t": ic_rel.mean() / ic_rel.std() * np.sqrt(len(ic_rel)),
                    "tercile_spread_bps": tercile_spread_bps(sampled),
                    "alpha_gross_ann": alpha_gross, "alpha_net_ann": alpha, "alpha_ci_low": low,
                    "alpha_ci_high": high, "beta": beta,
                    "net_return_ann": book["net"].mean() * periods_per_year,
                    "benchmark_return_ann": book["benchmark"].mean() * periods_per_year,
                    "sharpe_net": book["net"].mean() / book["net"].std() * np.sqrt(periods_per_year),
                    "buy_turnover_per_day": book["buy_turnover"].mean(),
                    "sticky_alpha_gross_ann": sticky_gross, "sticky_alpha_net_ann": sticky_alpha,
                    "sticky_alpha_ci_low": sticky_low, "sticky_alpha_ci_high": sticky_high,
                    "sticky_buy_turnover": sticky["buy_turnover"].mean(),
                }
            )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--mode", choices=["pooled", "per_symbol"], default="pooled")
    parser.add_argument("--task", choices=["direct", "twostage"], default="direct")
    parser.add_argument("--label", choices=["abs", "rel", "rel3", "rel5", "rel10", "rel20"], default="abs")
    parser.add_argument("--reevaluate", action="store_true")
    parser.add_argument("--features", choices=list(FEATURE_SETS), default="full")
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS), choices=list(MODEL_NAMES))
    parser.add_argument("--no-gpu", action="store_true")
    parser.add_argument("--panel", type=Path, default=ROOT / "data" / "extra" / "panel_1D.csv.gz")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results" / "research")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    panel = pd.read_csv(args.panel, parse_dates=["time"]).sort_values(["time", "symbol"]).reset_index(drop=True)
    label_column = f"label_{args.label}"
    horizon = int(args.label[3:]) if args.label.startswith("rel") and len(args.label) > 3 else 1
    if horizon > 1:
        panel = panel.dropna(subset=[label_column, f"r_fwd{horizon}"]).reset_index(drop=True)
        panel[label_column] = panel[label_column].astype(int)
        panel["r_next"] = panel[f"r_fwd{horizon}"]
        panel["r_rel"] = panel["r_next"] - panel.groupby("time")["r_next"].transform("mean")
    columns = list(FEATURE_SETS[args.features])
    started = time.perf_counter()
    if args.reevaluate:
        saved = pd.read_csv(args.output_root / args.name / "oof.csv.gz", parse_dates=["time", "test_start"])
        oof = saved[~saved["model"].isin(ENSEMBLES)]
    elif args.mode == "pooled":
        oof = run_pooled(panel, label_column, columns, args.models, args.task, gpu=not args.no_gpu, gap=horizon)
    else:
        oof = run_per_symbol(panel, label_column, columns, [m for m in args.models if m != "mlp"], args.task, gap=horizon)
    oof = add_ensembles(oof)
    metrics = evaluate(oof, horizon)
    output_dir = args.output_root / args.name
    output_dir.mkdir(parents=True, exist_ok=True)
    if not args.reevaluate:
        oof.to_csv(output_dir / "oof.csv.gz", index=False)
    metrics.assign(name=args.name, mode=args.mode, task=args.task, label=args.label, features=args.features,
                   horizon=horizon).to_csv(
        output_dir / "metrics.csv", index=False
    )
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", None)
    print(f"\n{args.name} finished in {time.perf_counter() - started:.0f}s")
    print(metrics[metrics["period"] != "all"].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
