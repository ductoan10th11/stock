PY := $(CURDIR)/.venv/bin/python
PYTHON_VERSION ?= 3.14
API_PORT ?= 8000
OOF_NAME := pooled_abs_full

.DEFAULT_GOAL := help
.PHONY: help setup api web build-web test daily panel oof train-final check-train up down logs nginx-enable nginx-enable-notebook notebook-password notebook-up notebook-down

help:
	@echo "make setup        tao .venv (Python $(PYTHON_VERSION), uv) va cai requirements.txt"
	@echo "make api          chay API FastAPI o che do dev, http://localhost:$(API_PORT)"
	@echo "make web          chay web React (Vite) o che do dev, goi API qua proxy /api"
	@echo "make build-web    build web React vao apps/web/dist"
	@echo "make test         kiem tra API (pytest) va web (vitest)"
	@echo "make daily        tai nen, cham diem 19 ma bang mo hinh da luu (chi suy luan, khong train)"
	@echo "make up           build web (dist) va chay container api (compose.yaml), cong 127.0.0.1:$(API_PORT); nginx phuc vu dist"
	@echo "make down         dung container api"
	@echo "make logs         xem log container api"
	@echo "make nginx-enable tro nginx/backtest.naot.me.conf vao /etc/nginx/sites-enabled, kiem tra va reload nginx (sudo)"
	@echo "make notebook-password  dat mat khau Jupyter (nhap tay, luu hash vao secrets/, khong commit)"
	@echo "make notebook-up    build va chay container Jupyter, cong 127.0.0.1:8888 (can notebook-password truoc)"
	@echo "make notebook-down  dung container Jupyter (make down de go han)"
	@echo "make nginx-enable-notebook  nhu nginx-enable, cho nginx/notebook.naot.me.conf (sudo)"
	@echo "make panel        dung lai data/extra/panel_1D.csv.gz (khong train)"
	@echo "make oof          sinh results/research/$(OOF_NAME)/oof.csv.gz   [TRAIN: can ALLOW_TRAIN=1, chay tren may GPU]"
	@echo "make train-final  huan luyen lai models/ensemble3_pooled_1D      [TRAIN: can ALLOW_TRAIN=1, chay tren may GPU]"

setup:
	uv venv --python $(PYTHON_VERSION) --clear .venv
	uv pip install --python $(PY) -r requirements.txt
	cd apps/web && npm ci

api:
	cd apps/api && $(PY) -m uvicorn app.main:app --reload --port $(API_PORT)

web:
	cd apps/web && npm run dev

build-web:
	cd apps/web && npm run build

test:
	cd apps/api && $(PY) -m pytest -q
	cd apps/web && npm test

daily:
	$(PY) scripts/predict_daily.py --crawl --crawl-days 700 --days 5

up: build-web
	docker compose up -d --build --remove-orphans

down:
	docker compose --profile notebook down

logs:
	docker compose logs -f --tail 100 api

notebook-password:
	@mkdir -p secrets
	$(PY) -c "from pathlib import Path; from jupyter_server.auth import passwd; p = Path('secrets/jupyter_password_hash'); p.write_text(passwd()); p.chmod(0o600); print('saved', p)"

notebook-up:
	@test -s secrets/jupyter_password_hash || { echo "Thieu secrets/jupyter_password_hash. Chay: make notebook-password" >&2; exit 1; }
	docker compose --profile notebook up -d --build notebook

notebook-down:
	docker compose --profile notebook stop notebook

nginx-enable:
	sudo ln -sfn $(CURDIR)/nginx/backtest.naot.me.conf /etc/nginx/sites-enabled/backtest.naot.me.conf
	sudo nginx -t && sudo systemctl reload nginx

nginx-enable-notebook:
	sudo ln -sfn $(CURDIR)/nginx/notebook.naot.me.conf /etc/nginx/sites-enabled/notebook.naot.me.conf
	sudo nginx -t && sudo systemctl reload nginx

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
