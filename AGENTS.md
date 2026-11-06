# AGENTS.md

Hướng dẫn cho AI agent và thành viên làm việc trong repo này.

## Tổng quan

Bài tiểu luận học phần Học máy (nhóm 16): dự đoán xu hướng tăng/giảm giá cổ phiếu từ nến ngày. Phân loại 3 lớp (`-1` giảm, `0` ngang, `1` tăng), kiểm định walk-forward, so sánh với mua và nắm giữ, dự đoán ngẫu nhiên.

Mô hình chính (nhóm đã chốt): **một mô hình chung huấn luyện trên dữ liệu gộp 19 mã** (4 mã của đề bài TCB, CTG, VNM, ACB và 15 mã bổ sung), khung ngày, kết hợp ba mô hình Logistic, Random Forest, XGBoost bằng cách lấy trung bình xác suất (`ensemble3`). Hai khái niệm này độc lập, không dùng lẫn:
- **Gộp mã (pooled):** cách chia dữ liệu huấn luyện, một mô hình cho nhiều mã, thay cho "mỗi mã một mô hình" (per-symbol).
- **`ensemble3`:** cách kết hợp mô hình, không liên quan đến số mã.

Chạy từng mã riêng (`scripts/train_models.py`) vẫn giữ làm baseline để so sánh. Báo cáo kết quả riêng cho 4 mã của đề bài như một tập con của mô hình gộp. Số liệu và lý do chọn nằm ở [docs/train.md](docs/train.md), mục 14 và 15.

Đọc trước khi làm việc: [docs/idea.md](docs/idea.md) (đề bài), [docs/data-preprocess.md](docs/data-preprocess.md) (thiết kế tiền xử lý, nhãn, đặc trưng, walk-forward, checklist chống rò rỉ), `docs/project-report/Tiêu trí chấm các bài kiểm tra và bài thi/Tiêu chí chấm.txt` (tiêu chí chấm).

## Cấu trúc repo

```
scripts/                  crawl.py (thu thập), clean_data.py, preprocess_data.py, filter_data.py, train_models.py, analyze_results.py, tune_models.py, select_final_model.py, screen_symbols.py, hourly_ablation.py, panel_data.py, panel_experiments.py, summarize_research.py, final_backtest.py, train_final_model.py, predict_daily.py
scripts/crawl.py         thu thập nến từ API DNSE (Entrade), ghi vào data/raw/<khung>/<mã>.csv
data/raw/<khung>/        dữ liệu thô, các cột time, open, high, low, close, volume
data/processed/1D/       dữ liệu đã tiền xử lý (đặc trưng, r_next, label)
results/<khung>/         kết quả walk-forward: fold_metrics, predictions, backtest, summary (train_models.py)
data/extra/            dữ liệu thí nghiệm mở rộng: 15 mã bổ sung (cleaned, processed) và panel_1D.csv.gz (sinh lại bằng panel_data.py)
data/screening/        chấm điểm chất lượng dữ liệu các mã ứng viên (screen_symbols.py)
results/extra/         kết quả thí nghiệm mở rộng (15 mã, khung 1D và 1H)
models/                  gói mô hình đã huấn luyện để triển khai (train_final_model.py): file mô hình và metadata.json
results/live/          nhật ký dự đoán hằng ngày và tín hiệu mới nhất (predict_daily.py); dữ liệu nến tải về nằm ở data/live/ (không commit)
results/research/      kết quả mô hình gộp nhiều mã: metrics.csv từng cấu hình, summary.csv (panel_experiments.py)
Makefile                 lệnh tắt: `make help` (setup, web, test, daily; target huấn luyện cần ALLOW_TRAIN=1, chạy trên máy GPU)
webapp/                  web Streamlit hai trang (backtest, paper trading): `.venv/bin/streamlit run webapp/app.py`; `market.py` dữ liệu và alpha, `engine.py` mô phỏng danh mục, `paper.py` tài khoản giả lập (trạng thái ở results/live/paper/account.json), `test_engine.py` kiểm tra
notebooks/               EDA và thực nghiệm
docs/                    tài liệu thiết kế
docs/project-report/
  bao-cao/               báo cáo LaTeX đang viết (bao_cao.tex, images/)
  latext_page/           mẫu báo cáo gốc của bộ môn, không sửa
requirements.txt         thư viện Python
.venv/                   môi trường ảo, không commit
```

Đường dẫn trong code luôn tương đối so với thư mục gốc repo (dùng `pathlib`), không dùng đường dẫn tuyệt đối của máy cá nhân.

## Môi trường

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Thêm thư viện mới thì cập nhật `requirements.txt`. Cố định `random_state = 42` ở mọi chỗ có ngẫu nhiên.

## Quy ước viết code

- Tên biến, hàm, lớp, file, thông báo log và lỗi viết bằng tiếng Anh. Hạn chế tiếng Việt trong code.
- Hạn chế comment. Chỉ viết khi thật sự cần, và chỉ giải thích lý do (vì sao), không mô tả code làm gì. Đặt tên rõ ràng thay cho comment.
- Ngoại lệ: nhãn trục, tiêu đề biểu đồ có thể bằng tiếng Việt nếu hình được chèn vào báo cáo.
- Không tự viết lại thứ đã có sẵn. Dùng hàm, lớp hoặc thành phần của thư viện đang dùng, ví dụ:
  - `pandas`: `rolling`, `ewm`, `shift`, `pct_change`, `groupby`.
  - `scikit-learn`: `Pipeline`, `StandardScaler`, `TimeSeriesSplit` (có `gap`, `test_size`), `metrics` (`f1_score`, `roc_auc_score`, `confusion_matrix`).
  - `xgboost`, `matplotlib`, `seaborn` cho mô hình và biểu đồ.
  Trước khi viết hàm mới, kiểm tra thư viện đã có chưa. Chỉ tự viết khi thư viện không có, và nêu lý do.
- Mã chạy được từ đầu đến cuối trên bản sao sạch của repo, không phụ thuộc file ngoài repo.

## Chống rò rỉ dữ liệu

Bắt buộc, xem checklist ở cuối [docs/data-preprocess.md](docs/data-preprocess.md). Tóm tắt:

- Đặc trưng tại phiên `t` chỉ dùng dữ liệu đến hết phiên `t`.
- `label` và `r_next` không bao giờ nằm trong `X`.
- Chia dữ liệu theo thời gian, không xáo trộn, không `train_test_split` ngẫu nhiên.
- Scaler, chọn đặc trưng, chọn siêu tham số chỉ khớp trên tập huấn luyện của từng fold, gói trong `Pipeline`.
- Bỏ 1 phiên giữa tập huấn luyện và tập kiểm tra.

## Tài liệu và báo cáo

- Tài liệu, README, báo cáo, markdown trong notebook viết bằng tiếng Việt.
- Số liệu trong báo cáo phải lấy từ mã chạy được của repo. Không bịa số liệu, không chỉ báo lần chạy tốt nhất.
- Chỉ trích dẫn tài liệu đã kiểm chứng thông tin (tác giả, năm, nơi đăng, trang).
- Báo cáo biên dịch bằng XeLaTeX, không dùng pdfLaTeX:

  ```bash
  cd docs/project-report/bao-cao && latexmk bao_cao.tex
  ```

- Không sửa mẫu gốc trong `latext_page/`. Không để comment trong file `.tex`.
- Phần sử dụng AI tạo sinh phải được khai báo trong Lời cam đoan của báo cáo.

## Git

- Không tự commit hay push, trừ khi được yêu cầu.
- Mỗi thành viên commit bằng tài khoản của chính mình, commit nhỏ, thông điệp rõ nghĩa. Lịch sử commit là minh chứng đóng góp khi chấm điểm.

## Phân công

- Hiếu: xử lý dữ liệu, báo cáo, slide.
- Toàn: crawl dữ liệu, huấn luyện mô hình, triển khai cloud.
