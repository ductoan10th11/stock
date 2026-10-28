# Đề bài: Dự đoán xu hướng tăng/giảm giá cổ phiếu

# Nhiệm vụ:

1. Nghiên cứu đặc điểm chuỗi giá cổ phiếu và các chỉ báo kỹ thuật (SMA, EMA, RSI, MACD, Bollinger Bands); phát biểu bài toán phân loại xu hướng.
2. Thu thập dữ liệu giá lịch sử của một số mã cổ phiếu (thị trường Việt Nam hoặc quốc tế) và tính toán các chỉ báo kỹ thuật làm đặc trưng.
3. Huấn luyện Logistic Regression, Random Forest, XGBoost với walk-forward validation; so sánh với chiến lược cơ sở (mua và nắm giữ, dự đoán ngẫu nhiên).
4. Đánh giá bằng Accuracy, F1, ROC-AUC và lợi nhuận mô phỏng (backtest đơn giản); thảo luận giới hạn của việc dự đoán giá và nguy cơ quá khớp.

- Gợi ý thuật toán: Logistic Regression, Random Forest, XGBoost, SVM.

# Data:

https://banggia.dnse.com.vn/v2?symbol=TCB
https://banggia.dnse.com.vn/v2?symbol=CTG
https://banggia.dnse.com.vn/v2?symbol=VNM
https://banggia.dnse.com.vn/v2?symbol=ACB

nến: 1d
khoảng crawl: 6 tháng
