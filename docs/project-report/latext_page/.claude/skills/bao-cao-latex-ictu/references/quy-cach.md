# Quy cách trình bày và các lệnh của mẫu

Mẫu gốc `latext_page/Mau bao cao mon Hoc may.tex` đã cài sẵn toàn bộ quy cách dưới
đây. Đọc file này khi cần chuẩn hóa một báo cáo có sẵn (để biết phải đưa nó về
đâu) hoặc khi sinh viên hỏi vì sao trình bày như vậy.

## Mục lục
1. Trang giấy, phông chữ
2. Tiêu đề và đánh số
3. Hình, bảng, công thức, mã nguồn
4. Trang đầu và đánh số trang
5. Tài liệu tham khảo
6. Các lệnh tiện ích của mẫu
7. Các lỗi đã gặp và cách sửa

## 1. Trang giấy, phông chữ
- A4, lề trái 3 cm, phải 2 cm, trên 2,5 cm, dưới 2,5 cm.
- Times New Roman 13pt thân bài (lớp `report` 12pt, `\normalsize` định nghĩa lại
  thành 13pt), giãn dòng `\setstretch{1.3}` (tương đương 1,5 dòng của Word),
  thụt đầu dòng 1 cm, cách đoạn 6pt.
- Biên dịch bằng **XeLaTeX** (cần `fontspec` cho tiếng Việt và Times New Roman).
  pdfLaTeX sẽ lỗi.

## 2. Tiêu đề và đánh số
| Cấp | Định dạng | Ví dụ |
|---|---|---|
| Chương | 14pt, đậm, căn giữa, IN HOA, hai dòng | CHƯƠNG 1 / TỔNG QUAN… |
| Mục 2 | 14pt, đậm | 1.1. Giới thiệu |
| Mục 3 | 13pt, đậm | 1.1.1. Mục |
| Mục 4 | 13pt, đậm nghiêng | 1.1.1.1. Mục |

- Mục lục ghi "Chương 1." trước tên chương, phụ lục ghi "Phụ lục A.".
- Bookmark PDF có số: "Chương 1. …", "1.1. …", "Phụ lục A. …" (do đoạn định nghĩa
  lại `\Hy@writebookmark`/`\Hy@numberline` sau `\hypersetup`).
- Mục không đánh số (Mở đầu, Kết luận…) dùng `\unnumberedchapter{...}`, vẫn vào
  mục lục, bookmark và đầu trang. Mục con trong đó dùng `\section*{1. ...}`.
- Đầu trang: trái "Báo cáo tiểu luận học phần …", phải tên chương; trang mở
  chương không có đầu trang.

## 3. Hình, bảng, công thức, mã nguồn
- Hình và bảng đánh số theo chương: Hình 2.1, Bảng 3.2. Nhãn in đậm, dấu chấm:
  "**Hình 2.1.** Phân bố nhãn…".
- **Tên bảng đặt trên bảng, tên hình đặt dưới hình.** Mọi hình/bảng phải được
  nhắc trong văn bản bằng `\ref` trước khi xuất hiện, và hình EDA/kết quả phải
  có đoạn *Nhận xét* ngay sau (tiêu chí chấm trừ điểm nếu thiếu).
- Dùng `[H]` (gói `float`) để hình/bảng nằm đúng chỗ.
- Bảng: kiểu `booktabs` (`\toprule \midrule \bottomrule`, không kẻ dọc) cho bảng
  số liệu; `tabularx` với cột `X` khi có cột văn bản dài. Số thập phân dùng dấu
  phẩy trong môi trường toán: `$0{,}85$`. Kết quả kiểm định chéo ghi dạng
  `$0{,}812 \pm 0{,}015$`.
- Công thức đánh số theo chương bằng `equation`, có `\label` và được giải thích
  ký hiệu.
- Mã nguồn: môi trường `lstlisting` với style `python` sẵn có, có
  `caption` + `label`, tên gọi "Đoạn mã 3.1". Chỉ đưa đoạn mã then chốt (≤ 30
  dòng); mã đầy đủ để ở kho Git/phụ lục.

## 4. Trang đầu và đánh số trang
Thứ tự: Bìa (không số) → Nhận xét của giảng viên → Lời cam đoan (có khai báo
dùng AI) → Lời cảm ơn → Bảng phân công nhiệm vụ → Mục lục → Danh mục hình →
Danh mục bảng → Danh mục từ viết tắt. Các trang này đánh số La Mã (i, ii…),
phần nội dung từ Mở đầu đánh số 1, 2, 3….

## 5. Tài liệu tham khảo
- Dùng `thebibliography` + gói `cite` (trích dẫn gộp [2, 4–6]).
- Thứ tự: tiếng Việt trước, tiếng nước ngoài sau; trong mỗi nhóm xếp ABC theo
  tên (Việt) hoặc họ (nước ngoài) tác giả. Số thứ tự [n] theo thứ tự trong danh
  mục, không theo thứ tự trích dẫn.
- Mẫu mục: `Tác giả (năm), ``Tên bài'', \textit{Tên tạp chí/kỷ yếu}, tập(số), tr. x--y.`
  Tiếng Anh dùng `vol.`, `no.`, `pp.`.
- Mỗi `\bibitem` phải được `\cite` ít nhất một lần trong bài và ngược lại.
- Không bịa thông tin tài liệu. Nếu thiếu năm/trang, để nguyên phần đã biết và
  báo cho người dùng bổ sung.

## 6. Các lệnh tiện ích của mẫu
| Lệnh | Tác dụng |
|---|---|
| Khối (A) đầu file: `\tendetai`, `\tenbaitoan` (tên bài toán trong tên Chương 1 và 2), `\giangvien`, `\nhom`, `\svAten`, `\svAma`, `\svBten`, `\svBma`, `\lophocphan`, `\hocky`, `\diadiem`, `\thoigian`, `\truong`, `\khoa`, `\hocphan`, `\loaibaocao` | Thông tin dùng chung cho bìa, cam đoan, nhận xét, phân công, PDF metadata |
| `\unnumberedchapter{TÊN}` | Chương không số nhưng có trong mục lục |
| `\huongdan{...}` | Chữ xám nghiêng gợi ý nội dung — xóa khi đã viết |
| `\khunghinh{rộng}{cao}{chữ}` | Khung giữ chỗ cho hình — thay bằng `\includegraphics` |
| `\dongcham{n}` | n dòng chấm (trang nhận xét) |
| Logo bìa | Tự dùng `images/logo.png` nếu có, không thì hiện khung giữ chỗ |

Nhóm 3 sinh viên: thêm `\svCten`, `\svCma` ở khối (A), thêm một dòng ở bìa,
bảng điểm trang nhận xét, chữ ký lời cam đoan và bảng phân công.

## 7. Các lỗi đã gặp và cách sửa
- **Tên trường dài bị xuống dòng/lệch trái trên bìa:** dòng đầu tiên sau
  `tikzpicture` overlay nằm chung đoạn với nó — cần `\par\vspace*{-\baselineskip}`
  sau `\end{tikzpicture}` (đã có trong mẫu); giảm cỡ chữ còn 13pt nếu vẫn tràn.
- **Text trong `\khunghinh` tràn lề:** chuỗi dài không ngắt được (đường dẫn
  file) — viết ngắn, dùng `\\` để xuống dòng.
- **Trang nhận xét tràn sang trang sau:** giảm số dòng `\dongcham`.
- **Bookmark chỉ có số mà không có "Chương":** kiểm tra theo cấp (`#4=0`), không
  theo kiểu (`#5` là tên file `toc`).
- **Tên file có dấu cách** (ví dụ `Mau bao cao mon Hoc may.tex`): XeLaTeX của
  MiKTeX/TeX Live xử lý được khi đặt trong dấu nháy; trên Overleaf cũng được.
- **Console Windows báo `UnicodeEncodeError`** khi in tiếng Việt từ Python: đặt
  `PYTHONIOENCODING=utf8` hoặc dùng `scripts/build.py` (đã tự xử lý).
- **Tên "Đoạn mã" nằm cuối trang, khung mã sang trang sau:** đặt
  `\needspace{8\baselineskip}` ngay trước `lstlisting` (gói `needspace` đã nạp).
- **Sơ đồ TikZ có đường cắt qua khối/nhãn:** đặt khối nằm ngoài vùng `fit`
  (ví dụ "Tập kiểm tra" ở x = 7,6 cm trong Hình 2.1), rút ngắn nhãn của khung
  `fit`, rồi render trang ra ảnh để kiểm tra bằng mắt.
