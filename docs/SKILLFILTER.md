---
name: bank-stock-data-filter
description: Lọc, làm sạch và chuẩn bị dữ liệu giá cổ phiếu ngân hàng Việt Nam (HOSE/HNX/UPCoM) để huấn luyện mô hình dự đoán tăng/giảm. Dùng khi người dùng nhắc đến cổ phiếu ngân hàng (VCB, BID, CTG, TCB, MBB, VPB, ACB, STB, HDB, TPB, VIB, SHB, ...), dữ liệu OHLCV, dự đoán tăng giảm, feature engineering cho chứng khoán, hoặc muốn lọc dữ liệu thị trường Việt Nam trước khi làm mô hình.
---

# Lọc dữ liệu cổ phiếu ngân hàng Việt Nam cho dự đoán tăng/giảm

Skill này hướng dẫn quy trình từ dữ liệu thô đến tập dữ liệu sạch, không rò rỉ thông tin tương lai, sẵn sàng cho mô hình phân loại (tăng = 1, giảm = 0). Không đưa ra khuyến nghị đầu tư; kết quả mô hình chỉ là tham khảo.

## 1. Xác định phạm vi

Trước khi xử lý, hỏi hoặc xác nhận (nếu người dùng chưa nói rõ):
- Danh sách mã: mặc định các ngân hàng niêm yết lớn gồm VCB, BID, CTG, TCB, MBB, VPB, ACB, STB, HDB, TPB, VIB, SHB. Ghi rõ mã nào không có đủ dữ liệu.
- Khoảng thời gian và tần suất (ngày, tuần). Mặc định là dữ liệu ngày.
- Nguồn dữ liệu: file CSV người dùng cung cấp, hoặc thư viện như `vnstock`. Nếu lấy qua API, ghi lại ngày truy xuất.

## 2. Chuẩn hóa cấu trúc

Đầu vào tối thiểu phải có: `ticker`, `date`, `open`, `high`, `low`, `close`, `volume`.
- Chuyển `date` sang kiểu datetime, sắp xếp theo `ticker` rồi `date`.
- Đổi tên cột về chữ thường, bỏ khoảng trắng thừa.
- Giá Việt Nam thường tính theo nghìn đồng; giữ nguyên đơn vị gốc và ghi chú trong báo cáo.

## 3. Lọc mã và giai đoạn

- Loại mã không phải ngân hàng hoặc không có trong danh sách đã xác nhận.
- Loại mã có ít hơn khoảng 250 phiên giao dịch (không đủ để tính MA dài hạn).
- Loại các phiên có `volume = 0` hoặc `close` không đổi hoàn toàn nếu là phiên không giao dịch do đình chỉ; ghi lại số lượng bị loại.
- Lọc các giai đoạn bất thường rõ ràng (ví dụ mã bị hủy niêm yết tạm thời hoặc sau khi sáp nhập) và ghi rõ trong báo cáo.

## 4. Làm sạch

- **Trùng lặp:** kiểm tra cặp (`ticker`, `date`) trùng; giữ một bản ghi và ghi số lượng.
- **Thiếu giá trị:** không điền bằng giá trị tương lai. Dùng forward fill chỉ trong phạm vi một mã và tối đa 2 phiên; phần còn lại loại bỏ.
- **Giá điều chỉnh:** kiểm tra xem `close` đã điều chỉnh cổ tức và chia tách cổ phiếu chưa. Nếu chưa, không dùng giá gốc để tính lợi suất dài hạn. Ghi rõ nguồn điều chỉnh.
- **Ngoại lai:** phát hiện bằng lợi suất ngày vượt quá ngưỡng (ví dụ ±7%, tương ứng biên độ sàn/trần HOSE) hoặc giá `high < low`, `close` ngoài khoảng `[low, high]`. Không tự xóa; đánh dấu và báo cho người dùng quyết định.
- **Phiên sàn/trần:** đánh dấu cờ `limit_hit` để có thể kiểm tra riêng.

## 5. Tạo đặc trưng (không dùng thông tin tương lai)

Mọi đặc trưng tại ngày `t` chỉ dùng dữ liệu đến hết ngày `t`:
- Lợi suất: `ret_1d`, `ret_5d`, `ret_20d` từ `close`.
- Biến động: độ lệch chuẩn của lợi suất 10 và 20 phiên.
- Trung bình động: tỷ lệ `close / MA_k - 1` với k = 5, 10, 20, 60.
- Động lượng: RSI(14), MACD.
- Khối lượng: `volume / MA_20(volume)`.
- Biên độ: `(high - low) / close`.
- Nếu có dữ liệu vĩ mô (lãi suất, tỷ giá USD/VND, chỉ số VN-Index), căn theo ngày giao dịch và lùi một phiên khi cần để tránh lookahead.

Tính toán theo từng mã bằng `groupby('ticker')`, không tính chéo giữa các mã.

## 6. Nhãn

- `target = 1` nếu `close(t+1) > close(t)`, ngược lại `0`.
- Hàng cuối của mỗi mã không có nhãn; loại bỏ.
- Kiểm tra tỷ lệ nhãn 0/1. Nếu lệch mạnh (ví dụ lớn hơn 60/40), báo cáo và đề xuất đánh giá bằng F1 hoặc AUC thay vì accuracy.

## 7. Chia tập dữ liệu

- Chia theo thời gian, không chia ngẫu nhiên. Ví dụ: 70% đầu để huấn luyện, 15% tiếp theo để kiểm định, 15% cuối để kiểm tra.
- Khi dùng nhiều mã, chia theo cùng mốc thời gian cho mọi mã.
- Chuẩn hóa (scaler) chỉ fit trên tập huấn luyện.
- Cần khoảng đệm (gap) vài phiên giữa các tập nếu đặc trưng dùng cửa sổ dài.

## 8. Kiểm tra rò rỉ trước khi xuất

Trước khi chuyển sang bước huấn luyện, xác nhận:
- Không có đặc trưng nào chứa `close` của ngày sau `t`.
- `target` không xuất hiện trong danh sách đặc trưng.
- Không có cột định danh (ticker dạng one-hot có thể dùng, nhưng không dùng ngày).
- Phân phối nhãn đã được báo cáo theo từng mã và theo năm.

## 9. Đầu ra

Xuất ra:
- `bank_stocks_clean.parquet` hoặc `.csv`: dữ liệu đã làm sạch, có đặc trưng và nhãn.
- `data_report.md`: số dòng ban đầu và sau mỗi bước lọc, danh sách mã bị loại và lý do, số ngoại lai, nguồn và ngày điều chỉnh giá, phân phối nhãn.

Khi trả lời người dùng, tóm tắt ngắn: số mã, khoảng thời gian, số dòng cuối cùng, và những điểm cần người dùng xác nhận.

### Quy tắc đã chốt cho dự án `stock-main`

Phạm vi dự án này đã được xác nhận gồm TCB, CTG, VNM, ACB; VNM được giữ lại để
đúng đề bài dù không phải ngân hàng. Bộ dữ liệu chính dùng nhãn ba lớp thay cho
nhãn nhị phân của quy tắc mặc định:

```
r_next(t) = ln(close[t+1] / close[t])
label = 1 nếu r_next > θ, -1 nếu r_next < -θ, còn lại 0
```

| Khung | θ | Đặc trưng | Train đầu | Test/fold | Gap |
|---|---:|---:|---:|---:|---:|
| 1 phút | 0.05% | 30 | 9.000 | 1.125 | 1 |
| 5 phút | 0.10% | 30 | 1.800 | 225 | 1 |
| 15 phút | 0.15% | 30 | 640 | 80 | 1 |
| 30 phút | 0.15% | 30 | 315 | 45 | 1 |
| 1 giờ | 0.20% | 30 | 1.000 | 125 | 1 |
| 1 ngày | 0.50% | 25 | 750 | 63 | 1 |

Mọi khung dùng 25 đặc trưng OHLCV đã mô tả trong `docs/data-preprocess.md`.
Các khung nội ngày thêm `time_sin`, `time_cos`, `weekday_sin`, `weekday_cos`,
`is_first_bar`. Bỏ 35 nến khởi động và nến cuối không có nhãn. Xuất dữ liệu vào
`data/processed/<KHUNG>/<MÃ>.csv` cùng báo cáo
`data/processed/preprocessing_summary.csv`.

## Lưu ý

- Dự đoán tăng/giảm cổ phiếu có độ không chắc chắn cao; luôn nói rõ điều này khi trình bày kết quả.
- Không dùng dữ liệu tài chính cá nhân của người dùng nếu họ không cung cấp rõ ràng.
- Nếu dữ liệu không đủ hoặc không rõ nguồn, dừng và hỏi trước khi tiếp tục.
