# Quy trình thực hiện

Tài liệu này sắp xếp các bước làm theo đúng bốn nhiệm vụ của đề bài ([idea.md](idea.md)), ghi trạng thái từng bước, script chạy và mục báo cáo tương ứng. Kết quả chi tiết của phần huấn luyện nằm ở [train.md](train.md). Thiết kế tiền xử lý nằm ở [data-preprocess.md](data-preprocess.md).

Trạng thái: **xong**, **một phần**, **chưa làm**. Cập nhật cột này mỗi khi hoàn thành một bước.

## Đối chiếu với đề bài

| Nhiệm vụ của đề | Bước tương ứng | Trạng thái |
|---|---|---|
| 1. Nghiên cứu chuỗi giá, chỉ báo kỹ thuật, phát biểu bài toán phân loại | B1 | Xong (Chương 1, 2 của báo cáo) |
| 2. Thu thập dữ liệu, tính chỉ báo làm đặc trưng | B2 đến B5 | Xong |
| 3. Huấn luyện Logistic Regression, Random Forest, XGBoost bằng walk-forward; so sánh với mua và nắm giữ, dự đoán ngẫu nhiên | B6, B8, B9 | Mô hình ban đầu, tinh chỉnh và chọn mô hình cuối xong |
| 4. Đánh giá bằng Accuracy, F1, ROC-AUC và backtest; thảo luận giới hạn dự đoán giá và quá khớp | B6, B7, B10, B11 | Chỉ số, backtest cuối, phân tích quá khớp và thảo luận giới hạn xong (tài liệu); chưa đưa vào báo cáo LaTeX |

## Notebook

Notebook để chạy thử và thực hành tại chỗ khi vấn đáp. Chạy từ thư mục gốc repo: `.venv/bin/jupyter notebook notebooks/`. Mỗi notebook có phần nhận xét ngắn dưới từng kết quả. Notebook chạy bản rút gọn (một mã, ít fold); số liệu chính thức ở [train.md](train.md).

| Notebook | Nội dung | Bước | Bài kiểm tra |
|---|---|---|---|
| [eda.ipynb](../notebooks/eda.ipynb) | Chất lượng dữ liệu, phân bố lợi suất và nhãn, tự tương quan, đặc trưng và nhãn | B4 | 1 |
| [models.ipynb](../notebooks/models.ipynb) | Ba thuật toán (ý tưởng, hàm mục tiêu, siêu tham số), baseline, walk-forward, ma trận nhầm lẫn, quá khớp | B6, B7 | 2 |
| [tuning.ipynb](../notebooks/tuning.ipynb) | Ablation đặc trưng, grid search, đường cong kiểm định, Voting, bảng so sánh | B8 | 3 |

## Điểm khác so với đề bài

- Đề gợi ý crawl 6 tháng. Nhóm dùng toàn bộ lịch sử khoảng 8 đến 10 năm (2016 hoặc 2018 đến 10/2026), vì 6 tháng chỉ có khoảng 126 mẫu, không đủ để chạy walk-forward. Lý do này cần nêu trong báo cáo.
- Đề yêu cầu ba thuật toán. Nhóm làm đủ ba, SVM là gợi ý tùy chọn và chưa làm.
- Đề chỉ yêu cầu nến ngày. Các khung 1, 5, 15, 30 phút và 1H đã được tiền xử lý như thí nghiệm mở rộng, chưa huấn luyện.

## Các bước

### B1. Cơ sở lý thuyết và phát biểu bài toán (nhiệm vụ 1)

Đặc điểm chuỗi giá, SMA, EMA, RSI, MACD, Bollinger Bands, phát biểu bài toán phân loại ba lớp.
- Đầu ra: Chương 1 và 2 của [bao_cao.tex](project-report/bao-cao/bao_cao.tex).
- Trạng thái: xong.

### B2. Thu thập dữ liệu (nhiệm vụ 2)

- Chạy: `python scripts/crawl.py`
- Đầu ra: `data/raw/<khung>/<mã>.csv`.
- Báo cáo: mục 3.1.
- Trạng thái: xong. Dữ liệu 1D lấy ngày 2026-10-23.

### B3. Làm sạch

- Chạy: `python scripts/clean_data.py`
- Đầu ra: `data/cleaned/<khung>/<mã>.csv` và `cleaning_summary.csv`.
- Báo cáo: mục 3.3.
- Trạng thái: xong. Khung 30 phút được dựng lại từ khung 5 phút vì dữ liệu thô hỏng khối lượng buổi sáng (xem [train.md](train.md), mục 7).

### B4. Khảo sát dữ liệu (EDA)

- Chạy: [notebooks/eda.ipynb](../notebooks/eda.ipynb) (có phần đặc trưng và nhãn dùng `data/processed/`, chạy sau B5)
- Báo cáo: mục 3.2.
- Trạng thái: xong.

### B5. Tạo đặc trưng và nhãn (nhiệm vụ 2)

- Chạy: `python scripts/preprocess_data.py`
- Đầu ra: `data/processed/<khung>/<mã>.csv` gồm 25 đặc trưng (khung 1D), `r_next`, `label`.
- Báo cáo: mục 3.4.
- Trạng thái: xong.

### B6. Huấn luyện mô hình ban đầu và baseline (nhiệm vụ 3, 4)

- Chạy: `python scripts/train_models.py`; minh họa từng bước ở [notebooks/models.ipynb](../notebooks/models.ipynb)
- Nội dung: walk-forward, ba mô hình với siêu tham số cố định, ba baseline (lớp đa số, ngẫu nhiên, mua và nắm giữ), tính Accuracy, F1 macro, ROC-AUC, backtest.
- Đầu ra: `results/1D/{fold_metrics,predictions,backtest,summary}.csv`.
- Báo cáo: mục 3.6.
- Trạng thái: xong. Chi tiết ở [train.md](train.md).

### B7. Phân tích kết quả và quá khớp (nhiệm vụ 4)

- Chạy: `python scripts/analyze_results.py` (sau `train_models.py`).
- Nội dung: chỉ số train so với test, ma trận nhầm lẫn gộp bốn mã, tỷ lệ nhãn dự đoán, feature importance của Random Forest và XGBoost, đường cong học tập (theo số phiên train), F1 theo năm.
- Đầu ra: năm hình `overfitting.png`, `confusion_matrix.png`, `feature_importance.png`, `learning_curve.png`, `f1_by_year.png` trong `docs/project-report/bao-cao/images/`; số liệu và nhận xét ở [train.md](train.md), mục 9.
- Báo cáo: mục 3.7 và hình `fig:learningcurve`.
- Trạng thái: xong. Phát hiện chính: Random Forest và XGBoost đạt 1,000 trên tập train, chỉ 0,34 đến 0,35 trên tập test (quá khớp nghiêm trọng); Logistic thiếu khả năng biểu diễn.

### B8. Cải tiến mô hình

Mỗi thay đổi đo trên cùng dữ liệu, cùng walk-forward, cùng chỉ số, để lập bảng ablation:
1. Đặc trưng: so sánh "chỉ nhóm lõi" (12 đặc trưng theo đề) với "lõi + bổ trợ" (25 đặc trưng). Có thể thêm lọc đặc trưng tương quan trên 0,95 trong từng fold.
2. Xử lý mất cân bằng: nhãn đã gần cân bằng nên chỉ thử `class_weight` và ghi kết quả dù không cải thiện.
3. Tinh chỉnh siêu tham số: trong mỗi fold, lấy 20% cuối của train làm validation, chọn siêu tham số trên phần này rồi huấn luyện lại trên toàn bộ train của fold. Không dùng khối test để chọn bất cứ thứ gì.
4. Tùy chọn: SVM, hoặc Voting/Stacking.

- Chạy: `python scripts/tune_models.py` (năm biến thể: 12 hoặc 25 đặc trưng, `class_weight`, tinh chỉnh trong từng fold); bản rút gọn để thực hành ở [notebooks/tuning.ipynb](../notebooks/tuning.ipynb).
- Đầu ra: `results/1D/tuning/{fold_metrics,predictions,backtest,best_params,summary}.csv`; số liệu và nhận xét ở [train.md](train.md), mục 10.
- Báo cáo: mục 3.8 và 3.9 (bảng `tab:sieuthamso`, `tab:ablation`, hình `fig:sosanhmohinh`).
- Trạng thái: một phần. Ablation, `class_weight` và tinh chỉnh xong; kết quả: nhóm bổ trợ có ích, `class_weight` chỉ cải thiện nhỏ, tinh chỉnh không tăng F1 test. SVM, Voting/Stacking và lọc đặc trưng tương quan chưa làm.

### B9. Chọn mô hình cuối và đánh giá tổng quát hóa

Chọn dựa trên đánh đổi giữa F1, độ ổn định giữa các fold, thời gian chạy và khả năng diễn giải. Khối test của walk-forward là tập kiểm tra giữ lại; chỉ báo cáo một lần sau khi đã chốt cấu hình. Báo cáo cả kết quả không tốt, không chỉ báo lần chạy tốt nhất.
- Chạy: `python scripts/select_final_model.py` (đọc `results/1D/tuning/` và `results/1D/`, ghi `results/1D/final/`).
- Báo cáo: mục 3.10. Số liệu và nhận xét ở [train.md](train.md), mục 11.
- Trạng thái: xong. Chốt Random Forest, 25 đặc trưng, siêu tham số mặc định. Random Forest và XGBoost hòa về F1 (chênh +0,002, khoảng tin cậy chứa 0), chọn theo ROC-AUC và độ ổn định. F1 macro hơn ngẫu nhiên 0,022 [0,011; 0,033], không đồng đều giữa các mã và yếu dần sau 2020. Sau B14 mô hình chính đổi sang `ensemble3` gộp mã (train.md mục 15).

### B10. Backtest và so sánh với baseline (nhiệm vụ 3, 4)

Chạy lại backtest cho cấu hình cuối (gộp 19 mã + `ensemble3`), so với chuẩn thị trường, mua và nắm giữ từng mã và chọn mã ngẫu nhiên, kèm nhạy cảm với phí, sụt giảm tối đa và cách giữ vị thế để giảm vòng quay.
- Chạy: `python scripts/panel_data.py`, `python scripts/panel_experiments.py --name pooled_abs_full --mode pooled --label abs --features full`, `python scripts/final_backtest.py`.
- Đầu ra: `results/research/final_backtest/`; số liệu và nhận xét ở [train.md](train.md), mục 16.
- Báo cáo: mục 3.6 và 3.10.
- Trạng thái: xong. Tín hiệu xếp hạng thật (không danh mục ngẫu nhiên nào đạt alpha của mô hình trước phí), nhưng với phí thực tế alpha ròng chưa khác 0 có ý nghĩa (`sticky` 0,0% ở dev, +9,1% ở xác nhận, khoảng tin cậy chứa 0). Chưa mô hình hóa T+2. Chưa thử cách chỉ giao dịch khi xác suất vượt ngưỡng; `sticky` là cách giảm vòng quay đã thử.

### B11. Thảo luận giới hạn (nhiệm vụ 4)

Giới hạn của việc dự đoán giá cổ phiếu (thị trường gần hiệu quả, nhiễu lớn, thay đổi chế độ), nguy cơ quá khớp, chi phí giao dịch, thiên lệch sống sót và giai đoạn tăng giá của mẫu. Nên viết sau khi có kết quả B7 đến B10.
- Đầu ra: [train.md](train.md), mục 17 (tín hiệu yếu, quá khớp và chọn cấu hình nhiều lần, thay đổi chế độ, chi phí và khớp lệnh, thiên lệch mẫu, điều nên và không nên nói, hướng phát triển).
- Báo cáo: mục 3.11, phần Kết luận và hướng phát triển.
- Trạng thái: xong phần tài liệu, chưa đưa vào báo cáo LaTeX.

### B12. Thí nghiệm mở rộng khung nến (tùy chọn)

Chạy `python scripts/train_models.py --resolution 1H` hoặc khung phút. Khung phút chỉ có 63 phiên nên chỉ đáng làm với 1H. Chỉ làm nếu còn thời gian, và không đưa vào kết luận chính.
- Chạy: `python scripts/train_models.py --resolution 1H`, `python scripts/hourly_ablation.py --processed-root data/processed --output-root results --symbols TCB CTG VNM ACB`.
- Đầu ra: `results/1H/`; số liệu và nhận xét ở [train.md](train.md), mục 18 (bốn mã gốc) và mục 13 (15 mã mới).
- Trạng thái: xong cho khung 1H, không làm khung phút (chỉ 63 phiên). F1 Logistic 0,40 và AUC 0,60 phần lớn nhờ giờ trong ngày (baseline `hour_prior` F1 0,376, AUC 0,596); backtest lỗ nặng hơn mua và nắm giữ ở cả bốn mã. Không đưa vào kết luận chính. Sharpe khung giờ đã sửa thang.

### B13. Hoàn thiện báo cáo

1. Điền số liệu từ `results/` vào Chương 3, xóa các `\huongdan` và `\dots` còn lại.
2. Viết Kết luận, Hướng phát triển, Chương 4 (hướng dẫn cài đặt, nhớ ghi `brew install libomp` cho macOS).
3. Khai báo việc dùng AI tạo sinh trong Lời cam đoan.
4. Biên dịch: `cd docs/project-report/bao-cao && latexmk bao_cao.tex`.
5. Slide và phần triển khai cloud (theo phân công).
- Trạng thái: chưa làm.

### B14. Hướng cải thiện mô hình: gộp nhiều mã, nhãn tương đối (thí nghiệm sau B9)

Thử các hướng gộp mã, nhãn tương đối so với thị trường, mô hình biến động hai giai đoạn, ensemble, VN-Index và chân trời 3 đến 20 ngày trên panel 19 mã, so sánh trên các fold đến hết 2024 và xác nhận trên các fold từ 2025.
- Chạy: `python scripts/panel_data.py --verify`, `python scripts/panel_experiments.py --name <tên> --mode pooled --label rel --features full`, `python scripts/summarize_research.py`.
- Đầu ra: `results/research/`; số liệu và nhận xét ở [train.md](train.md), mục 14.
- Trạng thái: xong phần thử nghiệm. Hướng tốt nhất: mô hình gộp nhiều mã, đặc trưng đầy đủ không kèm VN-Index (nhãn tuyệt đối và tương đối gần tương đương sau khi xác nhận). Tín hiệu xếp hạng được xác nhận ngoài mẫu, nhưng alpha ròng sau phí chưa khác 0 có ý nghĩa. Mô hình chính đã chốt (nhóm đồng ý): gộp 19 mã để huấn luyện một mô hình chung (pooled), kết hợp ba mô hình bằng `ensemble3`, khung ngày ([train.md](train.md), mục 15). Hai khái niệm độc lập: gộp mã là cách chia dữ liệu, `ensemble3` là cách kết hợp mô hình. `AGENTS.md` và `data-preprocess.md` đã sửa theo. Chưa đưa vào báo cáo LaTeX.

### B15. Mô hình triển khai (đã lưu)

Huấn luyện mô hình chính trên toàn bộ dữ liệu và lưu thành gói để chạy ở máy khác (không có GPU), dùng cho paper trading. Gói không dùng để backtest lại lịch sử.
- Chạy: `python scripts/train_final_model.py`.
- Đầu ra: `models/ensemble3_pooled_1D/` (3 file mô hình và `metadata.json`, 12 MB); chi tiết ở [train.md](train.md), mục 19.
- Dự đoán hằng ngày: `python scripts/predict_daily.py --crawl` (đầu ra `results/live/`, chi tiết ở [train.md](train.md), mục 20).
- Trạng thái: gói mô hình và script dự đoán xong, đã chạy thử với dữ liệu thật ngày 2026-11-06 và kiểm tra tính nhất quán đặc trưng (cần từ 250 nến mỗi mã). Chưa cố định phiên bản trong `requirements.txt`, chưa có script đối chiếu nhật ký với lợi suất thực tế.

### B16. Web backtest và paper trading

Backend FastAPI trong `apps/api/` và frontend React trong `apps/web/`. Chạy bằng `make` (xem `make help`): `make setup`, `make api` và `make web` (hai terminal), `make daily`, `make test`.
- Backtest dùng tín hiệu ngoài mẫu `results/research/pooled_abs_full/oof.csv.gz` (không dùng gói `models/` vì đã học cả giai đoạn này). File này sinh bằng `make oof ALLOW_TRAIN=1`, chỉ chạy trên máy GPU; các target huấn luyện từ chối chạy nếu thiếu `ALLOW_TRAIN=1`.
- Trang Backtest (`POST /api/backtest`): tín hiệu mô hình `ensemble3` và bảy alpha cổ điển (động lượng 12-1 tháng, động lượng 60 phiên, đảo chiều 5 phiên, biến động thấp, đảo chiều RSI, gần đỉnh 60 phiên, Alpha#6), tổ hợp z-score tùy chỉnh. Danh mục top-K, vùng đệm giữ vị thế, ngưỡng điểm. Kiểu "thực tế": khớp ở giá mở cửa phiên sau, khoá T+2 (số phiên giữ tối thiểu), trượt giá, mã kịch trần không mua được và kịch sàn không bán được (biên 7%, bước giá HOSE), trọng số mỗi mã chặn ở 10% giá trị giao dịch trung bình 20 phiên so với vốn. Kiểu "lý thuyết" giống `final_backtest.py`. So với trung bình đều 19 mã, VN-Index và chọn ngẫu nhiên. Khoảng tin cậy alpha có thêm bản Bonferroni cho 9 chiến thuật. Phần "chọn mã ngẫu nhiên" (30 danh mục mô phỏng, chậm nhất) tách thành `POST /api/backtest/random`, giao diện gọi sau khi kết quả chính đã có, nên bảng so sánh hiện dòng này sau vài giây. Kết quả được cache theo yêu cầu. Giao diện: thanh công cụ (khớp lệnh, giai đoạn, chiến thuật), thiết lập nâng cao trong ngăn trượt, bốn tab lấp đầy 100vh. Tab "Dự đoán mô hình": nến và dự đoán ngoài mẫu của walk-forward cho từng mã trong khoảng chọn (7 ngày, 1 tháng, 1 năm hoặc ngày tùy ý), kèm độ chính xác của 19 mã trong khoảng đó (`GET /api/backtest/predictions` và `/{mã}`); đây là đánh giá mô hình độc lập với quy tắc mua bán.
- Trang Paper trading (`/api/paper`): một tài khoản giả lập lưu trong SQLite `data/live/paper.db`; nút cập nhật tải nến (19 mã và VN-Index), chấm điểm bằng gói mô hình, xử lý các phiên mới. Cùng các ràng buộc như backtest thực tế, lô 100. Chỉ dùng tín hiệu của các phiên sau `trained_until`.
- Giao diện Paper Trading chia bốn tab (Tổng quan, Dự đoán, Lịch sử lệnh, Cài đặt). Tab Dự đoán (`GET /api/predictions`, `/api/predictions/<mã>`) vẽ nến 90 phiên của một mã, mũi tên dự đoán dưới mỗi nến (đặc: đoán đúng, rỗng: sai; dự đoán ngoài mẫu từ walk-forward và dự đoán thật sau ngày huấn luyện, giai đoạn giữa không có dự đoán), biểu đồ cột điểm mỗi ngày và ô dự đoán phiên tới. Tab Lịch sử lệnh hiện thêm giá vào, giá trị vào và lãi/lỗ (đ, %) cho mỗi lệnh bán, tính sau phí mua và phí bán.
- Tự động cập nhật: API tự chạy cập nhật dữ liệu và các phiên mới của tài khoản lúc 15:30 giờ Việt Nam các ngày thứ Hai đến thứ Sáu (`apps/api/app/services/scheduler.py`; thử lại 3 lần cách nhau 10 phút nếu lỗi; tắt bằng biến môi trường `AUTO_REFRESH=0`). Sau mỗi lần cập nhật, bot Telegram gửi báo cáo lãi/lỗ của paper trading (`reports.py`, `telegram.py`; mỗi phiên gửi một lần, bảng `daily_report`; cấu hình `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID` trong `apps/api/.env`, mẫu ở `.env.example`). Nút "Cập nhật dữ liệu" vẫn dùng được. Giới hạn container api: 1 GB RAM, 2 CPU (đỉnh đo được 470 MiB).
- Môi trường: Python 3.12 trở lên, phiên bản trong `requirements.txt` khớp `metadata.json` của gói mô hình. Chưa mô hình hóa lô 100 và hàng đợi khớp lệnh trong backtest.
- Quy tắc cho Mô hình AI (chỉ áp cho chiến thuật `model`, vì các tín hiệu khác là giá trị thô): mua khi điểm (xác suất tăng trừ giảm) từ một ngưỡng, bán khi điểm xuống dưới ngưỡng bán (`sell_score`), thay cho quy tắc cũ bán khi tụt hạng. Có thể chia vốn đều hoặc theo điểm, chỉ chia lúc mua vào (backtest và tài khoản paper giao dịch giống nhau).
- Chọn cấu hình: quét 324 tổ hợp (ngưỡng mua 0 đến 0,06; ngưỡng bán −0,2 đến 0 hoặc theo hạng; giữ tối thiểu 2, 5, 10 phiên; chia đều hay theo điểm; 10, 20, 30% số mã), kiểu thực tế, chọn theo Sharpe giai đoạn phát triển (đến hết 2024) rồi kiểm ở giai đoạn xác nhận (từ 2025). Mặc định: mua khi điểm ≥ +0,06, bán khi điểm ≤ −0,10, giữ ít nhất 2 phiên, chia đều, 3 mã.
- Kết quả cấu hình mặc định (kiểu thực tế, đã trừ phí và trượt giá): phát triển 40,7%/năm (Sharpe 1,24), xác nhận 19,5%/năm (Sharpe 0,64), toàn giai đoạn 35,2%/năm, sụt giảm tối đa −35%. Cân bằng đều 19 mã: 24,5%, 15,0%, 22,0%; VN-Index giai đoạn xác nhận 24,6%. Alpha so với cân bằng đều: +15,3% (khoảng tin cậy 95% [2,6%; 28,5%]) ở phát triển, +4,3% ([−20,5%; 29,2%]) ở xác nhận; sau hiệu chỉnh cho 324 lần thử, cả hai khoảng chứa 0. Hơn thị trường 4 trong 7 năm (thua 2020, 2024, 2025). Tương quan hạng Sharpe giữa phát triển và xác nhận qua 324 cấu hình là 0,46. Chia theo điểm không tốt hơn chia đều. Ngưỡng bán nông (−0,06) cho kết quả âm ở xác nhận, ngưỡng sâu (−0,1 đến −0,2) ổn định.
- Chạy lại (replay): tạo tài khoản với `replay: true` để tài khoản giao dịch ngay theo 5 phiên gần nhất (bắt đầu từ phiên thứ 6 tính ngược). Điểm các ngày trước ngày huấn luyện là điểm trong mẫu (cao tới 0,22 so với khoảng 0,04 ngoài mẫu), nên kết quả chỉ cho thấy cách chiến thuật vận hành; form tạo tài khoản ghi rõ điều này.
- Hiệu năng: `GET /api/paper` đọc và tính điểm 19 mã mất khoảng 0,95 giây; kết quả được cache theo thời điểm sửa file nến và nhật ký nên còn khoảng 10 đến 30 ms. Giao diện luôn hiện skeleton đúng hình dạng khi chờ, không giữ dữ liệu của mục cũ sau khi bấm, và tải sẵn dữ liệu khi rê chuột vào mục Paper Trading hoặc một mã.
- Giới hạn: chỉ giữ tối đa 3 mã nên rất tập trung; kết quả toàn giai đoạn lạc quan vì đã chọn trong nhiều cấu hình; chưa có bằng chứng thống kê rằng chiến thuật vượt thị trường.
- Trạng thái: xong. Kiểm tra: `make test`.

## Quyết định cần chốt

- **Tập kiểm tra giữ lại:** mẫu báo cáo hỏi "tập kiểm tra giữ lại", còn walk-forward không có một tập riêng. Đề xuất: coi các khối test của walk-forward là tập kiểm tra, và tinh chỉnh siêu tham số trong từng fold trên 20% cuối của train (đúng [data-preprocess.md](data-preprocess.md), mục 5). Cần nêu rõ trong báo cáo.
- **Số mã báo cáo chi tiết:** báo cáo cả bốn mã hay chọn một mã làm minh họa cho hình (ma trận nhầm lẫn, learning curve).
