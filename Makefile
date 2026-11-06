PY := .venv/bin/python
PYTHON_VERSION ?= 3.14
PORT ?= 8501
OOF_NAME := pooled_abs_full

.DEFAULT_GOAL := help
.PHONY: help setup web test daily panel oof train-final check-train

help:
	@echo "make setup        tao .venv (Python $(PYTHON_VERSION), uv) va cai requirements.txt"
	@echo "make web          chay web backtest + paper trading (PORT=$(PORT))"
	@echo "make test         kiem tra engine backtest"
	@echo "make daily        tai nen, cham diem 19 ma bang mo hinh da luu (chi suy luan, khong train)"
	@echo "make panel        dung lai data/extra/panel_1D.csv.gz (khong train)"
	@echo "make oof          sinh results/research/$(OOF_NAME)/oof.csv.gz   [TRAIN: can ALLOW_TRAIN=1, chay tren may GPU]"
	@echo "make train-final  huan luyen lai models/ensemble3_pooled_1D      [TRAIN: can ALLOW_TRAIN=1, chay tren may GPU]"

setup:
	uv venv --python $(PYTHON_VERSION) --clear .venv
	uv pip install --python $(PY) -r requirements.txt

web:
	@echo "Mo http://localhost:$(PORT)"
	$(PY) -m streamlit run webapp/app.py --server.port $(PORT) --server.headless true --browser.gatherUsageStats false

test:
	$(PY) webapp/test_engine.py

daily:
	$(PY) scripts/predict_daily.py --crawl --crawl-days 700 --days 5

panel:
	$(PY) scripts/panel_data.py

check-train:
ifneq ($(ALLOW_TRAIN),1)
	@echo "Tu choi: target nay huan luyen mo hinh (nong CPU). Chay tren may GPU roi dat ALLOW_TRAIN=1." >&2
	@exit 1
endif

oof: check-train
	$(PY) scripts/panel_experiments.py --name $(OOF_NAME) --mode pooled --label abs --features full

train-final: check-train
	$(PY) scripts/train_final_model.py
