# Quy trình thực hiện

Tài liệu này sắp xếp các bước làm theo đúng bốn nhiệm vụ của đề bài ([idea.md](idea.md)), ghi trạng thái từng bước, script chạy và mục báo cáo tương ứng. Kết quả chi tiết của phần huấn luyện nằm ở [train.md](train.md). Thiết kế tiền xử lý nằm ở [data-preprocess.md](data-preprocess.md).

Trạng thái: **xong**, **một phần**, **chưa làm**. Cập nhật cột này mỗi khi hoàn thành một bước.

## Đối chiếu với đề bài

| Nhiệm vụ của đề | Bước tương ứng | Trạng thái |
|---|---|---|
| 1. Nghiên cứu chuỗi giá, chỉ báo kỹ thuật, phát biểu bài toán phân loại | B1 | Xong (Chương 1, 2 của báo cáo) |
| 2. Thu thập dữ liệu, tính chỉ báo làm đặc trưng | B2 đến B5 | Xong |
| 3. Huấn luyện Logistic Regression, Random Forest, XGBoost bằng walk-forward; so sánh với mua và nắm giữ, dự đoán ngẫu nhiên | B6, B8, B9 | Mô hình ban đầu xong; tinh chỉnh chưa làm |
| 4. Đánh giá bằng Accuracy, F1, ROC-AUC và backtest; thảo luận giới hạn dự đoán giá và quá khớp | B6, B7, B10, B11 | Chỉ số, backtest và phân tích quá khớp xong; thảo luận chưa làm |

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

- Chạy: [notebooks/eda.ipynb](../notebooks/eda.ipynb)
- Báo cáo: mục 3.2.
- Trạng thái: xong.

### B5. Tạo đặc trưng và nhãn (nhiệm vụ 2)

- Chạy: `python scripts/preprocess_data.py`
- Đầu ra: `data/processed/<khung>/<mã>.csv` gồm 25 đặc trưng (khung 1D), `r_next`, `label`.
- Báo cáo: mục 3.4.
- Trạng thái: xong.

### B6. Huấn luyện mô hình ban đầu và baseline (nhiệm vụ 3, 4)

- Chạy: `python scripts/train_models.py`
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

- Báo cáo: mục 3.8 và 3.9 (bảng `tab:sieuthamso`, `tab:ablation`, hình `fig:sosanhmohinh`).
- Trạng thái: chưa làm.

### B9. Chọn mô hình cuối và đánh giá tổng quát hóa

Chọn dựa trên đánh đổi giữa F1, độ ổn định giữa các fold, thời gian chạy và khả năng diễn giải. Khối test của walk-forward là tập kiểm tra giữ lại; chỉ báo cáo một lần sau khi đã chốt cấu hình. Báo cáo cả kết quả không tốt, không chỉ báo lần chạy tốt nhất.
- Báo cáo: mục 3.10.
- Trạng thái: chưa làm.

### B10. Backtest và so sánh với baseline (nhiệm vụ 3, 4)

Chạy lại backtest cho cấu hình cuối. Có thể thêm phân tích nhạy cảm với chi phí giao dịch, hoặc chỉ giao dịch khi xác suất dự đoán vượt ngưỡng, để giảm số lần giao dịch.
- Báo cáo: mục 3.6 và 3.10.
- Trạng thái: một phần (backtest của mô hình ban đầu đã có).

### B11. Thảo luận giới hạn (nhiệm vụ 4)

Giới hạn của việc dự đoán giá cổ phiếu (thị trường gần hiệu quả, nhiễu lớn, thay đổi chế độ), nguy cơ quá khớp, chi phí giao dịch, thiên lệch sống sót và giai đoạn tăng giá của mẫu. Nên viết sau khi có kết quả B7 đến B10.
- Báo cáo: mục 3.11, phần Kết luận và hướng phát triển.
- Trạng thái: chưa làm.

### B12. Thí nghiệm mở rộng khung nến (tùy chọn)

Chạy `python scripts/train_models.py --resolution 1H` hoặc khung phút. Khung phút chỉ có 63 phiên nên chỉ đáng làm với 1H. Chỉ làm nếu còn thời gian, và không đưa vào kết luận chính.
- Trạng thái: chưa làm.

### B13. Hoàn thiện báo cáo

1. Điền số liệu từ `results/` vào Chương 3, xóa các `\huongdan` và `\dots` còn lại.
2. Viết Kết luận, Hướng phát triển, Chương 4 (hướng dẫn cài đặt, nhớ ghi `brew install libomp` cho macOS).
3. Khai báo việc dùng AI tạo sinh trong Lời cam đoan.
4. Biên dịch: `cd docs/project-report/bao-cao && latexmk bao_cao.tex`.
5. Slide và phần triển khai cloud (theo phân công).
- Trạng thái: chưa làm.

## Quyết định cần chốt

- **Tập kiểm tra giữ lại:** mẫu báo cáo hỏi "tập kiểm tra giữ lại", còn walk-forward không có một tập riêng. Đề xuất: coi các khối test của walk-forward là tập kiểm tra, và tinh chỉnh siêu tham số trong từng fold trên 20% cuối của train (đúng [data-preprocess.md](data-preprocess.md), mục 5). Cần nêu rõ trong báo cáo.
- **Số mã báo cáo chi tiết:** báo cáo cả bốn mã hay chọn một mã làm minh họa cho hình (ma trận nhầm lẫn, learning curve).
