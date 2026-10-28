"""Biên dịch và kiểm tra báo cáo LaTeX.

Cách dùng:
    python build.py <duong_dan/main.tex> [--render THU_MUC] [--pages 1-3]

- Chạy XeLaTeX 2 lần (đủ để cập nhật mục lục, danh mục, tham chiếu, bookmark).
- In: lỗi (!), tham chiếu/trích dẫn chưa định nghĩa, Overfull hbox > 5pt,
  số trang, cây bookmark của PDF (nếu có PyMuPDF), số đoạn \\huongdan và
  khung \\khunghinh còn sót.
- --render: xuất các trang chỉ định ra PNG (cần pdftoppm) để xem bằng mắt.
Mã thoát 1 nếu có lỗi biên dịch.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def chay_xelatex(tex: Path) -> int:
    lenh = ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name]
    ma = 0
    for _ in range(2):
        ma = subprocess.run(lenh, cwd=tex.parent, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode
        if ma != 0:
            break
    return ma


def doc_log(log: Path) -> dict:
    noi_dung = log.read_text(encoding="utf-8", errors="replace")
    loi = re.findall(r"^! .*(?:\n.*){0,2}", noi_dung, re.M)
    chua_dinh_nghia = sorted(set(re.findall(
        r"(?:Reference|Citation) `([^']+)' .*undefined", noi_dung)))
    tran = [(float(m.group(1)), m.group(2)) for m in re.finditer(
        r"Overfull \\hbox \(([\d.]+)pt too wide\) .*?lines? ([\d-]+)", noi_dung)]
    trang = re.search(r"Output written on .*?\((\d+) pages?", noi_dung)
    return {"loi": loi, "chua_dinh_nghia": chua_dinh_nghia,
            "tran": [t for t in tran if t[0] > 5],
            "so_trang": int(trang.group(1)) if trang else 0}


def in_bookmark(pdf: Path) -> None:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("  (bỏ qua: chưa cài PyMuPDF - pip install pymupdf)")
        return
    for cap, ten, trang in fitz.open(pdf).get_toc():
        print(f"  {'  ' * (cap - 1)}{ten}  [tr.{trang}]")


def main() -> int:
    # Console Windows mặc định cp1252 không in được tiếng Việt
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", type=Path)
    ap.add_argument("--render", type=Path, help="thư mục lưu ảnh PNG các trang")
    ap.add_argument("--pages", default="1-1", help="khoảng trang, ví dụ 1-3")
    ap.add_argument("--dpi", type=int, default=60)
    a = ap.parse_args()

    tex = a.tex.resolve()
    if shutil.which("xelatex") is None:
        print("Không tìm thấy xelatex (cài MiKTeX/TeX Live hoặc dùng Overleaf).")
        return 1

    ma = chay_xelatex(tex)
    kq = doc_log(tex.with_suffix(".log"))
    nguon = tex.read_text(encoding="utf-8")

    print(f"== Biên dịch: {'THÀNH CÔNG' if ma == 0 else 'LỖI'} "
          f"({kq['so_trang']} trang)")
    for l in kq["loi"]:
        print("  " + l.replace("\n", "\n  "))
    if kq["chua_dinh_nghia"]:
        print("== Tham chiếu/trích dẫn chưa định nghĩa:", ", ".join(kq["chua_dinh_nghia"]))
    if kq["tran"]:
        print("== Dòng tràn lề > 5pt (sửa trong .tex tại các dòng):")
        for rong, dong in kq["tran"]:
            print(f"  dòng {dong}: {rong:.1f}pt")
    con_hd = len(re.findall(r"^[^%\n]*\\huongdan\{", nguon, re.M))
    con_kh = len(re.findall(r"^[^%\n]*\\khunghinh\{", nguon, re.M))
    print(f"== Còn {con_hd} đoạn \\huongdan và {con_kh} khung \\khunghinh chưa thay")

    pdf = tex.with_suffix(".pdf")
    if ma == 0 and pdf.exists():
        print("== Bookmark PDF:")
        in_bookmark(pdf)
        if a.render:
            if shutil.which("pdftoppm") is None:
                print("  (bỏ qua render: không có pdftoppm)")
            else:
                a.render.mkdir(parents=True, exist_ok=True)
                dau, _, cuoi = a.pages.partition("-")
                subprocess.run(["pdftoppm", "-r", str(a.dpi), "-png",
                                "-f", dau, "-l", cuoi or dau, str(pdf),
                                str(a.render / "trang")], check=False)
                print(f"== Ảnh trang đã lưu tại: {a.render}")
    return 0 if ma == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
