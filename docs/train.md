# Huấn luyện và đánh giá

Ghi lại những gì đã làm ở bước huấn luyện (B6 trong [flow.md](flow.md)), kèm số liệu lấy từ `results/1D/`, để dùng viết mục 3.5 và 3.6 của báo cáo. Mọi số liệu dưới đây do `scripts/train_models.py` tạo ra, `random_state = 42`.

Trạng thái: **mô hình ban đầu với siêu tham số cố định** (B6), **phân tích kết quả** (B7, mục 9) và **ablation, class_weight, tinh chỉnh siêu tham số** (B8, mục 10).

## 1. Chạy lại

```bash
.venv/bin/pip install -r requirements.txt
brew install libomp
.venv/bin/python scripts/train_models.py
.venv/bin/python scripts/analyze_results.py
.venv/bin/python scripts/tune_models.py
.venv/bin/python scripts/select_final_model.py
```

`train_models.py` huấn luyện và ghi `results/`. `analyze_results.py` đọc `results/` rồi vẽ hình vào `docs/project-report/bao-cao/images/` và in các bảng ở mục 9.

`libomp` chỉ cần trên macOS, vì XGBoost phụ thuộc vào thư viện này. Thời gian chạy khoảng 3 phút trên máy phát triển. Tham số `--resolution` chọn khung nến, mặc định `1D`.

Đầu ra trong `results/1D/`:

| Tệp | Nội dung |
|---|---|
| `fold_metrics.csv` | Accuracy, F1 macro, ROC-AUC trên tập test và tập train, số phiên train, thời gian huấn luyện của từng mã, mô hình, fold |
| `predictions.csv` | Nhãn thật, nhãn dự đoán, ba xác suất và `r_next` trên từng phiên test |
| `feature_importance.csv` | Độ quan trọng đặc trưng của Random Forest và XGBoost trong từng fold |
| `backtest.csv` | Lợi nhuận, Sharpe, số giao dịch của từng mã và mô hình |
| `summary.csv` | Trung bình và độ lệch chuẩn theo mã và mô hình, kèm dòng `ALL` gộp bốn mã |

## 2. Dữ liệu và chia fold

- Dữ liệu: `data/processed/1D/<mã>.csv`, 25 đặc trưng (12 nhóm lõi, 13 nhóm bổ trợ), nhãn ba lớp với ngưỡng 0,5%.
- Mỗi mã huấn luyện riêng. Chia walk-forward cửa sổ mở rộng bằng hàm `walk_forward_splits` của `preprocess_data.py`: train đầu 750 phiên, mỗi khối test 63 phiên, các khối test liền nhau, bỏ 1 phiên giữa train và test.
- Nhãn mã hóa `label + 1` thành `0, 1, 2` (giảm, ngang, tăng) vì XGBoost yêu cầu nhãn bắt đầu từ 0.

| Mã | Số fold | Khối test đầu | Khối test cuối |
|---|---:|---|---|
| TCB | 20 | 2021-07-22 | 2026-08-10 |
| CTG | 27 | 2019-12-18 | 2026-10-14 |
| VNM | 27 | 2019-12-18 | 2026-10-14 |
| ACB | 27 | 2019-12-16 | 2026-10-19 |

## 3. Mô hình và baseline

| Tên | Cấu hình |
|---|---|
| `logistic` | `StandardScaler` rồi `LogisticRegression(max_iter=1000)`, đóng gói trong `Pipeline`, scaler fit lại trong từng fold |
| `random_forest` | `RandomForestClassifier(n_estimators=300)`, các tham số khác mặc định |
| `xgboost` | `XGBClassifier(n_estimators=300, objective="multi:softprob")`, các tham số khác mặc định |
| `majority` | `DummyClassifier(strategy="most_frequent")`: luôn dự đoán lớp đa số của tập train |
| `random` | Rút nhãn ngẫu nhiên theo tỷ lệ lớp của tập train, lặp 100 lần với seed khác nhau, lấy trung bình |
| `buy_and_hold` | Mua ở đầu giai đoạn test, giữ đến hết. Chỉ có trong backtest |

Các tham số mặc định của Random Forest (cây không giới hạn độ sâu) và XGBoost (`max_depth=6`, `learning_rate=0.3`) chưa được chọn theo dữ liệu. Đây là điểm xuất phát cho mục tối ưu hóa.

## 4. Chỉ số đánh giá

- Accuracy, F1 macro (trung bình ba lớp, tránh bị lớp đông chi phối), ROC-AUC one-vs-rest macro (từ `predict_proba`). Mỗi chỉ số tính trên từng khối test, rồi lấy trung bình và độ lệch chuẩn qua các fold.
- ROC-AUC không định nghĩa cho `random` (không có xác suất), nên để trống. `majority` luôn có ROC-AUC bằng 0,5 vì điểm số không đổi.
- Backtest long-only trên toàn bộ các khối test ghép liền nhau của từng mã:
  - Dự đoán tăng thì mua hoặc giữ, dự đoán giảm thì bán và đứng ngoài, dự đoán ngang thì giữ nguyên trạng thái.
  - Quyết định cuối phiên `t` ăn lợi suất log `r_next` của phiên `t+1`.
  - Phí 0,15% mỗi chiều, thuế 0,1% khi bán. Vị thế còn mở ở cuối giai đoạn được đóng và tính phí bán.
  - Sharpe tính từ lợi suất mỗi kỳ (ngày, hoặc nến với khung nhỏ hơn ngày), nhân căn số kỳ mỗi năm (252 nhân số nến mỗi phiên), không trừ lãi suất phi rủi ro.
  - Mua và nắm giữ trả phí một lần mua và một lần bán. Dự đoán ngẫu nhiên lấy trung bình lợi nhuận của 100 lần rút.

## 5. Kết quả

Giá trị trung bình ± độ lệch chuẩn qua các fold. Thời gian là giây huấn luyện trung bình mỗi fold.

### 5.1 Gộp bốn mã

| Mô hình | Accuracy | F1 macro | ROC-AUC | Thời gian (s) |
|---|---|---|---|---:|
| majority | 0,348 ± 0,086 | 0,170 ± 0,032 | 0,500 ± 0,000 | 0,00 |
| random | 0,335 ± 0,010 | 0,324 ± 0,009 | – | 0,00 |
| logistic | 0,388 ± 0,079 | 0,322 ± 0,055 | 0,530 ± 0,059 | 0,01 |
| random_forest | 0,386 ± 0,071 | 0,347 ± 0,060 | 0,538 ± 0,060 | 0,36 |
| xgboost | 0,365 ± 0,068 | 0,342 ± 0,065 | 0,523 ± 0,060 | 1,20 |

### 5.2 Theo từng mã

**TCB**

| Mô hình | Accuracy | F1 macro | ROC-AUC |
|---|---|---|---|
| majority | 0,345 ± 0,063 | 0,170 ± 0,024 | 0,500 ± 0,000 |
| random | 0,334 ± 0,007 | 0,326 ± 0,007 | – |
| logistic | 0,363 ± 0,069 | 0,327 ± 0,055 | 0,521 ± 0,055 |
| random_forest | 0,361 ± 0,061 | 0,336 ± 0,055 | 0,520 ± 0,058 |
| xgboost | 0,340 ± 0,049 | 0,326 ± 0,047 | 0,495 ± 0,059 |

**CTG**

| Mô hình | Accuracy | F1 macro | ROC-AUC |
|---|---|---|---|
| majority | 0,347 ± 0,066 | 0,171 ± 0,023 | 0,500 ± 0,000 |
| random | 0,338 ± 0,013 | 0,325 ± 0,006 | – |
| logistic | 0,387 ± 0,079 | 0,329 ± 0,067 | 0,548 ± 0,060 |
| random_forest | 0,390 ± 0,073 | 0,349 ± 0,049 | 0,555 ± 0,056 |
| xgboost | 0,389 ± 0,074 | 0,363 ± 0,070 | 0,534 ± 0,055 |

**VNM**

| Mô hình | Accuracy | F1 macro | ROC-AUC |
|---|---|---|---|
| majority | 0,365 ± 0,117 | 0,175 ± 0,043 | 0,500 ± 0,000 |
| random | 0,334 ± 0,008 | 0,323 ± 0,009 | – |
| logistic | 0,399 ± 0,081 | 0,322 ± 0,053 | 0,537 ± 0,056 |
| random_forest | 0,412 ± 0,060 | 0,363 ± 0,066 | 0,540 ± 0,049 |
| xgboost | 0,381 ± 0,058 | 0,352 ± 0,058 | 0,537 ± 0,057 |

**ACB**

| Mô hình | Accuracy | F1 macro | ROC-AUC |
|---|---|---|---|
| majority | 0,335 ± 0,083 | 0,165 ± 0,032 | 0,500 ± 0,000 |
| random | 0,333 ± 0,008 | 0,323 ± 0,011 | – |
| logistic | 0,396 ± 0,082 | 0,312 ± 0,046 | 0,513 ± 0,061 |
| random_forest | 0,376 ± 0,081 | 0,337 ± 0,068 | 0,533 ± 0,073 |
| xgboost | 0,345 ± 0,075 | 0,323 ± 0,074 | 0,519 ± 0,063 |

### 5.3 Backtest

Lợi nhuận tích lũy trên toàn bộ giai đoạn test của từng mã / Sharpe / số lần mua. Giai đoạn test của mỗi mã khác nhau (bảng ở mục 2), nên không cộng được giữa các mã.

| Mã | Mua và nắm giữ | majority | random | logistic | random_forest | xgboost |
|---|---|---|---|---|---|---|
| TCB | 30,6% / 0,17 / 1 | -3,5% / -0,02 / 2 | -51,9% / -0,71 / 221 | 5,7% / 0,05 / 138 | -43,1% / -0,43 / 182 | -69,7% / -0,97 / 199 |
| CTG | 226,9% / 0,53 / 1 | 36,4% / 0,23 / 2 | -43,3% / -0,42 / 316 | -41,2% / -0,34 / 268 | 2,1% / 0,01 / 303 | 57,2% / 0,28 / 297 |
| VNM | -18,1% / -0,12 / 1 | 0,0% / – / 0 | -68,3% / -1,01 / 266 | -24,2% / -0,22 / 138 | -12,0% / -0,11 / 177 | -58,1% / -0,72 / 236 |
| ACB | 252,6% / 0,65 / 1 | 252,6% / 0,65 / 1 | -31,8% / -0,34 / 293 | -39,5% / -0,32 / 203 | 27,5% / 0,16 / 215 | -28,0% / -0,22 / 234 |

Với `majority` ở ACB, mô hình luôn dự đoán "tăng" nên giống hệt mua và nắm giữ. Ở VNM, `majority` luôn dự đoán "ngang" nên không bao giờ vào thị trường.

## 6. Nhận xét

Các nhận xét dưới đây chỉ dựa trên số liệu ở mục 5. Phần giải thích nguyên nhân là giả thuyết, cần kiểm tra ở B7.

1. **Khả năng dự đoán yếu.** F1 macro của Random Forest (0,347) và XGBoost (0,342) cao hơn dự đoán ngẫu nhiên (0,324) khoảng 0,02, ROC-AUC chỉ 0,52 đến 0,54. Logistic có F1 macro bằng ngẫu nhiên (0,322) dù Accuracy cao hơn (0,388 so với 0,335). Điều này gợi ý Logistic dự đoán lệch về một vài lớp; cần xem ma trận nhầm lẫn để xác nhận.
2. **Chênh lệch nhỏ so với độ dao động.** Độ lệch chuẩn giữa các fold (khoảng 0,06) lớn hơn khoảng cách giữa mô hình và ngẫu nhiên (khoảng 0,02). Tỷ lệ fold mà F1 macro cao hơn ngẫu nhiên: Random Forest 66%, XGBoost 59%, Logistic 51%. Tỷ lệ fold có ROC-AUC trên 0,5: Random Forest 75%, Logistic 69%, XGBoost 63%. Chưa chạy kiểm định thống kê.
3. **Mô hình ít khác biệt giữa các mã.** CTG và VNM cho kết quả tốt hơn TCB và ACB đôi chút. XGBoost ở TCB có ROC-AUC 0,495, tức không tốt hơn đoán mò.
4. **Backtest không ủng hộ các mô hình.** Ba mô hình học máy giao dịch 138 đến 303 lần trong giai đoạn test, nên phí và thuế ăn phần lớn lợi nhuận, và không mô hình nào trong ba mô hình này thắng mua và nắm giữ ở TCB, CTG và ACB. Ở VNM (thị trường đi xuống, mua và nắm giữ -18,1%) chỉ `majority` (đứng ngoài, 0%) và Random Forest (-12,0%) tốt hơn. Dự đoán ngẫu nhiên lỗ nặng ở cả bốn mã (-32% đến -68%), cho thấy chi phí giao dịch tự nó đã rất lớn với tần suất giao dịch này.
5. **Thời gian huấn luyện** không đáng kể: Logistic 0,01 s, Random Forest 0,36 s, XGBoost 1,20 s mỗi fold.

## 7. Lưu ý khi viết báo cáo

- Đây là **một lần chạy** với siêu tham số mặc định, `random_state = 42`. Không kết luận "mô hình A tốt hơn mô hình B" khi chênh lệch nhỏ hơn độ lệch chuẩn giữa các fold.
- Giai đoạn test của CTG và ACB có xu hướng tăng mạnh (mua và nắm giữ +227% và +253%). Baseline này vì vậy rất khó thắng, và `majority` ở ACB trông tốt chỉ vì thị trường tăng.
- Backtest chưa tính trượt giá, thanh khoản hay quy định T+2 của thị trường Việt Nam. Chỉ nên trình bày như một mô phỏng đơn giản (đúng yêu cầu đề bài).
- Mỗi mã có giai đoạn test khác nhau và độ dài khác nhau (20 hoặc 27 fold), nên dòng "gộp bốn mã" là trung bình theo fold, mỗi fold một phiếu. Mã nhiều fold có trọng số lớn hơn.
- Đề bài yêu cầu thảo luận giới hạn của việc dự đoán giá và nguy cơ quá khớp. Số liệu về quá khớp nằm ở mục 9.

### Ghi chép chất lượng dữ liệu (cho mục 3.3)

Ghi lại các phát hiện khi kiểm tra dữ liệu trước khi huấn luyện:
- Khung 1D sạch. Hai chỗ thiếu phiên do nguồn: CTG và VNM thiếu 2018-01-23 và 2018-01-24; ACB thiếu 2020-12-02 đến 2020-12-08. Ảnh hưởng 3 nhãn, giữ nguyên.
- Khung 30 phút của API hỏng: nến buổi sáng chỉ chứa khoảng 0,5% khối lượng thật, tổng khối lượng cả ngày bằng khoảng 60% khung 1D. Đã dựng lại từ khung 5 phút, tổng khối lượng sau đó khớp 1D (sai lệch dưới 0,4%). Khung này chưa dùng trong huấn luyện.
- Các khung 1, 5, 15 phút chỉ có 63 phiên (2026-07-24 đến 2026-10-23), khung 1H có 497 phiên.

## 8. Chưa làm

Xem B13 trong [flow.md](flow.md): điền số liệu vào báo cáo, khai báo dùng AI tạo sinh, slide. B10 (mục 16), B11 (mục 17) và B12 (mục 18) đã xong. Phần còn thiếu của B8 (SVM, Voting/Stacking, lọc đặc trưng tương quan) ghi ở mục 10.5.

## 9. Phân tích kết quả (B7)

Mọi số liệu do `scripts/analyze_results.py` in ra, gộp bốn mã, từ cùng một lần chạy ở mục 5. Hình lưu tại `docs/project-report/bao-cao/images/`.

### 9.1 Quá khớp: so sánh tập train và tập test

Hình `overfitting.png`. Trung bình qua các fold:

| Mô hình | F1 macro train | F1 macro test | Chênh | ROC-AUC train | ROC-AUC test | Chênh |
|---|---:|---:|---:|---:|---:|---:|
| Logistic | 0,408 | 0,322 | 0,085 | 0,609 | 0,530 | 0,078 |
| Random Forest | 1,000 | 0,347 | 0,653 | 1,000 | 0,538 | 0,462 |
| XGBoost | 1,000 | 0,342 | 0,658 | 1,000 | 0,523 | 0,477 |

- Random Forest và XGBoost đạt F1 macro và ROC-AUC bằng 1,000 trên tập train ở mọi fold: hai mô hình **thuộc lòng** tập train. Đây là hệ quả của cây không giới hạn độ sâu (Random Forest) và 300 cây với `max_depth=6` (XGBoost) trên dữ liệu có rất ít tín hiệu. Kết quả này là bằng chứng quá khớp nghiêm trọng, và là lý do chính để tinh chỉnh siêu tham số ở B8.
- Logistic có chênh lệch nhỏ (0,085), nhưng F1 macro trên train cũng chỉ 0,408, tức mô hình tuyến tính không học được nhiều từ các đặc trưng này. Đây là dấu hiệu thiếu khả năng biểu diễn hơn là quá khớp.

### 9.2 Ma trận nhầm lẫn

Hình `confusion_matrix.png`. Gộp bốn mã, 6.363 mẫu test. Tỷ lệ theo hàng (nhãn thật), trong ngoặc là số mẫu.

| Mô hình | Giảm đúng | Ngang đúng | Tăng đúng |
|---|---:|---:|---:|
| Logistic | 32,7% (691) | 48,6% (1022) | 35,2% (757) |
| Random Forest | 37,2% (785) | 36,0% (757) | 42,6% (915) |
| XGBoost | 36,4% (769) | 32,9% (692) | 40,2% (864) |

Tỷ lệ nhãn dự đoán so với nhãn thật (giảm / ngang / tăng):

| | Giảm | Ngang | Tăng |
|---|---:|---:|---:|
| Thực tế | 33,2% | 33,0% | 33,8% |
| Logistic | 30,8% | 38,6% | 30,6% |
| Random Forest | 34,8% | 28,1% | 37,1% |
| XGBoost | 34,7% | 27,6% | 37,7% |

- Giả thuyết ở mục 6 về Logistic được xác nhận một phần: Logistic dự đoán "ngang" nhiều hơn thực tế (38,6% so với 33,0%) và chỉ nhận ra lớp "ngang" tốt (48,6%). Hai lớp còn lại gần như đoán ngẫu nhiên (32,7% và 35,2%). Đó là lý do Accuracy cao hơn ngẫu nhiên nhưng F1 macro thì không.
- Random Forest và XGBoost thiên về dự đoán "tăng" (37%) và "giảm" (35%), ít dự đoán "ngang" (28%). Nhận diện "tăng" tốt nhất (42,6% và 40,2%), "ngang" kém nhất. Phần lớn nhầm lẫn là giữa các lớp kề nhau và cả hai hướng ngược nhau, nên mô hình không tách được hướng một cách đáng tin.

### 9.3 Đặc trưng quan trọng

Hình `feature_importance.png`. Độ quan trọng dựa trên mức giảm tạp chất (Random Forest) và độ lợi (XGBoost), chuẩn hóa tổng bằng 1 mỗi fold, rồi trung bình qua các fold và mã.

- Độ quan trọng gần như **phẳng**: 25 đặc trưng, nếu đều nhau thì mỗi đặc trưng 0,040; đặc trưng cao nhất chỉ 0,048 (`atr14` ở cả hai mô hình). Không có đặc trưng nào chi phối.
- Random Forest xếp trên cùng các đặc trưng về biến động và khối lượng: `atr14`, `volat_5`, `vol_chg`, `hl_range`, `vol_ratio`, `volat_20`, `bb_width`. XGBoost xếp `atr14` đầu, sau đó là các đặc trưng giá so với trung bình động (`close_sma20`, `close_sma5`, `close_ema12`, `close_sma10`) và `ret_5`.
- Tỷ trọng nhóm lõi (12 chỉ báo theo đề) so với nhóm bổ trợ (13): Random Forest 43,8% và 56,2%; XGBoost 48,1% và 51,9%. Nếu các đặc trưng đều nhau, nhóm lõi chiếm 12/25 = 48%. Vậy nhóm lõi không quan trọng hơn nhóm bổ trợ; thí nghiệm ablation ở B8 mới cho biết nhóm bổ trợ có thực sự giúp hay không.
- Lưu ý: độ quan trọng kiểu tạp chất thiên về đặc trưng liên tục, nên chỉ dùng để mô tả, không dùng để loại đặc trưng (đúng nguyên tắc chống rò rỉ).

### 9.4 Đường cong học tập

Hình `learning_curve.png`. Mỗi điểm là F1 macro trung bình (gộp mã) ở một fold, làm mượt bằng trung bình trượt 5 fold. Trục ngang là số phiên trong tập train (750 đến 2.400, các fold giống nhau giữa các mã, riêng các fold từ số 21 trở đi không có TCB).

- F1 macro trên train: Random Forest và XGBoost luôn bằng 1,0; Logistic khoảng 0,40 đến 0,42.
- F1 macro trên test **không tăng** khi có thêm dữ liệu huấn luyện: Logistic từ khoảng 0,35 xuống khoảng 0,31; Random Forest từ khoảng 0,37 xuống khoảng 0,34; XGBoost từ khoảng 0,36 xuống khoảng 0,30. Các đường test luôn gần mức ngẫu nhiên (0,324).
- Hiểu theo hướng thận trọng: giới hạn nằm ở lượng tín hiệu trong đặc trưng, không phải ở lượng dữ liệu. Có thể dữ liệu cũ (nhiều năm trước) kém liên quan đến giai đoạn test hơn, nhưng đây là giả thuyết chưa kiểm tra (ví dụ bằng cửa sổ trượt có độ dài cố định).

### 9.5 Ổn định theo thời gian

Hình `f1_by_year.png`. F1 macro trung bình theo năm của khối test (gộp bốn mã):

| Năm | Logistic | Random Forest | XGBoost | Ngẫu nhiên |
|---|---:|---:|---:|---:|
| 2019 | 0,410 | 0,385 | 0,371 | 0,329 |
| 2020 | 0,305 | 0,373 | 0,350 | 0,324 |
| 2021 | 0,344 | 0,337 | 0,345 | 0,326 |
| 2022 | 0,315 | 0,342 | 0,349 | 0,323 |
| 2023 | 0,308 | 0,351 | 0,354 | 0,324 |
| 2024 | 0,304 | 0,340 | 0,345 | 0,322 |
| 2025 | 0,344 | 0,343 | 0,333 | 0,323 |
| 2026 | 0,311 | 0,338 | 0,307 | 0,324 |

- Năm 2019 chỉ có 3 fold (một fold mỗi mã ACB, CTG, VNM, bắt đầu giữa tháng 12/2019), nên số cao ở 2019 không đáng tin. Năm 2026 chưa trọn năm.
- Random Forest cao hơn ngẫu nhiên ở cả bảy năm 2020 đến 2026, nhưng mức hơn chỉ 0,01 đến 0,05. XGBoost hơn ngẫu nhiên trừ 2026 (0,307, thấp hơn 0,324). Logistic thấp hơn ngẫu nhiên ở 2020, 2022, 2023, 2024 và 2026.
- Không thấy xu hướng cải thiện rõ ràng theo thời gian; hiệu năng của cả ba mô hình nằm gần mức ngẫu nhiên và dao động theo năm.

### 9.6 Kết luận cho B8

1. Random Forest và XGBoost cần giới hạn độ phức tạp (độ sâu, số mẫu tối thiểu ở lá, tốc độ học, số cây). Ứng viên đầu tiên cho tinh chỉnh.
2. Logistic cần thử điều chuẩn khác (`C`) và có thể thêm `class_weight`, vì nó lệch về lớp "ngang".
3. Thí nghiệm "chỉ nhóm lõi" so với "lõi + bổ trợ" cần làm vì độ quan trọng không cho thấy nhóm nào vượt trội.
4. Với tín hiệu yếu như vậy, kỳ vọng thực tế là chỉ cải thiện nhỏ. Báo cáo nên đo mức cải thiện bằng độ lệch chuẩn giữa các fold, không chỉ bằng giá trị trung bình.

## 10. Cải tiến mô hình (B8)

`scripts/tune_models.py` chạy lại walk-forward với đúng các fold của mục 2 (101 fold, 4 mã) cho năm biến thể, mỗi biến thể huấn luyện ba mô hình. Kết quả lưu ở `results/1D/tuning/` (`fold_metrics.csv`, `predictions.csv`, `backtest.csv`, `best_params.csv`, `summary.csv`). Thời gian chạy khoảng 5 phút, `random_state = 42`.

| Biến thể | Đặc trưng | `class_weight` | Siêu tham số |
|---|---|---|---|
| `all_default` | 25 | không | mặc định, giống mục 3 |
| `core_default` | 12 (nhóm lõi) | không | mặc định |
| `all_balanced` | 25 | `balanced` (XGBoost dùng `sample_weight` tương ứng) | mặc định |
| `core_tuned` | 12 | không | chọn trong từng fold |
| `all_tuned` | 25 | không | chọn trong từng fold |

**Cách tinh chỉnh.** Trong mỗi fold, 20% cuối của tập train (theo thời gian, cách 1 phiên) làm validation. `GridSearchCV` với một lần chia cố định, chấm bằng F1 macro, `refit=True` huấn luyện lại trên toàn bộ train của fold. Khối test không được dùng để chọn gì.

| Mô hình | Lưới |
|---|---|
| Logistic | `C` ∈ {0,01; 0,1; 1; 10} |
| Random Forest | `max_depth` ∈ {3, 5, 8} × `min_samples_leaf` ∈ {5, 20}, 300 cây |
| XGBoost | `max_depth` ∈ {2, 3, 5} × `learning_rate` ∈ {0,03; 0,1}, 300 cây |

### 10.1 Môi trường chạy lại

Lần chạy này dùng Python 3.14 với phiên bản thư viện mới hơn `requirements.txt` (scikit-learn 1.9.1, XGBoost 3.4.1, pandas 3.1.1, numpy 2.5.4), vì các phiên bản ghim không cài được trên Python 3.14. Logistic, majority và random cho kết quả giống hệt mục 5; Random Forest gần như giống; XGBoost khác nhẹ (F1 macro gộp 0,348 thay vì 0,342). Vì vậy mọi so sánh ở mục 10 dùng `all_default` chạy cùng môi trường làm mốc, không dùng số ở mục 5. Trước khi đưa vào báo cáo cần chạy lại cả `train_models.py` và `tune_models.py` trong cùng một môi trường.

### 10.2 Kết quả gộp bốn mã

Trung bình ± độ lệch chuẩn qua 101 fold. Mốc ngẫu nhiên: F1 macro 0,324.

| Biến thể | Mô hình | F1 macro | ROC-AUC | F1 train |
|---|---|---|---|---:|
| `all_default` | Logistic | 0,322 ± 0,055 | 0,530 ± 0,059 | 0,408 |
| | Random Forest | 0,346 ± 0,060 | 0,538 ± 0,059 | 1,000 |
| | XGBoost | 0,348 ± 0,061 | 0,528 ± 0,058 | 1,000 |
| `core_default` | Logistic | 0,292 ± 0,066 | 0,516 ± 0,060 | 0,353 |
| | Random Forest | 0,338 ± 0,069 | 0,524 ± 0,063 | 1,000 |
| | XGBoost | 0,333 ± 0,064 | 0,514 ± 0,060 | 1,000 |
| `all_balanced` | Logistic | 0,333 ± 0,062 | 0,530 ± 0,059 | 0,410 |
| | Random Forest | 0,350 ± 0,060 | 0,535 ± 0,058 | 1,000 |
| | XGBoost | 0,351 ± 0,063 | 0,526 ± 0,056 | 1,000 |
| `core_tuned` | Logistic | 0,295 ± 0,070 | 0,516 ± 0,059 | 0,360 |
| | Random Forest | 0,323 ± 0,062 | 0,529 ± 0,060 | 0,624 |
| | XGBoost | 0,332 ± 0,061 | 0,525 ± 0,060 | 0,789 |
| `all_tuned` | Logistic | 0,320 ± 0,061 | 0,533 ± 0,061 | 0,406 |
| | Random Forest | 0,325 ± 0,060 | 0,536 ± 0,063 | 0,693 |
| | XGBoost | 0,345 ± 0,062 | 0,532 ± 0,055 | 0,831 |

### 10.3 So sánh theo cặp (cùng fold)

Chênh lệch F1 macro trung bình theo từng fold, kèm sai số chuẩn của trung bình (n = 101). Các fold của cùng một mã chồng lấn dữ liệu train và tự tương quan, nên sai số chuẩn chỉ mang tính tham khảo, không phải kiểm định thống kê.

| Biến thể | Mô hình | So với ngẫu nhiên | Tỷ lệ fold hơn ngẫu nhiên | So với `all_default` |
|---|---|---:|---:|---:|
| `all_default` | Logistic | -0,002 ± 0,006 | 50% | – |
| | Random Forest | +0,022 ± 0,006 | 65% | – |
| | XGBoost | +0,024 ± 0,006 | 62% | – |
| `core_default` | Logistic | -0,033 ± 0,007 | 32% | -0,031 ± 0,007 |
| | Random Forest | +0,014 ± 0,007 | 58% | -0,008 ± 0,008 |
| | XGBoost | +0,009 ± 0,007 | 52% | -0,015 ± 0,007 |
| `all_balanced` | Logistic | +0,009 ± 0,006 | 58% | +0,011 ± 0,006 |
| | Random Forest | +0,026 ± 0,006 | 63% | +0,004 ± 0,005 |
| | XGBoost | +0,027 ± 0,006 | 66% | +0,003 ± 0,006 |
| `core_tuned` | Logistic | -0,029 ± 0,007 | 33% | -0,028 ± 0,007 |
| | Random Forest | -0,001 ± 0,006 | 51% | -0,023 ± 0,007 |
| | XGBoost | +0,008 ± 0,006 | 55% | -0,016 ± 0,007 |
| `all_tuned` | Logistic | -0,005 ± 0,006 | 46% | -0,003 ± 0,004 |
| | Random Forest | +0,001 ± 0,006 | 47% | -0,021 ± 0,006 |
| | XGBoost | +0,021 ± 0,006 | 54% | -0,003 ± 0,006 |

### 10.4 Nhận xét

1. **Nhóm bổ trợ có ích.** Bỏ 13 đặc trưng bổ trợ làm F1 macro giảm ở cả ba mô hình: Logistic -0,031, XGBoost -0,015, Random Forest -0,008 (cùng cỡ sai số chuẩn, không rõ ràng). Với Logistic, bản chỉ có 12 đặc trưng lõi còn thấp hơn ngẫu nhiên 0,033. ROC-AUC cũng giảm theo (0,530 xuống 0,516 ở Logistic). Đặc trưng lõi theo đề bài một mình không đủ.
2. **`class_weight` chỉ cải thiện nhỏ.** Cao nhất ở Logistic (+0,011), còn Random Forest và XGBoost (+0,003 đến +0,004) nằm trong sai số. Điều này hợp lý vì nhãn đã gần cân bằng. Logistic vẫn chỉ hơn ngẫu nhiên 0,009.
3. **Tinh chỉnh không làm tăng F1 macro, và có chỗ làm giảm.** Random Forest giảm 0,021 (sai số chuẩn 0,006); XGBoost và Logistic không đổi trong sai số. ROC-AUC gần như không đổi (Random Forest 0,538 xuống 0,536; XGBoost 0,528 lên 0,532). Tinh chỉnh giảm mức thuộc lòng train (F1 train của Random Forest từ 1,000 xuống 0,693, XGBoost xuống 0,831), nhưng chênh lệch train với test vẫn lớn và F1 test không khá hơn. Giảm quá khớp trên train không đồng nghĩa với tổng quát hóa tốt hơn trên dữ liệu thiếu tín hiệu.
4. **Siêu tham số được chọn không ổn định giữa các fold.** XGBoost: sáu tổ hợp được chọn lần lượt 14 đến 21 trong 101 fold. Logistic (`all_tuned`): `C` = 0,01 được chọn 42 lần, 10 được chọn 26 lần. Validation 20% cuối của train chỉ có khoảng 150 đến 480 mẫu, quá nhiễu để phân biệt các cấu hình. Với Random Forest, `max_depth = 8` (phức tạp nhất trong lưới) được chọn 64 lần trong 101 fold. Giả thuyết cho việc F1 macro giảm dù ROC-AUC không đổi: cây nông dự đoán sát tỷ lệ lớp hơn nên nhận diện ba lớp kém đều; chưa kiểm tra.
5. **Backtest không nhất quán với chỉ số phân loại.** `core_default` Logistic có F1 thấp nhất (0,292) nhưng lại cho lợi nhuận cao nhất ở ACB trong mười lăm kết hợp (+167%, so với mua và nắm giữ +253%), với chỉ 78 giao dịch trung bình mỗi mã so với 187 của Logistic ở `all_default`. Ở CTG và ACB không cấu hình nào thắng mua và nắm giữ (+227% và +253%). Ở TCB chỉ `all_balanced` Logistic thắng (+48,1% so với +30,6%). Ở VNM (mua và nắm giữ -18,1%) nhiều cấu hình tốt hơn, trong đó `core_default` Logistic đạt +16,9%. Với 4 mã, một giai đoạn test và 15 kết hợp so sánh, không rút ra kết luận từ các con số này.
6. **Mức độ khác biệt nhỏ so với độ dao động.** Độ lệch chuẩn giữa các fold khoảng 0,06, lớn hơn nhiều so với hầu hết các chênh lệch ở mục 10.3 (phần lớn dưới 0,03). Kết luận "biến thể A tốt hơn biến thể B" chỉ đáng tin khi cả sai số chuẩn ở mục 10.3 cũng nhỏ hơn chênh lệch (ví dụ bỏ nhóm bổ trợ ở Logistic, tinh chỉnh Random Forest).

### 10.5 Hệ quả cho B9 và phần chưa làm

- Các biến thể được so sánh trên chính các khối test của walk-forward. Chọn biến thể có điểm test cao nhất rồi báo cáo điểm đó là lạc quan (chọn trên tập kiểm tra). Vì chênh lệch giữa các biến thể nằm trong sai số, B9 nên chốt cấu hình bằng lý do được nêu từ trước (dùng đủ 25 đặc trưng vì mục 10.4 điểm 1, giữ siêu tham số mặc định vì mục 10.4 điểm 3), và báo cáo bảng ở mục 10.2 đầy đủ, kể cả các biến thể không tốt hơn.
- Chưa làm: SVM, Voting/Stacking, lọc đặc trưng tương quan trên 0,95 trong từng fold. Các hướng có thể thử nếu còn thời gian: lưới điều chuẩn mạnh hơn (`min_samples_leaf` lớn, `max_depth` nhỏ hơn cho cây), chọn siêu tham số theo log-loss thay vì F1 macro (ít nhiễu hơn), cửa sổ huấn luyện trượt cố định thay cho cửa sổ mở rộng (mục 9.4), ngưỡng xác suất để giảm số giao dịch (B10).

## 11. Chọn mô hình cuối và đánh giá tổng quát hóa (B9)

`scripts/select_final_model.py` không huấn luyện lại: nó đọc `results/1D/tuning/fold_metrics.csv` (biến thể `all_default`) và các dòng `random`, `majority` của `results/1D/fold_metrics.csv`, rồi ghi `results/1D/final/` (`candidate_comparison.csv`, `final_by_symbol.csv`, `final_by_year.csv`). Các dòng `random` và `majority` giống hệt nhau giữa hai môi trường chạy (mục 10.1) nên dùng chung được.

Khoảng tin cậy 95% là bootstrap 10.000 lần: lấy mẫu lại các fold có hoàn lại trong từng mã, tính lại trung bình gộp. Khoảng này chưa tính tương quan giữa các mã (CTG, VNM, ACB có các khối test cùng thời điểm, nên cùng chịu một biến động thị trường), nên khoảng gộp bốn mã hẹp hơn thực tế. Khoảng theo từng mã ít bị vấn đề này hơn.

### 11.1 So sánh ba ứng viên

Cấu hình: 25 đặc trưng, siêu tham số mặc định (mục 10 cho thấy bỏ đặc trưng, thêm `class_weight` hay tinh chỉnh đều không cải thiện rõ ràng). Gộp bốn mã, 101 fold.

| Tiêu chí | Logistic | Random Forest | XGBoost |
|---|---:|---:|---:|
| F1 macro (trung bình) | 0,322 | 0,346 | 0,348 |
| Độ lệch chuẩn F1 giữa các fold | 0,055 | 0,060 | 0,061 |
| ROC-AUC (trung bình) | 0,530 | 0,538 | 0,528 |
| Tỷ lệ fold F1 hơn ngẫu nhiên | 50,5% | 65,3% | 62,4% |
| Tỷ lệ fold ROC-AUC trên 0,5 | 69,3% | 74,3% | 67,3% |
| F1 train | 0,408 | 1,000 | 1,000 |
| Thời gian huấn luyện mỗi fold (s) | 0,05 | 0,35 | 0,51 |
| F1 hơn ngẫu nhiên [KTC 95%] | -0,002 [-0,013; +0,009] | +0,022 [+0,010; +0,034] | +0,024 [+0,013; +0,035] |
| F1 hơn Random Forest [KTC 95%] | -0,024 [-0,037; -0,011] | – | +0,002 [-0,009; +0,013] |

- Logistic thấp hơn rõ rệt: không hơn ngẫu nhiên và thua Random Forest.
- Random Forest và XGBoost **hòa** về F1: chênh +0,002, khoảng tin cậy chứa 0. Hai mô hình cùng quá khớp train hoàn toàn.
- Khả năng diễn giải: Logistic có hệ số trực tiếp nhưng không học được gì đáng kể. Độ quan trọng đặc trưng của hai mô hình cây gần như phẳng (mục 9.3), nên không bên nào giải thích tốt hơn.

### 11.2 Quyết định

**Mô hình cuối: Random Forest, 25 đặc trưng, siêu tham số mặc định (300 cây), không dùng `class_weight`.**

Lý do, theo thứ tự ưu tiên:
1. F1 macro không phân biệt được Random Forest và XGBoost, nên quyết định dựa trên các tiêu chí còn lại. Random Forest có ROC-AUC cao hơn (0,538 so với 0,528), điểm này quan trọng nếu B10 dùng ngưỡng xác suất để giảm số giao dịch.
2. Random Forest hơn ngẫu nhiên ở nhiều fold hơn (65% so với 62%), và ROC-AUC trên 0,5 ở nhiều fold hơn (74% so với 67%).
3. Huấn luyện nhanh hơn (0,35 s so với 0,51 s).
4. Giữ cấu hình mặc định vì tinh chỉnh không cải thiện (mục 10.4), và không dùng `class_weight` vì nhãn đã gần cân bằng và mức cải thiện nằm trong sai số.

Giới hạn của quyết định: ba ứng viên và biến thể đều được so sánh trên chính các khối test, nên không có tập kiểm tra giữ lại hoàn toàn. Việc chọn giữa Random Forest và XGBoost chỉ có ảnh hưởng nhỏ (chênh +0,002), nên độ lạc quan do chọn là không đáng kể so với độ dao động; nếu chọn XGBoost thì kết luận chung không đổi. Báo cáo nên nêu rõ điều này và trình bày cả ba mô hình ở mục 10.2.

### 11.3 Đánh giá tổng quát hóa của mô hình cuối

Random Forest, theo từng mã. KTC 95% trong ngoặc vuông.

| Mã | Fold | Accuracy | F1 macro | ROC-AUC | F1 so với ngẫu nhiên | Accuracy so với majority | ROC-AUC so với 0,5 |
|---|---:|---:|---:|---:|---|---|---|
| TCB | 20 | 0,363 | 0,339 | 0,519 | +0,013 [-0,011; +0,036] | +0,017 [-0,007; +0,043] | +0,019 [-0,007; +0,042] |
| CTG | 27 | 0,389 | 0,347 | 0,555 | +0,023 [+0,006; +0,041] | +0,042 [+0,019; +0,065] | +0,055 [+0,034; +0,075] |
| VNM | 27 | 0,407 | 0,357 | 0,540 | +0,034 [+0,009; +0,058] | +0,042 [-0,001; +0,088] | +0,040 [+0,022; +0,058] |
| ACB | 27 | 0,377 | 0,338 | 0,534 | +0,016 [-0,009; +0,040] | +0,043 [+0,008; +0,081] | +0,034 [+0,007; +0,060] |
| Gộp | 101 | 0,385 | 0,346 | 0,538 | +0,022 [+0,011; +0,033] | +0,037 [+0,020; +0,055] | +0,038 [+0,026; +0,049] |

Theo năm của khối test (số fold trong ngoặc): F1 macro của mô hình hơn ngẫu nhiên ở cả tám năm, nhưng mức hơn nhỏ và giảm dần sau 2020.

| Năm | Fold | F1 macro | Ngẫu nhiên | Hơn |
|---|---:|---:|---:|---:|
| 2019 | 3 | 0,378 | 0,329 | +0,050 |
| 2020 | 12 | 0,373 | 0,324 | +0,049 |
| 2021 | 14 | 0,340 | 0,326 | +0,014 |
| 2022 | 16 | 0,338 | 0,324 | +0,015 |
| 2023 | 15 | 0,344 | 0,324 | +0,020 |
| 2024 | 14 | 0,342 | 0,322 | +0,020 |
| 2025 | 16 | 0,345 | 0,323 | +0,022 |
| 2026 | 11 | 0,336 | 0,324 | +0,012 |

Nhận xét:
1. **Có tín hiệu nhưng rất yếu.** Gộp bốn mã, F1 macro hơn ngẫu nhiên 0,022 và ROC-AUC hơn 0,5 là 0,038, cả hai có khoảng tin cậy không chứa 0. Accuracy 0,385 so với majority 0,348. Về mặt thực tế, mô hình đoán đúng hướng ngày kế tiếp chỉ hơn đoán mò vài điểm phần trăm.
2. **Không đồng đều giữa các mã.** CTG và VNM có khoảng tin cậy F1 tách khỏi 0; TCB và ACB thì chứa 0 (TCB chỉ có 20 fold và dữ liệu ngắn hơn). Hai mã có tín hiệu rõ nhất là hai mã có F1 và ROC-AUC cao nhất, nhưng chưa có kiểm định để khẳng định đây không phải ngẫu nhiên.
3. **Mức hơn ngẫu nhiên không tăng theo thời gian.** Phần lớn mức hơn đến từ 2019 và 2020 (+0,05, ít fold); từ 2021 trở đi chỉ +0,01 đến +0,02. Phù hợp với mục 9.4: thêm dữ liệu train không giúp, và tín hiệu có thể yếu dần hoặc dữ liệu cũ kém liên quan.
4. **Quá khớp train vẫn nặng.** F1 train 1,000 so với 0,346 trên test. Mô hình thuộc lòng tập train; mọi giá trị dự đoán trên test là khái quát hóa từ tín hiệu yếu.
5. **Giá trị thực tế chưa rõ.** Backtest của Random Forest cấu hình này (từ `results/1D/tuning/backtest.csv`, chưa phân tích kỹ, thuộc B10): ACB +17,8%, CTG -0,8%, TCB -45,4%, VNM -2,0%; mua và nắm giữ lần lượt +252,6%, +226,9%, +30,6%, -18,1%. Tín hiệu thống kê nhỏ không đủ bù chi phí giao dịch ở tần suất này.

## 12. Mở rộng số mã: chọn mã theo chất lượng dữ liệu (thử nghiệm sau B9)

Mục đích: kiểm tra xem kết quả yếu có do bốn mã ban đầu hay không. Chưa thay đổi phạm vi chính của đề tài (bốn mã, mục 2); đây là thí nghiệm bổ sung.

### 12.1 Thu thập và chọn mã

- `scripts/crawl.py` nhận thêm `--symbols`, `--resolutions`, `--output-root`. Đã crawl khung 1D của 35 mã thanh khoản cao (ngày 2026-11-06, dữ liệu đến 2026-11-05): VCB, BID, MBB, VPB, HDB, STB, TPB, VIB, SHB, SSI, VND, HCM, HPG, HSG, FPT, MWG, PNJ, REE, GAS, PLX, POW, SAB, MSN, VIC, VHM, VRE, GVR, DGC, DPM, DCM, PVD, KDH, VJC, CTD, NVL. Dữ liệu thô nằm trong `data/raw/1D/`.
- `scripts/screen_symbols.py` chấm chất lượng dữ liệu thô, kết quả ở `data/screening/symbol_quality.csv`. Tiêu chí chỉ dựa trên chất lượng dữ liệu, **không dựa trên kết quả mô hình**: đủ ít nhất 2.400 phiên; thiếu không quá 3 phiên so với lịch giao dịch chung; không có ngày khối lượng bằng 0; không quá 3 nến sai OHLC (bước làm sạch sửa được, giống bốn mã gốc); không có ngày biến động trên 7,5%; tỷ lệ ngày giá đóng cửa không đổi dưới 10%. Trong nhóm đạt, xếp theo giá trị giao dịch trung vị 500 phiên gần nhất.
- Tiêu chí `invalid_ohlc` ban đầu là bằng 0, sau đó nới thành tối đa 3 dòng vì bước làm sạch xử lý được các dòng này. Việc nới được quyết định trước khi huấn luyện bất kỳ mô hình nào.
- 15 mã đạt: HPG, FPT, SSI, MWG, STB, MSN, MBB, VCB, VJC, BID, DPM, PVD, GAS, PNJ, REE. **HPG và FPT** có giá trị giao dịch trung vị cao nhất (550 và 545 tỷ đồng mỗi phiên), đủ 2.493 phiên từ 2016-11-09, không thiếu phiên nào. Bị loại có SHB (19% ngày giá không đổi, 49 ngày vượt biên độ), VIC (12% ngày giá không đổi), VND, GVR, VIB (nhiều ngày vượt biên độ hoặc thiếu phiên), và các mã niêm yết sau 2017 (VPB, HDB, TPB, VHM, VRE, POW...) vì không đủ lịch sử.
- Dữ liệu làm sạch và tiền xử lý của các mã mới nằm trong `data/extra/cleaned/` và `data/extra/processed/` (không đụng đến `data/cleaned`, `data/processed` của bốn mã gốc). Kết quả huấn luyện ở `results/extra/1D/`, dùng đúng `train_models.py`, cùng 25 đặc trưng, nhãn ba lớp θ = 0,5%, walk-forward 750/63/gap 1.

Lệnh đã chạy:

```bash
.venv/bin/python scripts/crawl.py --resolutions 1D --symbols VCB BID MBB ...
.venv/bin/python scripts/screen_symbols.py
.venv/bin/python scripts/clean_data.py --input-root data/raw --output-root data/extra/cleaned --resolutions 1D --symbols HPG FPT ...
.venv/bin/python scripts/preprocess_data.py --input-root data/extra/cleaned --output-root data/extra/processed --resolutions 1D --symbols HPG FPT ...
.venv/bin/python scripts/train_models.py --symbols HPG FPT ... --processed-root data/extra/processed --output-root results/extra
```

### 12.2 Kết quả theo mã

Giá trị trung bình qua 27 fold (VJC 25 fold), cấu hình mặc định như mục 3.

| Mã | F1 ngẫu nhiên | F1 Logistic | F1 Random Forest | F1 XGBoost | AUC Logistic | AUC Random Forest | AUC XGBoost |
|---|---:|---:|---:|---:|---:|---:|---:|
| **HPG** | 0,327 | 0,323 | 0,327 | 0,351 | 0,521 | 0,536 | 0,530 |
| **FPT** | 0,323 | 0,307 | 0,324 | 0,335 | 0,535 | 0,531 | 0,516 |
| BID | 0,327 | 0,319 | 0,319 | 0,327 | 0,532 | 0,517 | 0,508 |
| DPM | 0,325 | 0,335 | 0,325 | 0,354 | 0,538 | 0,529 | 0,532 |
| GAS | 0,319 | 0,320 | 0,320 | 0,320 | 0,533 | 0,518 | 0,509 |
| MBB | 0,326 | 0,334 | 0,345 | 0,335 | 0,534 | 0,538 | 0,521 |
| MSN | 0,324 | 0,335 | 0,329 | 0,342 | 0,520 | 0,520 | 0,527 |
| MWG | 0,328 | 0,331 | 0,326 | 0,339 | 0,542 | 0,533 | 0,521 |
| PNJ | 0,328 | 0,335 | 0,346 | 0,335 | 0,554 | 0,552 | 0,517 |
| PVD | 0,325 | 0,319 | 0,318 | 0,331 | 0,512 | 0,534 | 0,533 |
| REE | 0,327 | 0,334 | 0,337 | 0,344 | 0,534 | 0,531 | 0,523 |
| SSI | 0,326 | 0,320 | 0,308 | 0,342 | 0,540 | 0,529 | 0,527 |
| STB | 0,324 | 0,308 | 0,306 | 0,320 | 0,527 | 0,511 | 0,507 |
| VCB | 0,326 | 0,329 | 0,342 | 0,350 | 0,550 | 0,536 | 0,532 |
| VJC | 0,324 | 0,307 | 0,348 | 0,346 | 0,538 | 0,544 | 0,524 |
| Trung bình 15 mã | 0,325 | 0,324 | 0,328 | 0,338 | 0,534 | 0,531 | 0,522 |

Hai mã được chọn (HPG, FPT) không nổi bật so với nhóm còn lại. Không chọn mã theo điểm mô hình, vì như vậy là chọn trên tập kiểm tra.

### 12.3 So sánh với bốn mã gốc

Gộp 403 fold của 15 mã mới, KTC 95% bootstrap theo cách ở mục 11 (lấy mẫu lại fold trong từng mã):

| Mô hình | F1 hơn ngẫu nhiên (15 mã mới) | F1 hơn ngẫu nhiên (4 mã gốc) | ROC-AUC hơn 0,5 (15 mã mới) | ROC-AUC hơn 0,5 (4 mã gốc) |
|---|---|---|---|---|
| Logistic | -0,001 [-0,007; +0,004] | -0,002 [-0,013; +0,009] | +0,034 [+0,029; +0,039] | +0,030 [+0,019; +0,041] |
| Random Forest | +0,003 [-0,003; +0,008] | +0,022 [+0,010; +0,034] | +0,031 [+0,025; +0,036] | +0,038 [+0,026; +0,049] |
| XGBoost | +0,013 [+0,007; +0,019] | +0,024 [+0,013; +0,035] | +0,022 [+0,017; +0,027] | +0,028 [+0,017; +0,039] |

Số mã có F1 trung bình hơn ngẫu nhiên: Logistic 8/15, Random Forest 10/15, XGBoost 14/15. AUC phân biệt tăng với giảm (trung bình ba mô hình) là 0,524 và AUC lớp "ngang" là 0,566, cùng hình dạng như bốn mã gốc (0,52–0,53 và 0,58–0,62).

### 12.4 Nhận xét

1. **Thêm mã không giúp.** Trên 15 mã mới, F1 macro hầu như bằng ngẫu nhiên (Logistic -0,001, Random Forest +0,003, XGBoost +0,013). Không có mã nào có tín hiệu rõ rệt; HPG và FPT cũng vậy.
2. **Tín hiệu ROC-AUC có thật nhưng rất nhỏ và lặp lại.** AUC cao hơn 0,5 khoảng 0,02 đến 0,03, khoảng tin cậy không chứa 0 ở cả hai nhóm mã. Tức mô hình xếp hạng xác suất đúng hơn ngẫu nhiên một chút, nhưng mức này không đủ để chuyển thành F1 macro khi chọn nhãn bằng argmax.
3. **Kết quả của Random Forest ở bốn mã gốc không lặp lại.** F1 hơn ngẫu nhiên +0,022 ở bốn mã gốc nhưng chỉ +0,003 ở 15 mã mới. Điều này gợi ý mức hơn ở mục 11 có phần do may mắn của bốn mã đó (hoặc của giai đoạn đó). Báo cáo không nên diễn giải con số +0,022 như hiệu năng kỳ vọng.
4. **Backtest của hai mã chọn:** HPG và FPT, cả ba mô hình đều thua mua và nắm giữ (+185,7% và +176,3%). Ví dụ Random Forest -11,0% ở HPG và -21,4% ở FPT, với 283 và 212 giao dịch. Chỉ Logistic ở FPT dương (+43,3%, 98 giao dịch).
5. **Kết luận bổ sung cho mục 9 và 10:** hướng giá ngày kế tiếp không dự đoán được từ dữ liệu giá-khối lượng, nhất quán trên 19 mã khác nhau. Nguyên nhân nằm ở dữ liệu và bài toán, không phải ở lựa chọn mô hình hay mã.

## 13. Khung 1H cho 15 mã mới (thí nghiệm sau B9)

Mục đích: xem khung 1H, nơi bốn mã gốc cho F1 cao hơn hẳn (mục 12 trước đó chỉ là khung ngày), có lặp lại trên các mã mới và tín hiệu đó đến từ đâu. Đây là thí nghiệm bổ sung, không thuộc phạm vi chính (khung 1D, bốn mã).

### 13.1 Dữ liệu và cách chạy

- Crawl khung 1H cho 15 mã đạt chất lượng ở mục 12 (HPG, FPT, SSI, MWG, STB, MSN, MBB, VCB, VJC, BID, DPM, PVD, GAS, PNJ, REE), ngày 2026-11-06. API chỉ trả khoảng 2 năm (2024-11-06 đến 2026-11-06), khoảng 2.480 nến mỗi mã.
- Sau làm sạch và tiền xử lý còn khoảng 2.445 mẫu mỗi mã, 30 đặc trưng (25 đặc trưng giá, khối lượng và 5 đặc trưng thời gian), ngưỡng nhãn θ = 0,2%, walk-forward train đầu 1.000 nến, test 125 nến, gap 1: **11 fold mỗi mã**, mỗi khối test khoảng 25 phiên.
- Dữ liệu ở `data/extra/{cleaned,processed}/1H/`, kết quả `train_models.py` ở `results/extra/1H/`, kết quả `hourly_ablation.py` ở `results/extra/1H/ablation_*.csv` và `hourly_profile.csv`.

```bash
.venv/bin/python scripts/crawl.py --resolutions 1H --symbols HPG FPT ...
.venv/bin/python scripts/clean_data.py --input-root data/raw --output-root data/extra/cleaned --resolutions 1H --symbols HPG FPT ...
.venv/bin/python scripts/preprocess_data.py --input-root data/extra/cleaned --output-root data/extra/processed --resolutions 1H --symbols HPG FPT ...
.venv/bin/python scripts/train_models.py --resolution 1H --symbols HPG FPT ... --processed-root data/extra/processed --output-root results/extra
.venv/bin/python scripts/hourly_ablation.py
```

### 13.2 Kết quả theo mã

Trung bình qua 11 fold, cấu hình mặc định.

| Mã | F1 ngẫu nhiên | F1 Logistic | F1 Random Forest | F1 XGBoost | AUC Logistic | AUC Random Forest | AUC XGBoost |
|---|---:|---:|---:|---:|---:|---:|---:|
| **HPG** | 0,329 | 0,424 | 0,419 | 0,399 | 0,616 | 0,587 | 0,567 |
| **FPT** | 0,328 | 0,373 | 0,406 | 0,378 | 0,597 | 0,594 | 0,568 |
| BID | 0,327 | 0,395 | 0,403 | 0,381 | 0,591 | 0,585 | 0,573 |
| DPM | 0,325 | 0,429 | 0,393 | 0,386 | 0,610 | 0,592 | 0,570 |
| GAS | 0,320 | 0,403 | 0,388 | 0,385 | 0,597 | 0,586 | 0,580 |
| MBB | 0,329 | 0,410 | 0,430 | 0,402 | 0,595 | 0,597 | 0,578 |
| MSN | 0,330 | 0,437 | 0,396 | 0,373 | 0,624 | 0,594 | 0,559 |
| MWG | 0,330 | 0,456 | 0,425 | 0,414 | 0,630 | 0,607 | 0,589 |
| PNJ | 0,328 | 0,456 | 0,441 | 0,443 | 0,637 | 0,633 | 0,627 |
| PVD | 0,331 | 0,366 | 0,358 | 0,390 | 0,587 | 0,570 | 0,572 |
| REE | 0,328 | 0,381 | 0,386 | 0,386 | 0,615 | 0,591 | 0,575 |
| SSI | 0,326 | 0,417 | 0,394 | 0,391 | 0,593 | 0,592 | 0,570 |
| STB | 0,327 | 0,420 | 0,412 | 0,389 | 0,609 | 0,596 | 0,574 |
| VCB | 0,330 | 0,402 | 0,392 | 0,388 | 0,616 | 0,589 | 0,576 |
| VJC | 0,327 | 0,465 | 0,408 | 0,410 | 0,635 | 0,620 | 0,608 |
| Trung bình 15 mã | 0,328 | 0,416 | 0,403 | 0,394 | 0,610 | 0,596 | 0,579 |

Cả 15 mã đều có F1 của mô hình tốt nhất cao hơn ngẫu nhiên từ khoảng 0,03 đến 0,14, và kết quả lặp lại kết quả của bốn mã gốc (F1 Logistic 0,40, AUC 0,60).

### 13.3 Tín hiệu đến từ đâu: baseline chỉ dùng giờ trong ngày

Baseline `hour_prior` không dùng chỉ báo nào: xác suất ba lớp bằng tần suất lớp theo giờ của nến trong tập train (`CategoricalNB` của scikit-learn với một đặc trưng là giờ). Gộp 15 mã, 165 fold:

| Biến thể | F1 macro | ROC-AUC | AUC tăng so với giảm | AUC lớp "ngang" |
|---|---:|---:|---:|---:|
| ngẫu nhiên (theo tỷ lệ lớp train) | 0,328 | – | – | – |
| `hour_prior` (chỉ giờ, không mô hình) | 0,393 | 0,601 | 0,586 | 0,609 |
| Logistic, chỉ 25 đặc trưng giá | 0,352 | 0,558 | 0,553 | 0,579 |
| Random Forest, chỉ 25 đặc trưng giá | 0,366 | 0,558 | 0,554 | 0,577 |
| Logistic, chỉ 5 đặc trưng thời gian | 0,399 | 0,595 | 0,579 | 0,608 |
| Random Forest, chỉ 5 đặc trưng thời gian | 0,401 | 0,596 | 0,583 | 0,608 |
| Logistic, 25 giá + 5 thời gian | 0,416 | 0,610 | 0,591 | 0,637 |
| Random Forest, 25 giá + 5 thời gian | 0,404 | 0,596 | 0,589 | 0,616 |

Chênh lệch theo cặp (cùng fold), KTC 95% bootstrap (lấy mẫu lại fold trong từng mã, chưa tính tương quan giữa các mã nên hẹp hơn thực tế):

| So sánh | F1 macro | ROC-AUC |
|---|---|---|
| Logistic đầy đủ so với `hour_prior` | +0,023 [+0,015; +0,030] | +0,009 [+0,004; +0,014] |
| Random Forest đầy đủ so với `hour_prior` | +0,011 [+0,002; +0,020] | -0,005 [-0,012; +0,001] |
| Logistic đầy đủ so với Logistic chỉ thời gian | +0,016 [+0,009; +0,024] | +0,015 [+0,010; +0,020] |
| Logistic chỉ đặc trưng giá so với `hour_prior` | -0,041 [-0,052; -0,031] | -0,043 [-0,050; -0,035] |
| Random Forest chỉ đặc trưng giá so với `hour_prior` | -0,027 [-0,037; -0,017] | -0,044 [-0,052; -0,034] |

### 13.4 Hiệu ứng theo giờ

Gộp 15 mã (khoảng 7.300 nến mỗi giờ). Nhãn của nến giờ `h` là biến động đến nến kế tiếp. Theo chuỗi nến 1H trong dữ liệu, đó là: 09:00 và 10:00 sang nến liền sau trong phiên, 11:00 sang 13:00 qua giờ nghỉ trưa, 13:00 sang 14:00 trong phiên, 14:00 sang 09:00 hôm sau (qua đêm). Đây là cách tôi đọc cấu trúc nến, chưa đối chiếu với tài liệu của API.

| Giờ nến | Lợi suất kế tiếp trung bình | Độ lệch chuẩn | Tỷ lệ "ngang" | Tỷ lệ tăng trong các nến có hướng |
|---|---:|---:|---:|---:|
| 09:00 | -0,082% | 0,77% | 31,6% | 36,9% |
| 10:00 | -0,058% | 0,47% | 49,7% | 38,4% |
| 11:00 | +0,060% | 0,88% | 31,7% | 47,7% |
| 13:00 | -0,005% | 0,96% | 28,6% | 46,8% |
| 14:00 | +0,092% | 1,41% | 21,5% | 53,1% |

### 13.5 Backtest cho HPG và FPT (khung 1H)

Cùng quy tắc long-only và chi phí như mục 4 (phí 0,15% mỗi chiều, thuế bán 0,1%). Các khối test ghép liền, khoảng 275 phiên.

| Mã | Mua và nắm giữ | Logistic | Random Forest | XGBoost | Ngẫu nhiên |
|---|---:|---:|---:|---:|---:|
| HPG | -19,3% | -52,5% (223 lệnh mua) | -52,4% (208) | -57,3% (210) | -62,5% (224) |
| FPT | -36,4% | -20,9% (78) | -33,4% (132) | -44,3% (188) | -65,3% (211) |

Cột Sharpe của `results/extra/1H/backtest.csv` ban đầu nhân với căn của 252 trong khi đơn vị là một nến giờ (khoảng 5 nến mỗi phiên), nên sai thang. Đã sửa trong `train_models.py` (số kỳ mỗi năm = 252 nhân số nến mỗi phiên, xem mục 18.1) và chạy lại: tổng lợi suất và số lệnh không đổi, chỉ cột Sharpe đổi (nhân khoảng căn 5, cùng dấu).

### 13.6 Nhận xét

1. **F1 cao hơn ở khung 1H phần lớn không phải do chỉ báo.** Baseline chỉ dùng giờ trong ngày (không có chỉ báo, không có mô hình học máy) đã đạt F1 0,393 và AUC 0,601, so với ngẫu nhiên 0,328. Các mô hình chỉ dùng 25 đặc trưng giá có F1 0,35 đến 0,37, **thấp hơn** baseline giờ 0,03 đến 0,04 và chỉ hơn ngẫu nhiên 0,02 đến 0,04; AUC 0,558 chỉ cao hơn nhẹ AUC khung ngày (mục 12, 0,52 đến 0,53).
2. **Nguồn gốc là cấu trúc nến, không phải hướng giá.** Khoảng cách giữa các nến không đồng nhất (trong phiên, nghỉ trưa, qua đêm) nên độ lớn biến động khác nhau theo giờ: tỷ lệ lớp "ngang" là 50% ở nến 10:00 nhưng 21% ở nến 14:00. Một mô hình biết giờ đã biết trước phần lớn phân bố ba lớp.
3. **Chỉ báo có đóng góp nhỏ nhưng ổn định ở Logistic.** Logistic đầy đủ hơn `hour_prior` 0,023 F1 và 0,009 AUC, với khoảng tin cậy không chứa 0 và hơn ở 12 trong 15 mã; Random Forest chỉ hơn 0,011 F1 và AUC không hơn. Khoảng tin cậy thực tế rộng hơn các con số này vì chưa tính tương quan giữa các mã.
4. **Hiệu ứng hướng theo giờ có thật nhưng quá nhỏ để giao dịch.** Lợi suất kế tiếp trung bình theo giờ chỉ từ -0,08% đến +0,09%, trong khi một vòng mua bán tốn 0,40%. Các giá trị này nhỏ hơn 1/4 chi phí, kể cả nến 14:00 (qua đêm) có tỷ lệ tăng cao nhất.
5. **Backtest xác nhận điều này.** Cả ba mô hình lỗ ở HPG (-52% đến -57%, nặng hơn mua và giữ -19%) và lỗ ở FPT. Chỉ Logistic ở FPT (-20,9%) tốt hơn mua và nắm giữ (-36,4%), nhưng vẫn lỗ.
6. **Hạn chế.** Chỉ có khoảng hai năm dữ liệu (11 fold mỗi mã, mỗi khối test khoảng 25 phiên), nên thiếu sức mạnh thống kê và chưa thấy được các chế độ thị trường khác. Ngưỡng nhãn 0,2% cố định cho mọi mã và mọi giờ.
7. **Kết luận.** Khung 1H cho điểm cao hơn khung ngày về mặt F1 macro, nhưng không cho dự đoán xu hướng giá tốt hơn: đóng góp thật sự của chỉ báo vẫn gần mức ROC-AUC 0,53 đến 0,56. Nếu đưa kết quả 1H vào báo cáo, phải nêu baseline `hour_prior` cạnh bảng kết quả, nếu không F1 0,40 sẽ bị hiểu nhầm là khả năng dự đoán.

## 14. Thử các hướng cải thiện: mô hình gộp, nhãn tương đối, biến động, ensemble, VN-Index (sau B9)

Mục đích: tìm hướng tốt nhất sau khi các mục 9 đến 13 cho thấy dự đoán theo từng mã gần như không hơn ngẫu nhiên. Ban đầu đây là thí nghiệm bổ sung bên cạnh phạm vi chính (bốn mã, mô hình riêng từng mã, mục 2); sau khi so sánh, hướng gộp mã được nhóm chọn làm mô hình chính (mục 15.3) và chạy riêng từng mã còn là baseline.

Thuật ngữ: "gộp mã" (pooled) là huấn luyện một mô hình trên dữ liệu nhiều mã; "ensemble" là trung bình xác suất của nhiều mô hình. Hai khái niệm độc lập nhau.

### 14.1 Thiết lập

- **Panel gộp 19 mã** (4 mã gốc và 15 mã mục 12), khung 1D, 45.554 dòng từ 2017-02-22 đến 2026-11-04, dựng bằng `scripts/panel_data.py`. Mọi đặc trưng tại ngày `t` chỉ dùng dữ liệu đến hết `t`; `--verify` dựng lại panel với dữ liệu bị cắt ở 6 mốc ngẫu nhiên và các đặc trưng trước mốc cắt giống hệt bản đầy đủ.
- **Nhóm đặc trưng:** `base` (25, như mục 4 của `data-preprocess.md`), `full` (53: thêm 13 đặc trưng riêng từng mã như lợi suất 10/20/60 phiên, biến động dài hạn, khoảng cách tới đỉnh/đáy 60 phiên; 10 đặc trưng thị trường tính từ chính 19 mã như lợi suất trung bình, độ phân tán, tỷ lệ mã tăng, lợi suất tương đối; 5 hạng phân vị chéo mã trong ngày), `full_idx` (61: thêm 8 đặc trưng VN-Index). VN-Index lấy bằng `crawl.py --kind index` (khung 1D từ 2016-11; API không có dòng tiền khối ngoại, chỉ có OHLCV).
- **Nhãn:** `abs` là nhãn tuyệt đối ba lớp θ = 0,5% như trước; `rel` chia ba theo hạng lợi suất ngày kế tiếp trong từng ngày (nhóm trên, giữa, dưới), nên loại thành phần chung của thị trường. Với 19 mã, nhóm "tăng" chiếm 36%, "giảm" 32%, "ngang" 32% do làm tròn. `rel3`, `rel5`, `rel10`, `rel20` là cùng cách chia theo lợi suất 3, 5, 10, 20 phiên.
- **Walk-forward theo ngày:** train đầu 750 ngày, mỗi khối test 63 ngày, khoảng cách bằng chân trời (1 ngày với nhãn ngày kế tiếp). **Dev** là các fold có khối test bắt đầu trước 2025-01-01 (20 fold, 23.746 dòng test); **xác nhận** là các fold từ 2025-01-01 (6 fold, 7.182 dòng test). Việc so sánh và chọn hướng chỉ dựa trên dev. Tôi có in bảng xác nhận cho mọi cấu hình để kiểm tra, nên kết quả xác nhận không còn là phép thử "một lần" nghiêm ngặt.
- **Mô hình** (siêu tham số cố định từ đầu, không tinh chỉnh): Logistic (`C = 0,1`), Random Forest (300 cây, `min_samples_leaf = 50`), XGBoost chạy trên GPU (`device="cuda"`, 300 cây, `max_depth = 4`, `learning_rate = 0,05`, `subsample = colsample = 0,8`, `min_child_weight = 20`), `ensemble3` là trung bình xác suất của ba mô hình, MLP trên GPU (PyTorch, tùy chọn, 3 seed) chỉ chạy ở các cấu hình pooled và cần cài thêm `torch`. Hai chế độ: `pooled` (một mô hình cho 19 mã) và `per_symbol` (mỗi mã một mô hình, cùng siêu tham số và cùng fold, làm đối chứng).
- **Chỉ số:** F1 macro (so với dự đoán ngẫu nhiên theo tỷ lệ lớp train), AUC phân biệt tăng với giảm trên các mẫu có hướng (điểm = `p_up - p_down`), IC xếp hạng (tương quan hạng Spearman mỗi ngày giữa điểm và lợi suất kế tiếp, lấy trung bình; t-stat theo ngày chưa hiệu chỉnh tự tương quan), danh mục long-only mua nhóm 20% điểm cao nhất (tối thiểu 3 mã), tỷ trọng bằng nhau, tái cân bằng mỗi `h` ngày, phí mua 0,15%, phí bán 0,15% cộng thuế 0,1%, benchmark là trung bình đều 19 mã. **Alpha** là hệ số chặn (quy năm) khi hồi quy lợi suất ngày của danh mục lên lợi suất benchmark, khoảng tin cậy 95% bằng bootstrap theo khối 10 ngày. Danh mục "dính" giữ một mã chừng nào hạng của nó còn trong 2 lần số vị thế mục tiêu, để giảm vòng quay (hệ số 2 đặt trước, không tinh chỉnh).
- Sau khi tổng hợp, các file trung gian `results/research/*/oof.csv.gz` (điểm dự đoán, khoảng 130 MB) và `data/extra/panel_1D.csv.gz` (20 MB) đã bị xóa để tiết kiệm chỗ. Sinh lại panel bằng `scripts/panel_data.py`, sinh lại điểm dự đoán bằng `panel_experiments.py` cho từng cấu hình (cần có `oof.csv.gz` để chạy `summarize_research.py` và `--reevaluate`). `metrics.csv`, `summary.csv`, `original_symbols_comparison.csv`, `execution_timing.csv`, `identity_baseline.csv`, `single_feature_ic*.csv`, `demeaned_score_ic.csv` được giữ lại.
- Chạy mỗi cấu hình pooled mất khoảng 2 phút nhờ GPU cho XGBoost và 24 nhân CPU cho Random Forest. Lệnh: `scripts/panel_experiments.py --name pooled_rel_full --mode pooled --label rel --features full` và `scripts/summarize_research.py`.

### 14.2 Kiểm tra rò rỉ và hiệu ứng nhận diện mã

Điểm IC của mô hình gộp (khoảng 0,10) cao hơn nhiều so với mọi thứ ở các mục trước, nên đã kiểm tra các nghi vấn trước khi dùng:

- **Mô hình học lại "mã nào từng tăng nhiều thì tiếp tục tăng"?** Dự đoán chỉ dựa trên lợi suất trung bình trong tập train của từng mã có IC 0,007 (t = 1,0) và dựa trên tỷ lệ nhãn hướng của từng mã có IC 0,011 (t = 1,5): không có ý nghĩa. Bỏ trung bình điểm quá khứ của chính từng mã khỏi điểm mô hình cũng không đổi IC (0,105 xuống 0,104 ở `pooled_abs_base`). Cả hai phép tính nằm trong `summarize_research.py` (`identity_baseline.csv`, `demeaned_score_ic.csv`).
- **Quy tắc đơn giản không cần huấn luyện cũng có tín hiệu:** đặc trưng `ret_3` có IC chéo mã -0,050 (t = -8,2) trên toàn bộ panel, đúng dấu ở cả 10 năm (từ -0,013 đến -0,076). Chiều hướng là đảo chiều ngắn hạn: mã giảm trong 3 ngày qua có xu hướng tốt hơn ngày kế tiếp. Các đặc trưng liên quan đến hình dạng nến cũng cùng hướng (`lower_shadow` -0,041, `upper_shadow` +0,039). Phép tính nằm trong `summarize_research.py` (`single_feature_ic.csv`, `single_feature_ic_by_year.csv`).
- **Tín hiệu không chỉ nằm ở khoảng qua đêm.** IC với lợi suất vào ở giá mở cửa hôm sau rồi giữ đến giá mở cửa hôm sau nữa là 0,09 (so với 0,12 tính từ giá đóng cửa), xem mục 14.6.

### 14.3 So sánh các hướng trên dev (20 fold)

F1 macro so với dự đoán ngẫu nhiên (0,330 với nhãn `abs`, 0,333 với `rel`); AUC tăng so với giảm và IC xếp hạng của `ensemble3` và XGBoost. F1 của hai loại nhãn không so sánh trực tiếp với nhau vì ba lớp khác nghĩa.

| Cấu hình | F1 `ensemble3` | AUC tăng/giảm `ensemble3` · XGBoost | IC `ensemble3` (t) · XGBoost |
|---|---:|---|---|
| mỗi mã một mô hình, `abs`, `base` | 0,368 | 0,530 · 0,527 | 0,052 (7,4) · 0,047 |
| mỗi mã một mô hình, `abs`, `full` | 0,374 | 0,540 · 0,541 | 0,054 (7,5) · 0,052 |
| mỗi mã một mô hình, `rel`, `full` | 0,374 | 0,547 · 0,540 | 0,063 (9,0) · 0,059 |
| gộp, `abs`, `base` | 0,377 | 0,553 · 0,553 | 0,105 (13,3) · 0,105 |
| gộp, `abs`, `full` | 0,380 | 0,565 · 0,563 | 0,109 (13,6) · 0,109 |
| gộp, `abs`, `full_idx` (kèm VN-Index) | 0,379 | 0,558 · 0,549 | 0,105 (12,9) · 0,106 |
| gộp, `abs`, `full_idx`, hai giai đoạn | 0,375 | 0,554 · 0,544 | 0,104 (12,9) · 0,107 |
| gộp, `rel`, `base` | 0,361 | 0,569 · 0,569 | 0,119 (16,0) · 0,113 |
| **gộp, `rel`, `full`** | **0,383** | **0,574 · 0,574** | **0,122 (15,7) · 0,117** |
| gộp, `rel`, `full_idx` | 0,381 | 0,574 · 0,575 | 0,121 (15,7) · 0,122 |

Hai giai đoạn: mô hình riêng cho "ngang so với có hướng" (biến động) rồi mô hình tăng/giảm trên các mẫu có hướng, ghép thành ba xác suất.

Xác nhận (6 fold từ 2025), cùng định dạng:

| Cấu hình | F1 `ensemble3` (ngẫu nhiên) | AUC tăng/giảm `ensemble3` · XGBoost | IC `ensemble3` (t) · XGBoost |
|---|---|---|---|
| mỗi mã một mô hình, `abs`, `full` | 0,380 (0,330) | 0,558 · 0,550 | 0,060 (4,6) · 0,051 |
| mỗi mã một mô hình, `rel`, `full` | 0,385 (0,329) | 0,560 · 0,555 | 0,075 (5,7) · 0,069 |
| gộp, `abs`, `full` | 0,401 (0,332) | 0,592 · 0,576 | 0,102 (7,1) · 0,098 |
| gộp, `rel`, `full` | 0,376 (0,332) | 0,564 · 0,557 | 0,101 (7,2) · 0,089 |
| gộp, `rel`, `full_idx` | 0,379 (0,332) | 0,566 · 0,560 | 0,107 (7,5) · 0,095 |

### 14.4 Trên đúng bốn mã gốc

Cùng điểm dự đoán của các cấu hình ở mục 14.3 nhưng chỉ tính trên TCB, CTG, VNM, ACB (`original_symbols_comparison.csv`; IC tính trên ít mã mỗi ngày nên nhiễu hơn).

| Cấu hình | Mô hình | F1 dev (ngẫu nhiên) | AUC tăng/giảm dev | IC dev | AUC tăng/giảm xác nhận | IC xác nhận |
|---|---|---|---:|---:|---:|---:|
| mỗi mã, `abs`, `full` | `ensemble3` | 0,384 (0,329) | 0,550 | 0,043 | 0,559 | 0,043 |
| gộp, `abs`, `full` | `ensemble3` | 0,375 (0,328) | 0,565 | 0,094 | 0,592 | 0,063 |
| gộp, `rel`, `full` | `ensemble3` | 0,357 (0,333) | 0,564 | 0,102 | 0,564 | 0,051 |
| mỗi mã, `abs`, `full` | XGBoost | 0,378 (0,329) | 0,546 | 0,027 | 0,552 | 0,016 |
| gộp, `abs`, `full` | XGBoost | 0,372 (0,328) | 0,561 | 0,103 | 0,584 | 0,080 |
| gộp, `rel`, `full` | XGBoost | 0,357 (0,333) | 0,561 | 0,089 | 0,557 | 0,039 |

So với mô hình riêng từng mã, mô hình gộp tăng AUC tăng/giảm trên bốn mã gốc khoảng 0,01 đến 0,03 và tăng IC; F1 macro thì không tăng ở dev (một phần vì nhãn `rel` đổi nghĩa ba lớp).

### 14.5 Chân trời và danh mục (`pooled_rel_full`, `ensemble3`)

Alpha ròng quy năm, trong ngoặc là khoảng tin cậy 95%. "Dính" là danh mục giữ vị thế khi hạng còn trong 2 lần số vị thế. Vòng quay là tỷ trọng mua vào mỗi lần tái cân bằng.

| Chân trời | Giai đoạn | IC (t) | AUC tăng/giảm | Alpha gộp | Alpha ròng | Vòng quay | Alpha ròng, dính (vòng quay) |
|---|---|---|---:|---:|---|---:|---|
| 1 ngày | dev | 0,122 (15,7) | 0,574 | +52% | -7% [-18%; +4%] | 0,59 | +5% [-6%; +16%] (0,37) |
| 1 ngày | xác nhận | 0,101 (7,2) | 0,564 | +46% | -16% [-39%; +5%] | 0,61 | +5% [-16%; +26%] (0,37) |
| 3 ngày | dev | 0,089 (6,8) | 0,557 | +19% | -2% [-13%; +9%] | 0,64 | +6% [-4%; +15%] (0,41) |
| 3 ngày | xác nhận | 0,078 (3,0) | 0,555 | +13% | -10% [-30%; +14%] | 0,67 | -8% [-26%; +9%] (0,44) |
| 5 ngày | dev | 0,060 (3,5) | 0,545 | +22% | +9% [-1%; +21%] | 0,63 | +6% [-4%; +16%] (0,40) |
| 5 ngày | xác nhận | 0,052 (1,8) | 0,522 | +11% | -3% [-22%; +16%] | 0,73 | -6% [-22%; +8%] (0,49) |
| 10 ngày | dev | 0,059 (2,3) | 0,529 | +17% | +11% [-2%; +23%] | 0,65 | +12% [-1%; +25%] (0,44) |
| 10 ngày | xác nhận | -0,009 (-0,2) | 0,483 | -10% | -16% [-24%; -3%] | 0,68 | -6% [-14%; +10%] (0,48) |
| 20 ngày | dev | 0,047 (1,2) | 0,533 | +10% | +6% [-5%; +19%] | 0,81 | +5% [-9%; +17%] (0,57) |
| 20 ngày | xác nhận | 0,034 (0,6) | 0,534 | -9% | -13% [-18%; -6%] | 0,82 | -9% [-27%; -8%] (0,59) |

### 14.6 Thời điểm vào lệnh (nhãn 1 ngày, dev)

Vào lệnh theo giá đóng cửa ngày `t` là điều khó làm đúng trong thực tế. IC (điểm so với từng loại lợi suất kế tiếp) và alpha gộp của danh mục khi giả định các cách vào lệnh khác nhau (`execution_timing.csv`):

| Cấu hình, mô hình | IC giá đóng cửa | IC qua đêm | IC trong phiên | IC mở cửa đến mở cửa | Alpha gộp: đóng cửa | mở cửa | chỉ trong phiên |
|---|---:|---:|---:|---:|---:|---:|---:|
| gộp, `rel`, `full`, `ensemble3` | 0,122 | 0,104 | 0,073 | 0,094 | +52% | +45% | +33% |
| gộp, `rel`, `full`, XGBoost | 0,117 | 0,094 | 0,072 | 0,089 | +56% | +45% | +34% |
| gộp, `abs`, `full`, `ensemble3` | 0,109 | 0,088 | 0,064 | 0,087 | +46% | +42% | +28% |

### 14.7 Nhận xét

1. **Gộp mã là đòn bẩy lớn nhất.** IC từ 0,05 lên 0,105 và AUC tăng/giảm từ 0,53 lên 0,55 đến 0,565, trên cả 19 mã (mục 14.3) và trên riêng bốn mã gốc (mục 14.4). Khác với kết luận ở mục 12 ("hướng giá không dự đoán được"), kết luận đó đúng cho mô hình riêng từng mã, nhưng với mô hình gộp có thông tin chéo mã thì có tín hiệu xếp hạng thật sự, xác nhận được ở 2025 trở đi.
2. **Nhãn tương đối chỉ hơn ở dev, không được xác nhận.** Ở dev, `rel` cho IC 0,122 và AUC 0,574, so với 0,109 và 0,565 của `abs`. Ở giai đoạn xác nhận hai nhãn ngang nhau về IC (0,101 và 0,102) và `abs` còn có AUC cao hơn (0,592 so với 0,564), nên coi hai nhãn gần tương đương.
3. **Đặc trưng.** Nhóm `full` hơn `base` ở dev: AUC tăng/giảm +0,005 đến +0,012, F1 +0,003 đến +0,022, IC +0,003 đến +0,004. Thêm VN-Index không giúp (IC 0,121 so với 0,122; F1 0,381 so với 0,383): các đặc trưng thị trường tính từ 19 mã đã chứa thông tin đó.
4. **Mô hình.** Mô hình hai giai đoạn (IC 0,104 và 0,107 cho `ensemble3` và XGBoost, so với 0,105 và 0,106 khi huấn luyện trực tiếp cùng đặc trưng), MLP trên GPU (IC 0,086 đến 0,108, thấp hơn XGBoost cùng cấu hình) và ensemble (gần bằng XGBoost) đều không cải thiện rõ so với XGBoost đơn lẻ.
5. **Tín hiệu chủ yếu là đảo chiều ngắn hạn** (mục 14.2), suy giảm nhanh khi chân trời dài: IC giảm từ 0,122 (1 ngày) xuống 0,089, 0,060, 0,059, 0,047 (3, 5, 10, 20 ngày). Ở 10 và 20 ngày, giai đoạn xác nhận không còn tín hiệu (IC -0,009 và 0,034, AUC 0,48 và 0,53).
6. **Alpha ròng sau phí chưa khác 0 có ý nghĩa.** Với nhãn 1 ngày, alpha gộp rất lớn (khoảng +50% mỗi năm) nhưng vòng quay 0,6 mỗi ngày làm phí (0,4% mỗi vòng) ăn gần hết: alpha ròng -7% ở dev và -16% ở xác nhận, khoảng tin cậy chứa 0. Danh mục "dính" giảm vòng quay còn 0,37 và đưa alpha ròng lên +5% ở cả hai giai đoạn, vẫn có khoảng tin cậy rộng chứa 0. Chân trời 3 đến 5 ngày có alpha ròng dev từ -2% đến +9% nhưng không lặp lại ở 2025 trở đi. Giai đoạn xác nhận chỉ có 6 fold nên khoảng tin cậy rất rộng.
7. **Chi phí hòa vốn.** Với nhãn 1 ngày, alpha gộp +52% chia cho (252 × 0,59 vòng quay) cho mức phí hai chiều khoảng 0,35%, thấp hơn mức 0,40% giả định ở đây; danh mục "dính" cho khoảng 0,45%. Phí môi giới thực tế của người dùng quyết định kết luận.
8. **Hạn chế quan trọng.**
   - **Quy tắc T+2 không được mô hình hóa:** thị trường Việt Nam không cho bán lại cổ phiếu vừa mua trước ngày T+2, nên tái cân bằng hằng ngày (chân trời 1 ngày) không thực hiện được. Kết quả 1 ngày chỉ nói về chất lượng tín hiệu, không phải chiến lược giao dịch được.
   - **Giả định khớp tại giá đóng cửa.** Vào ở giá mở cửa hôm sau giữ khoảng 80% đến 90% alpha gộp (mục 14.6) nhưng sau phí còn âm hơn (alpha ròng -15% đến -25% ở dev).
   - **Thiên lệch chọn mã.** 19 mã được chọn theo thanh khoản năm 2026 và có đủ 10 năm lịch sử (mục 12), nên có thể có thiên lệch sống sót. Phép thử nhận diện mã (mục 14.2) cho thấy mô hình không chỉ học lại xu hướng từng mã, nhưng chưa kiểm tra được ảnh hưởng của việc chọn mã lên bản thân hiệu ứng đảo chiều.
   - **Không tính trượt giá, thanh khoản, ảnh hưởng thị trường.** Benchmark là trung bình đều 19 mã, tái cân bằng hằng ngày, không phí. IC t-stat theo ngày chưa hiệu chỉnh tự tương quan; khoảng tin cậy bootstrap của alpha đáng tin hơn.
9. **Hướng nên theo:** mô hình gộp nhiều mã với đặc trưng `full` không kèm VN-Index, XGBoost trên GPU hoặc `ensemble3`. Chọn theo dev thì nhãn tương đối (`rel`) nhỉnh hơn, nhưng xác nhận không ủng hộ, nên có thể giữ nhãn tuyệt đối (đúng định nghĩa ba lớp của đề) mà không mất tín hiệu đáng kể. Về chân trời, 1 ngày cho tín hiệu mạnh nhất nhưng không giao dịch được vì T+2; 5 ngày là chân trời ngắn nhất tuân thủ T+2 còn tín hiệu, nhưng alpha ròng chưa được xác nhận. Nếu báo cáo cần một kết luận về lợi nhuận, kết luận trung thực là: dự đoán xếp hạng có tín hiệu thật nhưng nhỏ, và chưa chứng minh được lợi nhuận ròng sau phí.

### 14.8 Mô hình tối ưu hiện tại, theo số đo của đề bài

Chọn theo dev (20 fold), báo cáo thêm xác nhận (6 fold từ 2025). Cấu hình: **mô hình gộp 19 mã, 53 đặc trưng (`full`), nhãn tuyệt đối ba lớp θ = 0,5%**, siêu tham số cố định như mục 14.1. Các ô là trung bình ± độ lệch chuẩn qua các fold (`results/research/pooled_abs_full/metrics.csv`, đã thêm Accuracy vào `panel_experiments.py`).

| Mô hình | Accuracy dev | F1 macro dev | ROC-AUC (OvR macro) dev | Accuracy xác nhận | F1 macro xác nhận | ROC-AUC xác nhận |
|---|---|---|---|---|---|---|
| **ensemble3** (trung bình Logistic, Random Forest, XGBoost) | 0,417 ± 0,034 | 0,380 ± 0,030 | 0,580 ± 0,026 | 0,413 ± 0,020 | 0,401 ± 0,015 | 0,590 ± 0,009 |
| XGBoost (GPU) | 0,411 ± 0,037 | 0,378 ± 0,028 | 0,576 ± 0,029 | 0,404 ± 0,027 | 0,389 ± 0,019 | 0,583 ± 0,011 |
| Random Forest | 0,417 ± 0,030 | 0,376 ± 0,030 | 0,577 ± 0,024 | 0,407 ± 0,018 | 0,393 ± 0,012 | 0,586 ± 0,007 |
| Logistic | 0,404 ± 0,030 | 0,371 ± 0,029 | 0,567 ± 0,024 | 0,410 ± 0,012 | 0,403 ± 0,009 | 0,586 ± 0,008 |
| Lớp đa số (baseline) | 0,364 | 0,177 | 0,500 | 0,343 | 0,170 | 0,500 |
| Dự đoán ngẫu nhiên (baseline) | – | 0,330 | – | – | 0,332 | – |

Phân biệt tăng với giảm (AUC trên các mẫu có hướng) và IC xếp hạng ngày: `ensemble3` 0,565 và 0,109 (dev), 0,592 và 0,102 (xác nhận); XGBoost 0,563 và 0,109 (dev), 0,576 và 0,098 (xác nhận).

Đối chứng cùng giao thức nhưng mỗi mã một mô hình (`results/research/persym_abs_full/metrics.csv`), dev: Accuracy 0,386 đến 0,399, F1 macro 0,368 đến 0,374, ROC-AUC 0,551 đến 0,566, AUC tăng/giảm 0,529 đến 0,541, IC 0,046 đến 0,054 (ba mô hình và `ensemble3`).

Nhận xét:
- **Mô hình tối ưu theo số đo là `ensemble3`**, nhưng chênh lệch giữa bốn mô hình nhỏ hơn nhiều so với độ lệch chuẩn giữa các fold (0,03): `ensemble3` hơn XGBoost 0,002 F1 và 0,004 AUC ở dev. Nếu cần một mô hình đơn để báo cáo, XGBoost và Random Forest gần như ngang nhau; XGBoost có IC cao hơn (0,109 so với 0,095).
- **So với baseline:** Accuracy cao hơn lớp đa số khoảng 0,05 (0,41 đến 0,42 so với 0,364), F1 macro cao hơn dự đoán ngẫu nhiên khoảng 0,05 (0,38 so với 0,330), ROC-AUC 0,58 so với 0,50.
- **So với mô hình riêng từng mã:** F1 macro chỉ hơn khoảng 0,006 (0,380 so với 0,374), nhưng ROC-AUC hơn khoảng 0,02 (0,580 so với 0,562), AUC tăng/giảm hơn 0,025 và IC gấp đôi. Lợi thế của việc gộp mã nằm ở chất lượng xếp hạng xác suất chứ không phải ở F1 macro.
- Ở giai đoạn xác nhận, thứ hạng bốn mô hình lẫn lộn (Logistic có F1 0,403 cao nhất, trên cả `ensemble3` 0,401), cho thấy sự chênh lệch giữa các mô hình không ổn định. Chỉ có kết luận "mô hình gộp tốt hơn baseline" là ổn định giữa dev và xác nhận.

## 15. So sánh hai mô hình ứng viên và quyết định chọn mô hình chính

So sánh `ensemble3` huấn luyện trên dữ liệu gộp 19 mã, khung ngày (mục 14.8) với Logistic giá + thời gian khung 1H (mục 13.3). Số liệu lấy từ các mục đó, không chạy lại. Hai bài toán khác nhau (ngưỡng nhãn 0,5% so với 0,2%, 19 mã và 10 năm so với 15 mã và 2 năm, 26 fold so với 165 fold gộp theo mã), nên so sánh chỉ mang tính tương đối.

### 15.1 Bảng so sánh

| | Logistic 1H (25 giá + 5 giờ) | `ensemble3`, huấn luyện gộp 19 mã, khung ngày |
|---|---|---|
| F1 macro | 0,416 | 0,380 (dev), 0,401 (xác nhận) |
| ROC-AUC (OvR macro) | 0,610 | 0,580 (dev), 0,590 (xác nhận) |
| AUC tăng so với giảm | 0,591 | 0,565 (dev), 0,592 (xác nhận) |
| AUC lớp "ngang" | 0,637 | 0,641 (dev), 0,613 (xác nhận) |
| Accuracy | không tính cho nhóm 15 mã | 0,417 ± 0,034 (dev), 0,413 ± 0,020 (xác nhận) |
| F1 macro dự đoán ngẫu nhiên | 0,328 | 0,330 (dev), 0,332 (xác nhận) |
| Baseline mạnh nhất | `hour_prior`: F1 0,393, AUC 0,601, AUC tăng/giảm 0,586 | không có (baseline ngẫu nhiên và lớp đa số) |
| Hơn baseline mạnh nhất | F1 +0,023 [+0,015; +0,030], AUC +0,009 [+0,004; +0,014] | F1 +0,050 so với ngẫu nhiên (dev), +0,069 (xác nhận) |
| Cùng mô hình chỉ dùng đặc trưng giá | F1 0,352, AUC 0,558, AUC tăng/giảm 0,553 | – |
| Backtest long-only sau phí | HPG -52,5%, FPT -20,9% (Logistic) | alpha gộp +46% đến +52% mỗi năm, alpha ròng -7% (dev), -16% (xác nhận), khoảng tin cậy chứa 0 |

### 15.2 Cách đọc

- **Điểm thô của 1H cao hơn, phần lớn do giờ trong ngày.** Baseline `hour_prior` (chỉ dùng tần suất lớp theo giờ, không chỉ báo, không mô hình) đã đạt F1 0,393 và AUC tăng/giảm 0,586. Logistic 1H chỉ hơn baseline đó 0,023 F1; chỉ riêng đặc trưng giá thì kém `ensemble3` khung ngày (F1 0,352 so với 0,380, AUC 0,558 so với 0,580).
- **Tín hiệu của `ensemble3` khung ngày không có nguồn cấu trúc kiểu giờ trong ngày.** AUC tăng/giảm 0,565 đến 0,592 so với baseline thật sự là 0,5, đến chủ yếu từ thông tin chéo mã (đảo chiều ngắn hạn, mục 14.2), và được xác nhận ở giai đoạn từ 2025.
- **"Ổn định" chỉ đúng một phần.** `ensemble3` ổn định so với baseline: F1 hơn ngẫu nhiên ở cả dev và xác nhận, AUC 0,58 đến 0,59, IC 0,109 và 0,102. Nhưng độ lệch chuẩn F1 giữa các fold vẫn khoảng 0,03 (không nhỏ hơn các mô hình đơn lẻ), và thứ hạng giữa bốn mô hình không ổn định: ở xác nhận Logistic có F1 0,403, cao hơn `ensemble3` 0,401.
- **"Tốt hơn" cũng chỉ đúng một phần.** `ensemble3` hơn XGBoost 0,002 F1 và 0,004 AUC ở dev, nhỏ hơn nhiều so với độ lệch chuẩn giữa các fold. Phần lợi thật sự đến từ việc gộp mã (AUC hơn mô hình riêng từng mã khoảng 0,02, IC gấp đôi), không phải từ việc ghép ba thuật toán.

### 15.3 Quyết định

**Mô hình chính của báo cáo: gộp 19 mã (pooled) + `ensemble3`, khung ngày, 53 đặc trưng, nhãn tuyệt đối ba lớp.** Hai phần này độc lập: gộp mã là cách chia dữ liệu huấn luyện (một mô hình chung cho 19 mã); `ensemble3` là cách kết hợp mô hình (trung bình xác suất Logistic, Random Forest, XGBoost). Đóng góp rất khác nhau: gộp mã là đòn bẩy chính (IC xếp hạng khoảng 0,05 lên 0,105; AUC khoảng 0,53 lên 0,565), còn `ensemble3` gần như không hơn XGBoost đơn về điểm số và được chọn chủ yếu vì ổn định giữa các fold. Lý do chọn:
1. Đề bài ghi nến 1 ngày; khung ngày là phạm vi chính, 1H là thí nghiệm mở rộng.
2. Tín hiệu được xác nhận ngoài mẫu và hơn baseline tầm thường một cách rõ ràng, trong khi điểm cao của 1H chủ yếu là hiệu ứng giờ.
3. Số liệu trên 10 năm và 26 fold chắc hơn 2 năm và 11 fold mỗi mã.

Phương án thay thế gần ngang: XGBoost đơn lẻ (cùng cấu hình, F1 0,378, AUC 0,576), nếu muốn một mô hình duy nhất cho gọn. Logistic 1H giữ làm thí nghiệm mở rộng, và khi đưa vào báo cáo phải nêu kèm baseline `hour_prior`.

Điều kiện đi kèm quyết định:
- Quyết định này khác "mỗi mã một mô hình riêng" ban đầu và kết luận Random Forest riêng từng mã ở mục 11. Nhóm đã đồng ý đổi; `AGENTS.md`, `data-preprocess.md` và `flow.md` đã sửa theo. Mục 11 giữ nguyên như kết quả của baseline từng mã.
- Không nêu `ensemble3` là "tốt hơn rõ" mô hình đơn lẻ, và không nêu lợi nhuận: alpha ròng sau phí chưa khác 0 có ý nghĩa, và quy tắc T+2 chưa được mô hình hóa (mục 14.7).

## 16. Backtest cuối của mô hình chính (B10)

Mô hình: gộp 19 mã + `ensemble3`, nhãn tuyệt đối, 53 đặc trưng (mục 15.3). Điểm của mỗi mã mỗi ngày là `p_up - p_down` ngoài mẫu từ walk-forward (26 fold). Lệnh: `python scripts/panel_data.py`, `python scripts/panel_experiments.py --name pooled_abs_full --mode pooled --label abs --features full`, rồi `python scripts/final_backtest.py`. Kết quả sinh lại giống hệt lần chạy trước (chênh 0,0 ở F1, AUC, IC, alpha). Đầu ra ở `results/research/final_backtest/` (`strategies.csv`, `random_baseline.csv`, `buy_and_hold.csv`).

### 16.1 Cách chạy backtest

- **Danh mục:** mỗi ngày mua nhóm 20% mã có điểm cao nhất (tối thiểu 3 mã), tỷ trọng bằng nhau, giữ đến phiên kế tiếp. Giá vào và ra là giá đóng cửa.
- **Chi phí (hệ số phí 1,0):** mua 0,15%, bán 0,25% (gồm thuế 0,1%). Phân tích nhạy cảm nhân phí với 0, 0,5, 1 và 2.
- **Hai cách giao dịch:** `daily` (chọn lại mỗi ngày) và `sticky` (giữ mã đang nắm cho đến khi hạng tụt quá 2 lần ngưỡng chọn), dùng để giảm số lần giao dịch.
- **Chuẩn so sánh:** danh mục 19 mã tỷ trọng bằng nhau, cân bằng lại mỗi ngày, không tính phí (alpha và beta tính so với chuẩn này); mua và nắm giữ từng mã; 200 danh mục chọn mã ngẫu nhiên cùng quy tắc (`random_state = 42`).
- **Chỉ số:** lợi suất năm hóa (trung bình ngày nhân 252), Sharpe, sụt giảm tối đa, alpha và beta theo hồi quy so với chuẩn, khoảng tin cậy 95% bootstrap theo khối (khối 10, 2.000 lần).
- **Giai đoạn:** dev (20 fold, 1.260 phiên) và xác nhận (6 fold từ 2025-01-01, 378 phiên).

### 16.2 Kết quả chính (hệ số phí 1,0, tức phí thực tế)

| Chiến lược | Giai đoạn | Lợi suất năm | Sharpe | Sụt giảm tối đa | Alpha năm [khoảng tin cậy 95%] | Beta | Mua mỗi ngày |
|---|---|---|---|---|---|---|---|
| Chuẩn: 19 mã tỷ trọng bằng nhau | dev | 22,8% | 0,99 | −34,7% | – | 1,00 | – |
| | xác nhận | 12,6% | 0,58 | −21,5% | – | 1,00 | – |
| `ensemble3` chọn lại mỗi ngày | dev | 7,6% | 0,26 | −37,4% | −17,8% [−28,5; −6,5] | 1,11 | 64% |
| | xác nhận | 11,2% | 0,41 | −34,7% | −1,9% [−24,5; +20,9] | 1,04 | 63% |
| `ensemble3` giữ vị thế (sticky) | dev | 25,3% | 0,87 | −37,9% | 0,0% [−11,5; +11,9] | 1,11 | 40% |
| | xác nhận | 22,3% | 0,80 | −37,8% | +9,1% [−17,9; +37,0] | 1,04 | 41% |

(Tỷ lệ mua mỗi ngày là phần danh mục phải mua mới, tính theo giá trị.)

### 16.3 Nhạy cảm với chi phí (alpha năm so với chuẩn)

| Hệ số phí | `daily` dev | `daily` xác nhận | `sticky` dev | `sticky` xác nhận |
|---|---|---|---|---|
| 0 (chưa phí) | +46,3% [+35,3; +58,0] | +61,4% [+37,9; +85,6] | +40,0% [+28,4; +52,2] | +50,5% [+22,5; +79,2] |
| 0,5 | +14,3% [+3,5; +25,8] | +29,8% [+6,8; +53,3] | +20,0% [+8,5; +32,0] | +29,8% [+2,4; +58,0] |
| 1,0 (phí thực tế) | −17,8% [−28,5; −6,5] | −1,9% [−24,5; +20,9] | 0,0% [−11,5; +11,9] | +9,1% [−17,9; +37,0] |
| 2,0 | −81,8% | −65,2% | −40,0% | −32,2% |

### 16.4 So với chọn mã ngẫu nhiên và mua và nắm giữ

- **Chọn ngẫu nhiên (200 danh mục, `daily`):** khi chưa tính phí, alpha ngẫu nhiên trung bình −0,6% (độ lệch chuẩn 5,0%) ở dev và −0,3% (9,2%) ở xác nhận. Không danh mục ngẫu nhiên nào đạt alpha của mô hình (+46,3% và +61,4%): tỷ lệ bằng 0 trên 200 lần. Đây là bằng chứng tín hiệu thật, chưa phải bằng chứng lợi nhuận. Với phí thực tế danh mục ngẫu nhiên lỗ nặng (alpha trung bình −80% mỗi năm) vì đảo danh mục mỗi ngày, nên so sánh có phí nên dựa vào chuẩn thị trường (mục 16.2), không dựa vào dòng này.
- **Mua và nắm giữ (tổng lợi suất cả giai đoạn):**

| Tài sản | Dev (1.260 phiên) | Xác nhận (378 phiên) |
|---|---|---|
| TCB | +157%, sụt giảm tối đa −64% | +18,9% |
| CTG | +148%, −52% | +5,0% |
| VNM | −10,5%, −42% | +10,2% |
| ACB | +209%, −42% | +15,7% |
| 19 mã tỷ trọng bằng nhau | +167%, −40% | +14,9% |

Danh mục `sticky` có phí thực tế cho tổng lợi suất +187% ở dev (+32% ở xác nhận) so với chuẩn +173% (+17%).

### 16.5 Nhận xét

1. **Tín hiệu xếp hạng thật nhưng nhỏ so với chi phí.** Trước phí, alpha +46% đến +61% mỗi năm, khoảng tin cậy xa 0 ở cả dev và xác nhận. Danh mục giữ lại khoảng 64% giá trị mua mới mỗi ngày với `daily`, nên phí thực tế (0,4% mỗi vòng mua bán) ăn hết lợi thế.
2. **Với phí thực tế không có alpha ròng khác 0 có ý nghĩa.** `daily` âm ở dev (−17,8%, khoảng tin cậy không chứa 0) và gần 0 ở xác nhận; `sticky` bằng 0,0% ở dev và +9,1% ở xác nhận với khoảng tin cậy rộng chứa 0. Khoảng tin cậy ở xác nhận rộng vì chỉ có 378 phiên.
3. **Giảm vòng quay giúp nhưng chưa đủ để kết luận có lãi.** `sticky` cắt lượng mua từ 64% xuống 40% mỗi ngày và nâng alpha ròng khoảng 18 điểm phần trăm ở dev. Điểm hòa vốn nằm quanh hệ số phí 1,0 (alpha dev 0,0%), nên kết quả nhạy với mức phí thực tế của từng nhà môi giới.
4. **Rủi ro không thấp hơn chuẩn.** Beta 1,04 đến 1,11 và sụt giảm tối đa −35% đến −38% (chuẩn −35% ở dev, −22% ở xác nhận). Lợi suất ròng của `sticky` gần chuẩn nhưng không rủi ro thấp hơn.
5. **Phải nêu khi đưa vào báo cáo.** Giá vào ra là giá đóng cửa; quy tắc T+2 của thị trường Việt Nam (cổ phiếu mua hôm nay chưa bán được ngay hôm sau) chưa được mô hình hóa, nên chiến lược `daily` không thực hiện được nguyên trạng; tập mã là 19 mã còn niêm yết và có dữ liệu đẹp nên có thiên lệch sống sót; chuẩn so sánh không tính phí cân bằng lại; xác nhận chỉ là kiểm tra ngoài mẫu một lần cho các cấu hình đã in ra, không phải thử nghiệm một lần đúng nghĩa (mục 14.1); mức phí là giả định của nhóm. Do đó kết luận đúng là: mô hình có khả năng xếp hạng mã tốt hơn ngẫu nhiên, còn lợi nhuận giao dịch sau phí chưa được chứng minh.

Hai file trung gian lớn (`results/research/pooled_abs_full/oof.csv.gz`, `data/extra/panel_1D.csv.gz`) đã bị xóa sau khi chạy xong, sinh lại bằng các lệnh ở đầu mục.

## 17. Giới hạn của kết quả (B11)

Mục này gom các giới hạn đã nêu rải rác ở mục 9, 11 đến 16 thành một chỗ để đưa vào báo cáo. Mỗi ý chỉ dựa trên số liệu có trong repo; ý nào chưa kiểm tra được thì ghi rõ là chưa kiểm tra.

### 17.1 Tín hiệu yếu, nhiễu lớn

- Mô hình tốt nhất (mục 14.8) chỉ đạt Accuracy 0,41 đến 0,42 so với 0,364 của lớp đa số, F1 macro 0,38 so với 0,330 của dự đoán ngẫu nhiên, ROC-AUC 0,58 so với 0,50. Chênh lệch giữa bốn mô hình nhỏ hơn độ lệch chuẩn giữa các fold (khoảng 0,03).
- Mô hình riêng từng mã gần như không hơn ngẫu nhiên: AUC phân biệt tăng với giảm chỉ 0,52 đến 0,54 (mục 9, 12, 14.8). Chỉ khi gộp mã mới có tín hiệu xếp hạng (IC khoảng 0,10), và tín hiệu đó chủ yếu là đảo chiều ngắn hạn (đặc trưng `ret_3` có IC −0,050), không phải một quy luật tổng quát về xu hướng (mục 14.2).
- Tín hiệu suy giảm nhanh theo chân trời: IC từ 0,122 (1 ngày) xuống 0,047 (20 ngày), và ở 10 đến 20 ngày không còn tín hiệu trong giai đoạn xác nhận (mục 14.7). Điều này phù hợp với thị trường gần hiệu quả: phần dự đoán được là nhỏ và biến mất khi giữ lâu hơn.
- Hệ quả: nhãn ba lớp với ngưỡng 0,5% có tỷ lệ các lớp gần nhau (khoảng 35% giảm, 30% ngang, 36% tăng), nên Accuracy trên 0,33 không đủ để kết luận mô hình có giá trị; luôn đặt cạnh lớp đa số và dự đoán ngẫu nhiên.

### 17.2 Quá khớp và chọn cấu hình trên cùng dữ liệu

- **Quá khớp rõ ràng khi chưa giới hạn độ phức tạp.** Với siêu tham số mặc định, Random Forest và XGBoost đạt F1 macro 1,000 trên tập train nhưng chỉ 0,347 và 0,342 trên tập test (mục 9.1). Sau khi giới hạn độ sâu và số mẫu ở lá, và nhất là sau khi gộp mã, khoảng cách này nhỏ hơn nhiều, nhưng chưa đo lại bằng đúng bảng train so với test cho mô hình cuối.
- **Thêm dữ liệu huấn luyện không cải thiện kết quả ở mô hình từng mã** (mục 9.4: F1 trên test không tăng khi tập train lớn lên). Cho thấy giới hạn nằm ở lượng thông tin trong đặc trưng chứ không ở số mẫu. Chưa kiểm tra lại điều này cho mô hình gộp.
- **Chọn lựa nhiều lần.** Qua các mục 10 đến 15, nhóm đã thử 16 cấu hình gộp và từng mã (nhãn tuyệt đối và tương đối, ba nhóm đặc trưng, chân trời từ 1 đến 20 ngày, mô hình hai giai đoạn, MLP) cùng các biến thể tinh chỉnh, 1H và nhiều mã. Việc chọn chỉ dựa trên dev, nhưng bảng xác nhận (từ 2025) đã được in ra cho mọi cấu hình, nên xác nhận là kiểm tra ngoài mẫu chứ không phải thử nghiệm một lần đúng nghĩa. Không hiệu chỉnh cho số lần thử, nên các khoảng tin cậy trong mục 16 có xu hướng lạc quan.
- Siêu tham số của mô hình gộp cố định từ đầu (không tinh chỉnh), nên nếu có thiên lệch thì không đến từ chọn siêu tham số, nhưng tinh chỉnh có thể cải thiện thêm; chưa làm.

### 17.3 Thay đổi chế độ thị trường

- F1 theo năm dao động và không có xu hướng cải thiện (mục 9.5); ở mô hình từng mã có năm mô hình thấp hơn ngẫu nhiên (XGBoost 2026, Logistic 2020, 2022 đến 2024 và 2026).
- Giai đoạn xác nhận (từ 2025) chỉ có 6 fold. Tín hiệu chân trời 10 và 20 ngày có ở dev nhưng mất ở xác nhận; alpha ròng chân trời 3 đến 5 ngày cũng không lặp lại (mục 14.7). Nên không giả định tín hiệu đảo chiều ngắn hạn bền vững qua các chế độ thị trường khác.
- Giai đoạn mẫu 2017 đến 2026 nhìn chung là tăng giá: danh mục 19 mã tỷ trọng bằng nhau tăng khoảng 173% trong 5 năm dev (22,8% mỗi năm, mục 16.2), ACB và TCB tăng 209% và 157%. Mọi chiến lược mua nhiều có beta trên 1 (1,04 đến 1,11) hưởng lợi từ xu hướng này. Phần alpha được tính để tách riêng ảnh hưởng đó, nhưng kết quả vẫn chưa được thử trong một thị trường đi xuống kéo dài (mẫu chỉ có VNM đi xuống ở dev).

### 17.4 Chi phí và cách khớp lệnh

- **Phí quyết định kết luận.** Trước phí alpha +46% đến +61% mỗi năm, với phí giả định 0,15% mua và 0,25% bán thì chọn lại mỗi ngày âm, giữ vị thế hòa vốn quanh 0 (mục 16.3). Mức phí thực tế của từng nhà môi giới không có trong dữ liệu, nên chỉ có thể báo cáo độ nhạy, không khẳng định có lãi hay lỗ.
- **T+2 chưa được mô hình hóa.** Cổ phiếu vừa mua chưa bán được ngay hôm sau, nên chiến lược chọn lại mỗi ngày không thực hiện được nguyên trạng; chỉ nên đọc kết quả 1 ngày như chất lượng tín hiệu (mục 14.7).
- **Khớp tại giá đóng cửa.** Chiến lược mua ở đúng giá đóng cửa của phiên đã có tín hiệu. Vào ở giá mở cửa hôm sau giữ khoảng 80% đến 90% alpha trước phí (mục 14.6) nhưng sau phí còn âm hơn.
- **Không tính trượt giá, thanh khoản, ảnh hưởng giá của lệnh.** Mỗi lần mua mới 64% danh mục mỗi ngày (mục 16.2) là khối lượng lớn đối với cổ phiếu có thanh khoản thấp hơn nhóm đang dùng. Chuẩn so sánh (19 mã tỷ trọng bằng nhau, cân bằng lại hằng ngày) không tính phí; mua và nắm giữ thực tế gần như không tốn phí cân bằng lại.

### 17.5 Mẫu dữ liệu và thiên lệch sống sót

- **Chọn mã có điều kiện.** 19 mã gồm 4 mã của đề bài và 15 mã được chọn trong 35 ứng viên thanh khoản cao, theo chất lượng dữ liệu và yêu cầu đủ khoảng 10 năm lịch sử (mục 12.1). Các mã niêm yết sau hoặc đã hủy niêm yết không có mặt, nên có thiên lệch sống sót; chưa đo được ảnh hưởng của nó lên hiệu ứng đảo chiều.
- **Các mã tương quan mạnh với nhau** (cùng thị trường, cùng ngành ngân hàng), nên số quan sát độc lập ít hơn 45.554 dòng. Chỉ số t của IC tính theo ngày chưa hiệu chỉnh tự tương quan; khoảng tin cậy bootstrap theo khối (khối 10 ngày) đáng tin hơn nhưng vẫn bỏ qua phụ thuộc dài hơn.
- **Nguồn dữ liệu.** API DNSE (Entrade) cho nến ngày từ khoảng 2016 đến 2018 tùy mã và khung 1H chỉ khoảng 2 năm; giá được giả định đã điều chỉnh chia tách và cổ tức (không thấy bước nhảy vượt biên độ sàn, nhưng chưa đối chiếu với nguồn thứ hai). Một số nến lỗi (ngày trùng, OHLC sai) đã sửa ở bước làm sạch (`data-preprocess.md` mục 2).
- **Khung 1H** chỉ có 2 năm và phần lớn điểm F1 cao đến từ hiệu ứng giờ trong ngày (baseline `hour_prior` F1 0,393 so với Logistic 0,416, mục 13.3), nên không dùng làm kết luận chính.

### 17.6 Điều có thể và không nên nói trong báo cáo

Có thể nói, vì có số liệu hỗ trợ:
- Mô hình gộp 19 mã xếp hạng mã tốt hơn ngẫu nhiên và hơn mô hình từng mã về IC và AUC tăng/giảm, kể cả ở giai đoạn xác nhận (IC 0,10, AUC tăng/giảm 0,59 trên 19 mã; trên riêng bốn mã gốc AUC 0,592 so với 0,559). F1 macro trên bốn mã gốc thì không tăng ở dev (mục 14.4).
- Trước phí, danh mục chọn theo mô hình có alpha dương rõ so với chuẩn và so với 200 danh mục ngẫu nhiên.
- Mô hình học cây không giới hạn quá khớp nặng trên dữ liệu ít tín hiệu, và việc giới hạn độ phức tạp cùng gộp mã giảm điều đó.

Không nên nói:
- "Mô hình có lãi" hoặc "thắng thị trường": alpha ròng sau phí chưa khác 0 có ý nghĩa (mục 16).
- "`ensemble3` tốt hơn rõ rệt các mô hình đơn": chênh lệch nhỏ hơn độ lệch chuẩn giữa các fold.
- "Giá cổ phiếu dự đoán được": chỉ có tín hiệu xếp hạng yếu, chủ yếu đảo chiều ngắn hạn, mất dần theo chân trời.
- Số liệu của lần chạy tốt nhất: luôn nêu kèm số cấu hình đã thử (mục 17.2).

### 17.7 Hướng phát triển

Theo thứ tự đáng làm, chưa làm cái nào:
1. Mô hình hóa T+2 và giá vào ở giá mở cửa hôm sau, giữ vị thế tối thiểu 2 đến 3 phiên, rồi đo lại alpha ròng.
2. Chạy thử không đặt lệnh (paper trading) để có phép kiểm tra ngoài mẫu thật sự, không dùng dữ liệu đã nhìn.
3. Tinh chỉnh siêu tham số của mô hình gộp trong từng fold; thử cửa sổ huấn luyện trượt cố định để xem dữ liệu cũ có làm yếu tín hiệu không.
4. Thêm mã (cả mã đã hủy niêm yết nếu có dữ liệu) để giảm thiên lệch sống sót; thử trên thị trường quốc tế như một kiểm tra khác chế độ.
5. Chỉ giao dịch khi điểm vượt ngưỡng, và lưu mô hình để dự đoán hằng ngày (hiện chỉ có backtest, chưa có mô hình lưu sẵn).

## 18. Khung 1H cho bốn mã gốc (B12)

Chạy `train_models.py` ở khung 1H cho TCB, CTG, VNM, ACB, đúng như mô tả của B12. Khung phút (1, 5, 15, 30) không chạy vì chỉ có 63 phiên (mục 7). Đây là thí nghiệm mở rộng, không đưa vào kết luận chính (mô hình chính là khung ngày, mục 15.3).

### 18.1 Thiết lập

- Dữ liệu `data/processed/1H/` (cùng 30 đặc trưng: 25 giá, khối lượng và 5 thời gian; ngưỡng nhãn θ = 0,2%; 2.446 đến 2.447 mẫu mỗi mã từ 2024-11-04 đến 2026-10-23), mô hình riêng từng mã, walk-forward train đầu 1.000 nến, test 125 nến, gap 1: **11 fold mỗi mã**, test ghép liền từ 2025-08-25 đến 2026-10-05 (1.375 nến, khoảng 275 phiên mỗi mã). Siêu tham số mặc định như mục 3.
- Lệnh: `python scripts/train_models.py --resolution 1H` (kết quả `results/1H/`) và `python scripts/hourly_ablation.py --processed-root data/processed --output-root results --symbols TCB CTG VNM ACB` (`results/1H/ablation_*.csv`, `hourly_profile.csv`). Mất khoảng 40 giây mỗi lệnh.
- Sửa Sharpe: `backtest()` trong `train_models.py` và `tune_models.py` nay nhận `periods_per_year`, tính bằng 252 nhân số nến mỗi phiên của dữ liệu (1 với khung ngày, khoảng 5 với 1H). Kết quả khung ngày không đổi về công thức (hệ số vẫn 252); `results/extra/1H/backtest.csv` đã tính lại.

### 18.2 Kết quả

Trung bình qua 11 fold (`results/1H/summary.csv`):

| Mã | F1 ngẫu nhiên | F1 Logistic | F1 Random Forest | F1 XGBoost | AUC Logistic | AUC Random Forest | AUC XGBoost |
|---|---:|---:|---:|---:|---:|---:|---:|
| TCB | 0,329 | 0,402 | 0,406 | 0,391 | 0,591 | 0,579 | 0,565 |
| CTG | 0,328 | 0,423 | 0,415 | 0,387 | 0,612 | 0,587 | 0,565 |
| VNM | 0,324 | 0,399 | 0,365 | 0,405 | 0,616 | 0,591 | 0,580 |
| ACB | 0,328 | 0,382 | 0,384 | 0,370 | 0,587 | 0,567 | 0,559 |
| **Trung bình 4 mã** | 0,327 | **0,401** | 0,392 | 0,388 | **0,601** | 0,581 | 0,567 |

Accuracy trung bình: Logistic 0,429, Random Forest 0,420, XGBoost 0,405, lớp đa số 0,371 (F1 macro 0,179). Quá khớp (F1 train so với test): Random Forest và XGBoost 1,000 so với 0,39; Logistic 0,457 so với 0,401. Con số F1 0,40 và AUC 0,60 khớp với số đã nêu ở mục 13.2 cho bốn mã gốc.

### 18.3 Tín hiệu đến từ đâu (bốn mã gốc)

Cùng phép so sánh như mục 13.3 (`ablation_summary.csv`, `ablation_differences.csv`):

| Biến thể | F1 macro | ROC-AUC | AUC tăng/giảm |
|---|---:|---:|---:|
| `hour_prior` (chỉ tần suất lớp theo giờ) | 0,376 | 0,596 | 0,570 |
| Logistic, 25 đặc trưng giá | 0,331 | 0,547 | 0,550 |
| Logistic, chỉ 5 đặc trưng thời gian | 0,382 | 0,595 | 0,571 |
| Logistic, giá và thời gian | 0,401 | 0,601 | 0,578 |
| Random Forest, giá và thời gian | 0,392 | 0,581 | 0,567 |

Chênh lệch (khoảng tin cậy 95%): Logistic giá và thời gian hơn `hour_prior` +0,026 F1 [+0,012; +0,040] nhưng AUC chỉ +0,005 [−0,003; +0,014] (chứa 0); Random Forest hơn +0,017 F1 [−0,004; +0,037] và thấp hơn 0,015 AUC [−0,029; −0,001]; Logistic chỉ giá **thấp hơn** `hour_prior` 0,045 F1 và 0,049 AUC.

Lợi suất nến kế tiếp theo giờ (`hourly_profile.csv`): giờ 9 −0,066%, 10 −0,056%, 11 +0,047%, 13 +0,022%, 14 +0,095%; tỷ lệ lớp "ngang" 57% ở nến 10 giờ và 27% ở nến 14 giờ. Mọi giá trị nhỏ hơn 1/4 chi phí một vòng mua bán (0,40%).

### 18.4 Backtest (long-only, phí 0,15% mua và 0,25% bán, tổng lợi suất cả giai đoạn test)

| Mã | Mua và nắm giữ | Logistic | Random Forest | XGBoost | Ngẫu nhiên | Số lệnh mua (3 mô hình) |
|---|---:|---:|---:|---:|---:|---:|
| TCB | −12,9% | −47,5% | −29,9% | −49,0% | −61,2% | 184 đến 207 |
| CTG | −12,0% | −49,9% | −44,9% | −60,0% | −62,4% | 215 đến 228 |
| VNM | +4,4% | −20,4% | −33,4% | −26,6% | −47,7% | 129 đến 156 |
| ACB | −8,5% | −44,1% | −31,7% | −36,7% | −58,4% | 162 đến 195 |

`majority` (đứng ngoài thị trường) cho 0% và là chiến lược duy nhất hơn mua và nắm giữ ở TCB, CTG, ACB.

### 18.5 Nhận xét

1. **Kết quả lặp lại các mã mới (mục 13):** F1 Logistic 0,40 và AUC 0,60 cao hơn nhiều so với khung ngày của cùng bốn mã (AUC 0,52 đến 0,54, mục 5), nhưng phần lớn nhờ giờ trong ngày: 5 đặc trưng thời gian riêng lẻ đã cho AUC 0,595 và `hour_prior` 0,596. Đóng góp của chỉ báo giá trên nền đó nhỏ (AUC +0,005, khoảng tin cậy chứa 0).
2. **Đặc trưng giá khung 1H không dự đoán được hướng:** Logistic chỉ giá có AUC 0,547, gần khung ngày.
3. **Backtest lỗ nặng ở cả ba mô hình và cả bốn mã**, nặng hơn mua và nắm giữ, với 129 đến 228 lệnh mua trong khoảng 275 phiên: phí 0,4% mỗi vòng và hiệu ứng theo giờ nhỏ hơn 1/4 phí. Giữ nguyên kết luận mục 13.6: không đưa 1H vào kết luận chính, và nếu nêu F1 0,40 phải kèm baseline `hour_prior`.
4. **Hạn chế:** chỉ khoảng hai năm dữ liệu, 11 fold, mỗi khối test khoảng 25 phiên, và mô hình riêng từng mã (không gộp mã như mô hình chính). Gộp mã ở khung 1H chưa thử.

## 19. Mô hình triển khai (gói mô hình đã lưu)

Gói `models/ensemble3_pooled_1D/` là mô hình chính (gộp 19 mã + `ensemble3`, khung ngày, 53 đặc trưng `full`, nhãn tuyệt đối ba lớp) huấn luyện **một lần trên toàn bộ dữ liệu có nhãn** (45.554 dòng, 2017-02-22 đến 2026-11-04), dùng để chạy dự đoán ở máy khác mà không phải huấn luyện lại. Lệnh: `python scripts/train_final_model.py` (thêm `--no-gpu` nếu không có GPU; mất khoảng 5 giây).

| File | Nội dung | Kích thước |
|---|---|---|
| `logistic.joblib` | Pipeline scaler và Logistic (`C = 0,1`) | dưới 0,01 MB |
| `random_forest.joblib` | 300 cây, `min_samples_leaf = 50` | 10,0 MB |
| `xgboost.json` | 300 cây, `max_depth = 4`, `learning_rate = 0,05` | 1,8 MB |
| `metadata.json` | danh sách 53 đặc trưng theo thứ tự, thứ tự lớp, ngưỡng nhãn, 19 mã, khoảng thời gian huấn luyện, phiên bản thư viện, commit | nhỏ |

Cách dùng: `load_bundle(thư_mục)` và `ensemble_probabilities(bundle, bảng_đặc_trưng)` trong `train_final_model.py` trả về `p_down`, `p_flat`, `p_up` (trung bình xác suất của ba mô hình) và `score = p_up - p_down`.

Đã kiểm tra:
- Nạp lại gói cho xác suất khớp bản trong bộ nhớ (chênh lớn nhất 2e-8 trên 500 dòng; sai khác nhỏ do XGBoost huấn luyện trên GPU và dự đoán trên CPU).
- Tiến trình riêng, **không có GPU** (`CUDA_VISIBLE_DEVICES=""`), nạp gói và dự đoán 15 mã của một ngày mất 0,7 giây, bộ nhớ đỉnh khoảng 260 MB (đo bằng `/usr/bin/time -v`, bao gồm nạp thư viện). Tổng thể nhẹ hơn nhiều so với ước tính 1 GB khi huấn luyện.
- Tổng thư mục 12 MB.

Lưu ý:
- **Gói không có đánh giá riêng.** Hiệu năng kỳ vọng là kết quả walk-forward ở mục 14.8 và 16, không phải số đo trên chính dữ liệu đã huấn luyện. Không dùng gói này để chạy lại backtest lịch sử (mô hình đã thấy dữ liệu đó).
- **Phiên bản thư viện phải khớp** với `metadata.json` (Python 3.14.4, scikit-learn 1.9.1, xgboost 3.4.1, numpy 2.5.4, pandas 3.1.1), vì file `joblib` phụ thuộc phiên bản. `requirements.txt` hiện ghim phiên bản cũ hơn và chưa khớp.
- **Ngày dữ liệu của mã.** Dữ liệu bốn mã gốc (TCB, CTG, VNM, ACB) trong `data/cleaned/` dừng ở 2026-10-23, còn 15 mã bổ sung đến 2026-11-05, nên ngày cuối của panel (2026-11-04) chỉ có 15 mã. Khi chạy thật phải crawl lại đủ 19 mã.
- Khâu dự đoán hằng ngày: `scripts/predict_daily.py` (mục 20).
- Cần huấn luyện lại định kỳ (backtest dùng chu kỳ 63 phiên).

## 20. Dự đoán hằng ngày (paper trading)

`scripts/predict_daily.py` nạp gói mô hình (mục 19), chấm điểm nến ngày mới nhất của 19 mã và cập nhật nhật ký. Không huấn luyện, không cần GPU.

```bash
.venv/bin/python scripts/predict_daily.py --crawl
```

Chạy sau 15:05 giờ Việt Nam (nến ngày đóng lúc 15:00; bước làm sạch bỏ nến của hôm nay nếu chạy trước giờ đó). Tham số: `--crawl` lấy lại khoảng 420 ngày lịch (khoảng 290 nến) của 19 mã từ DNSE vào `data/live/raw/1D/` (thư mục này không commit); không có `--crawl` thì đọc file đã có; `--days N` chấm điểm N ngày gần nhất (dùng để lấp nhật ký); `--model-dir`, `--output-dir`, `--buffer` (mặc định 2,0 như backtest).

**Đầu vào:** nến ngày thô `time, open, high, low, close, volume` của 19 mã trong `metadata.json` (cần đủ cả 19 mã vì đặc trưng thị trường và hạng chéo mã tính từ tất cả các mã cùng ngày). Qua cùng bước làm sạch như huấn luyện (`clean_data.py`), rồi dựng đặc trưng bằng `panel_data.featurize` (cùng mã với panel huấn luyện, `build_panel` giữ nguyên kết quả sau khi tách hàm: so sánh bằng nhau trên 45.554 dòng). Không cần VN-Index.

**Đầu ra** (`results/live/`):
- `predictions_log.csv`: nhật ký nối thêm mỗi ngày, một dòng cho mỗi (ngày, mã): `p_down`, `p_flat`, `p_up`, `score = p_up - p_down`, `rank` (1 là điểm cao nhất), `n_symbols`, `model_trained_until`, `scored_at`. Chạy lại cùng ngày thì ghi đè các dòng của ngày đó (không trùng).
- `latest_signals.csv` (và in ra màn hình): các mã của ngày mới nhất kèm `daily_top` (nhóm 20% điểm cao nhất, tối thiểu 3 mã, tức 4 mã trong 19) và `sticky_hold`, `sticky_action` (`buy`, `sell`, `hold` so với hôm trước) theo cách giữ vị thế của backtest. Vị thế `sticky` được tính lại từ toàn bộ nhật ký nên phụ thuộc ngày bắt đầu ghi.

**Số nến cần thiết.** Đo bằng cách tính đặc trưng từ lịch sử bị cắt ngắn rồi so với đặc trưng dựng từ toàn bộ lịch sử, trên 591 dòng của 45 ngày gần nhất:

| Số nến mỗi mã | Chênh lệch điểm lớn nhất | Tỷ lệ giữ nguyên thứ hạng |
|---|---:|---:|
| 400 | 2e-13 | 100% |
| 270 | 4e-9 | 100% |
| 150 | 3e-3 | 99,7% |
| 120 | 2e-3 | 98,3% |
| 100 | 8e-3 | 94,6% (mất 76 trong 591 dòng) |

Chỉ báo dạng EMA phụ thuộc cả lịch sử nên chuỗi ngắn làm lệch nhẹ. Khuyến nghị **từ 250 nến**; script cảnh báo khi một mã ít hơn 250 nến đã đóng. (Con số 120 đến 150 nêu ở phần thảo luận trước chỉ là mức tối thiểu.)

**Cảnh báo script đưa ra:** phiên bản scikit-learn, xgboost, numpy, pandas khác lúc lưu mô hình; mô hình huấn luyện cách ngày chấm hơn 100 ngày (cần huấn luyện lại bằng `train_final_model.py`); thiếu mã ở ngày chấm; nến mới nhất cũ hơn 4 ngày.

**Đã chạy thử:** `--crawl --days 3` ngày 2026-11-06 lúc 15:27: thu 19 mã, mỗi mã 287 nến, chấm 3 ngày (57 dòng nhật ký, không trùng), mất khoảng 1 giây không kể thời gian crawl. Chạy lại không tạo dòng trùng. Nhật ký thử đã xóa để việc ghi thật bắt đầu từ ngày bạn chọn.

**Lưu ý khi đọc nhật ký:**
- Chỉ các dòng có `time` sau `model_trained_until` mới là ngoài mẫu; các dòng không sau ngày đó nằm trong dữ liệu huấn luyện, không dùng để đánh giá.
- Điểm là tín hiệu xếp hạng từ giá đóng cửa của `time`. Vào lệnh thực tế ở phiên kế tiếp (giá mở cửa hoặc sau đó), T+2 chưa được mô hình hóa, và kết quả backtest cho thấy alpha ròng sau phí chưa khác 0 có ý nghĩa (mục 16). Không dùng làm khuyến nghị giao dịch.
- Ngày lễ: không có nến mới nên script chấm lại ngày cuối và ghi đè, không gây lỗi.
- Chưa có script đối chiếu nhật ký với lợi suất thực tế (cần thêm khi đủ số ngày).

Lịch chạy tự động (ví dụ cron, múi giờ Việt Nam): `5 15 * * 1-5 cd <repo> && .venv/bin/python scripts/predict_daily.py --crawl`.
