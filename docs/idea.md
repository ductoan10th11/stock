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

---

# Kiến trúc và flow hoạt động của dự án

Các sơ đồ dưới đây vẽ bằng Mermaid, hiển thị trực tiếp trên GitHub. Trong VS Code, cần cài tiện ích "Markdown Preview Mermaid Support" để xem ở chế độ xem trước. Chi tiết từng bước và trạng thái nằm ở [flow.md](flow.md); kết quả huấn luyện nằm ở [train.md](train.md).

Chú thích màu: xanh dương là mã nguồn, vàng là dữ liệu, xanh lá là kết quả hoặc bước đã xong, cam là bước làm một phần, xám nét đứt là bước chưa làm.

## 1. Kiến trúc: mã nguồn, dữ liệu và kết quả

Luồng đi từ nguồn dữ liệu đến báo cáo. Mỗi script đọc thư mục dữ liệu ở bước trước và ghi thư mục dữ liệu ở bước sau, không ghi đè dữ liệu thô.

```mermaid
flowchart TD
    API(["API DNSE (Entrade)<br/>nến 1, 5, 15, 30 phút, 1H, 1D"])

    crawl["scripts/crawl.py<br/>thu thập nến"]
    raw[("data/raw/KHUNG/MÃ.csv<br/>time, open, high, low, close, volume")]

    clean["scripts/clean_data.py<br/>gộp ngày trùng, sửa OHLC,<br/>bỏ volume 0, bỏ nến chưa đóng,<br/>dựng khung 30 phút từ 5 phút"]
    cleaned[("data/cleaned/KHUNG/MÃ.csv")]

    prep["scripts/preprocess_data.py<br/>25 đặc trưng (30 với khung nội ngày),<br/>r_next, label với ngưỡng θ,<br/>bỏ 35 dòng khởi động"]
    processed[("data/processed/KHUNG/MÃ.csv<br/>đặc trưng, r_next, label")]

    train["scripts/train_models.py<br/>walk-forward, 3 mô hình, baseline, backtest"]
    analyze["scripts/analyze_results.py<br/>quá khớp, nhầm lẫn, importance, hình"]
    results[("results/KHUNG/<br/>fold_metrics, predictions, backtest,<br/>feature_importance, summary")]

    eda["notebooks/eda.ipynb<br/>khảo sát dữ liệu"]
    nbm["notebooks/models.ipynb<br/>3 thuật toán, baseline, walk-forward"]
    nbt["notebooks/tuning.ipynb<br/>ablation, siêu tham số, Voting"]
    filt["scripts/filter_data.py<br/>nhánh thử nghiệm: chỉ ngân hàng, nhãn 2 lớp"]
    filtered[("data/filtered/")]

    docs["docs/train.md<br/>ghi chép số liệu"]
    report["docs/project-report/bao-cao/<br/>bao_cao.tex, hình, bảng"]

    API --> crawl --> raw --> clean --> cleaned --> prep --> processed --> train --> results --> docs --> report
    results --> analyze --> report
    raw --> eda --> report
    processed --> nbm --> report
    processed --> nbt --> report
    raw --> filt --> filtered
    prep -. "import walk_forward_splits,<br/>feature_columns_for" .-> train

    classDef code fill:#dbeafe,stroke:#2563eb,color:#111827
    classDef data fill:#fef9c3,stroke:#ca8a04,color:#111827
    classDef out fill:#dcfce7,stroke:#16a34a,color:#111827
    classDef side fill:#f3f4f6,stroke:#9ca3af,stroke-dasharray:4 3,color:#111827
    class crawl,clean,prep,train,analyze,eda,nbm,nbt code
    class raw,cleaned,processed,results,filtered data
    class docs,report out
    class filt,API side
```

## 2. Quy trình thực hiện theo đề bài

Các bước B1 đến B13 trong [flow.md](flow.md), nối theo thứ tự làm. "NV" là nhiệm vụ của đề bài (mục "Nhiệm vụ" ở trên). Cạnh nét đứt là bước tùy chọn hoặc vòng lặp so sánh.

```mermaid
flowchart TD
    B1["B1 · NV1<br/>Lý thuyết, phát biểu bài toán"]
    B2["B2 · NV2<br/>Thu thập dữ liệu"]
    B3["B3<br/>Làm sạch"]
    B4["B4<br/>Khảo sát dữ liệu (EDA)"]
    B5["B5 · NV2<br/>Đặc trưng và nhãn"]
    B6["B6 · NV3, NV4<br/>Huấn luyện mô hình ban đầu<br/>và baseline"]
    B7["B7 · NV4<br/>Phân tích kết quả, quá khớp,<br/>ma trận nhầm lẫn, feature importance"]
    B8["B8<br/>Cải tiến: nhóm đặc trưng,<br/>mất cân bằng, siêu tham số"]
    B9["B9<br/>Chọn mô hình cuối,<br/>đánh giá tổng quát hóa"]
    B10["B10 · NV3, NV4<br/>Backtest so với mua và nắm giữ"]
    B11["B11 · NV4<br/>Thảo luận giới hạn dự đoán giá"]
    B12["B12<br/>Thí nghiệm khung 1H (tùy chọn)"]
    B13["B13<br/>Hoàn thiện báo cáo,<br/>slide, cloud"]

    B1 --> B2 --> B3 --> B5 --> B6 --> B7 --> B8 --> B9 --> B10 --> B11 --> B13
    B2 --> B4 --> B5
    B8 -. "so sánh với B6<br/>(bảng ablation)" .-> B6
    B9 -.-> B12 -.-> B13

    classDef done fill:#dcfce7,stroke:#16a34a,color:#111827
    classDef part fill:#ffedd5,stroke:#ea580c,color:#111827
    classDef todo fill:#f3f4f6,stroke:#9ca3af,stroke-dasharray:4 3,color:#111827
    class B1,B2,B3,B4,B5,B6,B7,B8,B9,B10,B11,B12 done
    class B13 todo
```

## 3. Bên trong `train_models.py`

Chạy cho từng mã. Mọi thứ học từ dữ liệu (scaler, mô hình) chỉ được fit trên tập train của fold đang xét, nên khối test không bị rò rỉ.

```mermaid
flowchart TD
    start(["python scripts/train_models.py"])
    load["Đọc data/processed/KHUNG/MÃ.csv<br/>X = các cột đặc trưng<br/>y = label + 1 (0, 1, 2)<br/>r_next, time"]
    split["walk_forward_splits<br/>(hàm có sẵn trong preprocess_data.py)<br/>train đầu 750, test 63, gap 1"]

    subgraph FOLD["Với mỗi fold (20 đến 27 fold mỗi mã)"]
        direction TB
        build["build_models()<br/>tạo mô hình mới:<br/>majority, logistic, random_forest, xgboost"]
        fit["fit chỉ trên tập train của fold<br/>(StandardScaler trong Pipeline cũng vậy)"]
        proba["predict_proba trên khối test<br/>nhãn dự đoán = lớp có xác suất cao nhất"]
        score["Accuracy, F1 macro,<br/>ROC-AUC one-vs-rest"]
        rnd["Baseline ngẫu nhiên:<br/>rút nhãn theo tỷ lệ lớp của train,<br/>100 lần, lấy trung bình"]
        build --> fit --> proba --> score
        rnd --> score
    end

    concat["Ghép dự đoán của các khối test<br/>(liền nhau, không chồng lấn)"]
    bt["backtest() cho từng mô hình<br/>+ mua và nắm giữ<br/>+ ngẫu nhiên (100 lần rút)"]
    write["Ghi results/KHUNG/<br/>fold_metrics, predictions, backtest, summary"]

    start --> load --> split --> build
    score --> concat --> bt --> write

    classDef step fill:#dbeafe,stroke:#2563eb,color:#111827
    classDef out fill:#dcfce7,stroke:#16a34a,color:#111827
    class load,split,build,fit,proba,score,rnd,concat,bt step
    class write out
```

## 4. Chia dữ liệu walk-forward (khung 1D)

Cửa sổ train mở rộng dần, mỗi khối test dài 63 phiên và liền ngay khối trước. Phiên cuối của train bị bỏ vì nhãn của nó dùng giá đóng cửa của phiên test đầu tiên.

```text
Fold 1   [=========== train 750 ===========] gap [-- test 63 --]
Fold 2   [============== train 813 ==============] gap [-- test 63 --]
Fold 3   [================= train 876 =================] gap [-- test 63 --]
  ...
Fold N   [========================= train mở rộng =========================] gap [-- test 63 --]

         |---------------------------- thời gian ---------------------------->
```

Số fold: TCB 20, CTG 27, VNM 27, ACB 27. Siêu tham số (ở bước tinh chỉnh sắp tới) chỉ được chọn trên 20% cuối của tập train, không dùng khối test.

## 5. Quy tắc giao dịch của backtest

Quyết định cuối phiên `t` ăn lợi suất của phiên `t+1`. Chiến lược chỉ mua (long-only) vì thị trường Việt Nam không cho bán khống.

```mermaid
stateDiagram-v2
    direction LR
    state "Đứng ngoài thị trường" as Out
    state "Đang giữ cổ phiếu" as Hold

    [*] --> Out
    Out --> Hold: dự đoán tăng, mua, phí 0,15%
    Hold --> Out: dự đoán giảm, bán, phí 0,15% và thuế 0,1%
    Out --> Out: dự đoán giảm hoặc ngang
    Hold --> Hold: dự đoán tăng hoặc ngang
    Hold --> [*]: hết giai đoạn test, bán nốt
```
