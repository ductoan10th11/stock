# Cấu trúc nội dung theo bộ tiêu chí chấm học phần Học máy

Bộ tiêu chí có 4 mốc: Bài kiểm tra 1 (tuần 4), 2 (tuần 6), 3 (tuần 8) và Bài
thi kết thúc (tuần 9). Mỗi mốc 10 tiêu chí, [N] = sản phẩm nhóm, [CN] = cá nhân
(vấn đáp). Báo cáo chỉ là minh chứng cho tiêu chí [N]; tiêu chí [CN] chấm qua
vấn đáp nên không cần viết vào báo cáo, nhưng phần giải thích nguyên lý
(Chương 1) giúp sinh viên chuẩn bị.

Mẫu có 3 chương: (1) Tổng quan về học máy và bài toán \tenbaitoan (tên bài
toán đặt ở khối (A)), (2) Mô hình hóa bài toán và phương pháp \tenbaitoan, (3) Thực nghiệm và
đánh giá — phần dữ liệu nằm ở đầu Chương 3.

Dùng bảng này để (1) đặt nội dung có sẵn của sinh viên vào đúng mục, (2) chỉ ra
mục còn thiếu so với mốc đang nộp.

## Chương 2 (2.1, 2.2, 2.5) + Chương 3 (3.1–3.4) — Bài toán và dữ liệu ↔ Bài kiểm tra 1
| Mục trong mẫu | Tiêu chí | Cần có để đạt tối đa |
|---|---|---|
| 2.1 Phát biểu bài toán | KT1-1 | Loại bài toán, đơn vị mẫu, đầu vào, đầu ra — cụ thể với dữ liệu nhóm |
| 2.2 Mục tiêu (Bảng mục tiêu–chỉ số) | KT1-2 | Mục tiêu thực tế → mục tiêu ML, chỉ số chính, mức mong muốn |
| 3.1 Dữ liệu thực nghiệm (từ điển dữ liệu) | KT1-3 | Nguồn, điều kiện sử dụng, số mẫu, số đặc trưng, kiểu, ý nghĩa từng đặc trưng |
| 3.2.1 Thống kê, phân bố | KT1-4 | Thống kê mô tả, biểu đồ phân bố + **nhận xét từng biểu đồ** |
| 3.2.2 Quan hệ đặc trưng | KT1-5 | Tương quan, ≥ 3 nhận xét có ích cho mô hình |
| 3.3 Chất lượng dữ liệu | KT1-6, 7 | **Định lượng** thiếu/trùng/ngoại lai/mất cân bằng/rò rỉ; cách xử lý + lý do; trước–sau |
| 3.4 Chuẩn bị dữ liệu | KT1-8 | Mã hóa, chuẩn hóa, cách chia tập; fit chỉ trên tập huấn luyện |
| 2.5 Phương pháp & chỉ số | KT1-9 | Lý do chọn hold-out/K-Fold/TimeSeriesSplit và chỉ số |

## Chương 2 (2.3–2.4) + Chương 3 (3.5–3.7) — Mô hình ↔ Bài kiểm tra 2
| Mục | Tiêu chí | Cần có |
|---|---|---|
| 2.3.1 Lựa chọn thuật toán | KT2-1 | ≥ 2 thuật toán phù hợp, có lý do |
| 2.3.2 Mô hình cơ sở | KT2-2 | Baseline (lớp đa số/trung bình/tuyến tính) và kết quả |
| 2.4 Quy trình huấn luyện + 3.5 Môi trường | KT2-3, 4 | Pipeline/ColumnTransformer, cố định random_state, đoạn mã chính |
| 3.6 Kết quả | KT2-5, 6 | CV trên tập huấn luyện, mean ± std; bảng so sánh với baseline; ma trận nhầm lẫn/ROC/phần dư. Dữ liệu mất cân bằng: không chỉ báo Accuracy |
| 3.7 Phân tích dự đoán | KT2-7 | Nhóm mẫu sai nhiều; so sánh train–validation (quá khớp/chưa khớp) |
| Chương 1 mục 1.3 | KT2-8 (CN) | Ý tưởng, hàm mục tiêu, siêu tham số chính của thuật toán đã dùng |

## Chương 3 (3.8–3.10) — Tối ưu hóa và cải tiến ↔ Bài kiểm tra 3
| Mục | Tiêu chí | Cần có |
|---|---|---|
| 3.8.1 Hạn chế | KT3-1 | Bằng chứng: chênh lệch train–val, learning curve, lỗi tập trung |
| 3.8.2–3.8.4 Giải pháp | KT3-2, 3, 4, 5 | ≥ 2 giải pháp gắn với hạn chế; cải tiến dữ liệu/đặc trưng; thuật toán/ensemble mới; tìm siêu tham số trên CV (không dùng tập test) |
| 3.9 So sánh (ablation) | KT3-6, 8 | Cùng dữ liệu, cùng cách chia, cùng chỉ số; đóng góp từng thay đổi; biểu đồ có nhãn trục + nhận xét |
| 3.10.1 Tổng quát hóa | KT3-7 | Kết quả test giữ lại so với CV; độ ổn định qua fold |
| 3.10.2 Mô hình cuối | KT3-9 (CN) | Đánh đổi độ chính xác – ổn định – thời gian – diễn giải |

## Bài thi kết thúc
| Thành phần | Tiêu chí | Cần có |
|---|---|---|
| Toàn bộ chương 2–3 | KT4-1, 2 | Đủ quy trình, đã sửa tồn tại của 3 mốc |
| Phụ lục A | KT4-3 | README, requirements, seed; lệnh chạy lại |
| Chương 3 + Kết luận | KT4-4 | Mô hình cuối vượt baseline hoặc giải thích; báo cáo trung thực (không chỉ lần chạy tốt nhất) |
| Toàn báo cáo | KT4-5 | Đúng mẫu, văn phong khoa học, hình–bảng đúng quy cách, trích dẫn đủ |
| Bảng phân công + Phụ lục B | KT4-10 | Phân công cụ thể, nhật ký/commit có ngày cho cả 9 tuần |
| Lời cam đoan | Liêm chính | Khai báo phạm vi dùng AI tạo sinh |
