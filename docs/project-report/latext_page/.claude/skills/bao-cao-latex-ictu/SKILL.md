---
name: bao-cao-latex-ictu
description: Tạo, chuẩn hóa và chỉnh sửa MẪU báo cáo môn học / tiểu luận của sinh viên bằng LaTeX (XeLaTeX) cho học phần Học máy theo quy cách của bộ môn KHMT – ICTU. Dùng skill này bất cứ khi nào người dùng (thường là giảng viên) muốn tạo mẫu báo cáo LaTeX môn Học máy cho sinh viên, chuẩn hóa một file .tex mẫu cho "chuyên nghiệp, đủ thành phần", thêm/bớt mục trong mẫu (bìa, lời cam đoan, mục lục, danh mục hình/bảng, bookmark, phụ lục), sửa lỗi trình bày của mẫu, hay đối chiếu mẫu với bộ tiêu chí chấm — kể cả khi họ chỉ nói "mẫu báo cáo môn học", "chuẩn hóa file tex", "report template", "latex template for students".
---

# Mẫu báo cáo môn Học máy (LaTeX) theo quy cách ICTU

Sản phẩm của skill là **một bản mẫu** để phát cho sinh viên, không phải báo cáo
của một nhóm cụ thể. Mẫu chứa khung đầy đủ thành phần với **3 chương** (Tổng quan về học máy và
bài toán `\tenbaitoan`; Mô hình hóa bài toán và phương pháp `\tenbaitoan`; Thực nghiệm và đánh
giá — phần dữ liệu nằm ở đầu Chương 3), thông tin giữ chỗ
(`Nguyễn Văn A`, `DTC22xxxxxxxx`, `\dots`), các đoạn gợi ý `\huongdan{...}` cho
sinh viên biết cần viết gì, và khung `\khunghinh{...}` ở chỗ cần đặt hình.

Skill nằm trong thư mục `latext_page/.claude/skills/bao-cao-latex-ictu/`.
**Bản mẫu gốc (duy nhất) là file `latext_page/Mau bao cao mon Hoc may.tex`**
cùng thư mục `latext_page/images/` — tức `../../../` tính từ thư mục skill.
Mọi chỉnh sửa mẫu làm trực tiếp trên file đó; không tạo bản sao mẫu bên trong
skill để tránh hai bản lệch nhau. Script biên dịch + kiểm tra nằm ở
`scripts/build.py` của skill. Luôn bắt đầu từ mẫu này thay vì
viết preamble từ đầu: nó đã giải quyết sẵn phông tiếng Việt, đánh số trang
La Mã/Ả Rập, mục lục, bookmark có số chương và các lỗi bố cục khó thấy.

## Tài liệu kèm theo — đọc khi cần
- `references/quy-cach.md`: quy cách trình bày (lề, phông, tiêu đề, hình/bảng,
  tài liệu tham khảo), các lệnh tiện ích của mẫu, các lỗi đã gặp và cách sửa.
  Đọc khi chuẩn hóa một file khác hoặc khi gặp lỗi bố cục.
- `references/cau-truc-tieu-chi.md`: ánh xạ các mục Chương 2–3 với bộ tiêu chí
  chấm 4 mốc của học phần Học máy. Đọc khi sửa cấu trúc chương hoặc viết lại
  các đoạn `\huongdan`.

## Xác định tình huống

Skill chỉ dành cho học phần **Học máy**: giữ nguyên tên học phần, cấu trúc
3 chương và các đoạn hướng dẫn bám theo bộ tiêu chí chấm Học máy.

1. **Tạo bản mẫu mới** (bản cho lớp/khóa khác): sao chép file mẫu gốc và
   thư mục `images/` tới nơi người dùng chỉ định. Chỉ đổi những gì họ yêu cầu (tên trường/khoa,
   lớp, học kỳ, tên file…) — sửa ở khối **(A) THÔNG TIN BÁO CÁO** đầu
   file để bìa, cam đoan, trang nhận xét tự cập nhật.
2. **Chuẩn hóa một file .tex mẫu có sẵn**: đọc hết file cũ trước. Lấy mẫu làm
   khung, chuyển nội dung cũ (đoạn hướng dẫn, ví dụ hình/bảng, công thức,
   `\bibitem` và các `\cite` đi kèm) vào mục tương ứng, giữ `\label`/`\cite` để
   tham chiếu không gãy; phần nào không khớp mục nào thì giữ ở mục gần nhất
   thay vì xóa. Chỉ ghi đè file gốc khi người dùng đồng ý hoặc file đã nằm
   trong git; nếu không, ghi ra file mới.
3. **Sửa/thêm/bớt thành phần của mẫu** (thêm nhóm 3 sinh viên, đổi thứ tự
   trang đầu, bỏ một dòng trên bìa…): sửa trực tiếp, rồi xem lại trang bị ảnh
   hưởng — xóa một dòng có thể làm dòng khác xuống dòng xấu.
4. **Kiểm tra**: chạy `scripts/build.py`, đối chiếu `references/quy-cach.md`.

## Nguyên tắc cho một bản mẫu

- Đây là mẫu, nên **không điền nội dung, số liệu hay kết quả của một đề tài cụ
  thể**. Ô số liệu để `\dots`; thông tin sinh viên để giữ chỗ; đoạn cần viết để
  `\huongdan{...}`. Ví dụ minh họa (dòng mẫu trong bảng từ điển dữ liệu, đoạn mã
  Pipeline) được phép, miễn là rõ ràng là ví dụ.
- Đoạn `\huongdan{...}` nên nói cụ thể sinh viên phải viết gì và tiêu chí chấm
  đòi hỏi gì (ví dụ "định lượng số giá trị thiếu, không chỉ nêu có thiếu") —
  đó là giá trị chính của mẫu đối với sinh viên.
- Không bịa tài liệu tham khảo. Giữ các tài liệu có sẵn; nếu thêm mới thì chỉ
  thêm tài liệu kinh điển mà bạn chắc chắn thông tin (tác giả, năm, nơi đăng,
  trang), và nói cho người dùng biết đã thêm gì.
- Sinh viên áp dụng lại các phương pháp đã có, không đề xuất phương pháp mới,
  nên tên chương, mục và đoạn hướng dẫn tránh chữ "đề xuất"/"phương pháp mới"
  cho phần việc của nhóm (dùng "phương pháp giải quyết", "áp dụng", "lựa
  chọn"). "Đề xuất" chỉ dùng khi nói về công trình của tác giả khác được trích.
- Mọi hình/bảng ví dụ có `\caption` + `\label` và được `\ref` trong văn bản,
  để sinh viên học theo đúng cách.

## Biên dịch và kiểm tra (luôn làm trước khi báo xong)

```bash
python latext_page/.claude/skills/bao-cao-latex-ictu/scripts/build.py "latext_page/Mau bao cao mon Hoc may.tex" \
       --render <thu_muc_tam> --pages 1-3
```

Script chạy XeLaTeX hai lần rồi in: lỗi biên dịch, tham chiếu/trích dẫn chưa
định nghĩa, dòng tràn lề > 5pt, số `\huongdan`/`\khunghinh` trong file, và cây
bookmark của PDF; `--render` xuất trang ra PNG. Với một bản mẫu, việc còn nhiều
`\huongdan`/`\khunghinh` là bình thường. Sau đó:

1. Sửa hết lỗi và tham chiếu chưa định nghĩa.
2. Xem ảnh trang bìa, trang nhận xét và vài trang có hình/bảng bằng công cụ
   đọc ảnh — log không bắt được lỗi như tên trường xuống dòng xấu, trang nhận
   xét tràn sang trang sau, bảng lệch.
3. Kiểm tra bookmark có dạng "Chương 1. …", "1.1. …", "Phụ lục A. …".

Không có `xelatex` trên máy: nói rõ với người dùng, gợi ý cài MiKTeX/TeX Live
hoặc tải lên Overleaf (Menu → Compiler → XeLaTeX); vẫn bàn giao file .tex.

## Bàn giao

Báo cáo ngắn: file nào đã tạo/sửa (đường dẫn dạng link), kết quả biên dịch (số
trang, cảnh báo còn lại), những gì đã thay đổi so với mẫu gốc, và những gì
người dùng nên tự kiểm tra (tên khoa, học hàm học vị, logo `images/logo.png`).
Không tự commit/push trừ khi được yêu cầu.

## Dữ liệu thử nghiệm của skill

- `evals/`: các tình huống thử (đề bài, tiêu chí kiểm tra, file đầu vào).
- `../bao-cao-latex-ictu-workspace/`: kết quả các lần chạy thử theo vòng
  (`iteration-N/`), điểm chấm, `benchmark.md`, script chấm `grade.py`
  (`python grade.py iteration-N`) và trang so sánh `review.html`.
