# Báo cáo lọc dữ liệu cổ phiếu ngân hàng

## Phạm vi và nguồn dữ liệu

- Nguồn: API biểu đồ DNSE (Entrade), được lưu trong `data/raw/1D`.
- Ngày cuối của dữ liệu nguồn: 2026-10-23.
- Ngày cuối có thể gán nhãn: 2026-10-22.
- Mã đầu vào: TCB, CTG, VNM, ACB.
- Mã bị loại vì không phải ngân hàng: VNM.
- Mã bị loại vì có dưới 250 phiên: Không có.
- Đơn vị giá được giữ nguyên theo nguồn: nghìn đồng.
- Trạng thái điều chỉnh cổ tức/chia tách chưa được DNSE xác nhận chính thức; cần xác nhận trước khi diễn giải lợi suất dài hạn.

## Kết quả lọc

- Tổng số dòng thô: 9580.
- Số dòng sau khi chỉ giữ mã ngân hàng: 7085.
- Số dòng theo tệp nguồn: TCB: 2098, CTG: 2495, VNM: 2495, ACB: 2492.
- Dòng trùng (`ticker`, `date`) đã loại: 3.
- Ô thiếu trước forward fill: 0; dòng còn thiếu sau forward fill tối đa 2 phiên và đã loại: 0.
- Dòng giá không dương đã loại: 0.
- Phiên volume không dương đã loại: 0.
- Dòng warm-up hoặc không có nhãn đã loại: 180.
- Tổng số dòng cuối cùng: 6902.
- Ngoại lai và phiên chạm biên độ được giữ lại, đánh dấu bằng `outlier`, `ohlc_invalid` và `limit_hit`.

## Thống kê theo mã

```text
        rows  first_date   last_date  outliers  limit_hits
ticker                                                    
ACB     2431  2017-01-18  2026-10-22         0           0
CTG     2434  2017-01-18  2026-10-22         3          18
TCB     2037  2018-08-24  2026-10-22         3          12
```

## Phân phối nhãn theo mã

```text
target  giảm  tăng
ticker            
ACB     1319  1112
CTG     1258  1176
TCB     1070   967
```

## Phân phối nhãn theo mã và năm

```text
target       giảm  tăng
ticker year            
ACB    2017   130   109
       2018   136   114
       2019   146   104
       2020   126   121
       2021   125   125
       2022   128   121
       2023   130   119
       2024   134   116
       2025   143   106
       2026   121    77
CTG    2017   129   110
       2018   135   113
       2019   142   108
       2020   124   128
       2021   131   119
       2022   129   120
       2023   127   122
       2024   120   130
       2025   116   133
       2026   105    93
TCB    2018    49    41
       2019   151    99
       2020   125   127
       2021   120   130
       2022   134   115
       2023   132   117
       2024   131   119
       2025   125   124
       2026   103    95
```

## Kiểm tra rò rỉ

- Các đặc trưng tại ngày `t` chỉ dùng dữ liệu đến hết ngày `t`.
- `target` dùng giá đóng cửa ngày kế tiếp và không thuộc danh sách đặc trưng.
- `ticker` và `date` chỉ là cột định danh, không tự động đưa vào ma trận đặc trưng.
- Việc chia train/validation/test và fit scaler phải được thực hiện ở bước huấn luyện theo thời gian.

Kết quả mô hình dự đoán tăng/giảm có độ không chắc chắn cao và không phải khuyến nghị đầu tư.
