"""Chấm các run trong iteration: python grade.py <iteration_dir>"""
import json
import re
import sys
import pathlib
import fitz

sys.stdout.reconfigure(encoding="utf-8")
IT = pathlib.Path(sys.argv[1])


def pdf_info(out):
    pdfs = sorted(out.glob("*.pdf"))
    if not pdfs:
        return None, "", [], []
    doc = fitz.open(pdfs[0])
    text = "\n".join(p.get_text() for p in doc)
    labels = [doc[i].get_label() or str(i + 1) for i in range(len(doc))]
    return pdfs[0], text, doc.get_toc(), labels


def main_tex(out):
    texs = [t for t in out.glob("*.tex")]
    return max(texs, key=lambda t: t.stat().st_size) if texs else None


def log_ok(tex):
    log = tex.with_suffix(".log") if tex else None
    if not log or not log.exists():
        return False, "không có file .log"
    s = log.read_text(encoding="utf-8", errors="replace")
    errs = re.findall(r"^! .*", s, re.M)
    return (not errs and "Output written" in s), (errs[:2] or "log sạch, có Output written")


def co(text, *ws):
    t = text.lower()
    return all(w.lower() in t for w in ws)


def bm_numbered(toc):
    return any(re.match(r"^(Chương\s*)?1[.\s]", t) for _, t, _ in toc) and \
        any(re.match(r"^1\.1[.\s]", t) for _, t, _ in toc)


def front(text):
    miss = [w for w in ["cam đoan", "cảm ơn", "mục lục", "danh mục hình", "danh mục bảng"]
            if w not in text.lower()]
    return not miss, f"thiếu: {miss}" if miss else "có đủ 5 phần"


def roman(labels):
    has_r = any(re.fullmatch(r"[ivxl]+", l) for l in labels)
    has_a = any(l == "1" for l in labels)
    return has_r and has_a, f"nhãn trang: {labels[:4]}...{labels[-2:]}"


def grade_chuan_hoa(out):
    pdf, text, toc, labels = pdf_info(out)
    tex = main_tex(out)
    src = tex.read_text(encoding="utf-8", errors="replace") if tex else ""
    r = []
    ok, ev = log_ok(tex)
    r.append((ok and pdf is not None, f"{tex.name if tex else '-'}: {ev}"))
    r.append((co(text, "báo cáo") and ("trường" in text.lower()), "tìm 'báo cáo' và 'trường' trong PDF"))
    r.append(front(text))
    keys = ["alquraishi2021", "lananh", "tuananh2024", "hai2017", "thuan2022", "thuy2023"]
    bib = [k for k in keys if re.search(r"\\bibitem(\[[^\]]*\])?\{" + k + r"\}", src)]
    cited = [k for k in keys if re.search(r"\\cite[a-z]*\{[^}]*\b" + k + r"\b", src)]
    r.append((len(bib) == 6 and len(cited) == 6, f"bibitem {len(bib)}/6, được cite {len(cited)}/6"))
    r.append(("Random Forest là mô hình tối ưu" in src and "43,70" in src, "tìm câu Random Forest và 43,70 trong .tex"))
    imgs = [i for i in ["image1", "image2", "image3"] if i in src]
    r.append((len(imgs) == 3, f"hình giữ lại: {imgs}"))
    r.append(roman(labels) if labels else (False, "không có PDF"))
    r.append((bm_numbered(toc), f"bookmark đầu: {[t for _, t, _ in toc][:6]}"))
    return r


def grade_khai_pha(out):
    pdf, text, toc, labels = pdf_info(out)
    tex = out / "Mau bao cao mon Khai pha du lieu.tex"
    r = []
    ok, ev = log_ok(tex if tex.exists() else None)
    r.append((tex.exists() and (out / "Mau bao cao mon Khai pha du lieu.pdf").exists() and ok, str(ev)))
    first = "\n".join(text.split("\n")[:60])
    hk = re.search(r"(học kỳ|HỌC KỲ)\s*(2|II)", text) and "2026" in text and "2027" in text
    r.append((co(text, "khai phá dữ liệu") and "K23" in text and bool(hk), "bìa/khối thông tin: Khai phá dữ liệu, K23, HK2 2026-2027"))
    r.append(front(text))
    hp_hocmay = re.search(r"học phần:?\s*học máy", text, re.I)
    r.append((not hp_hocmay and co(text, "khai phá"), "không còn 'Học phần: Học máy'; chương nhắc khai phá"))
    src = tex.read_text(encoding="utf-8", errors="replace") if tex.exists() else ""
    placeholder = bool(re.search(r"Nguyễn Văn A|xxxx|\\dots|\.\.\.", src))
    guide = bool(re.search(r"hướng dẫn|huongdan", src, re.I))
    r.append((placeholder and guide, f"giữ chỗ={placeholder}, hướng dẫn={guide} (cần đọc thêm để chắc không bịa số liệu)"))
    r.append((bm_numbered(toc), f"bookmark đầu: {[t for _, t, _ in toc][:6]}"))
    return r


GRADERS = {"chuan-hoa-file-tex-cu": grade_chuan_hoa, "mau-cho-hoc-phan-khac": grade_khai_pha}
for case, fn in GRADERS.items():
    if not (IT / case).exists():
        continue
    meta = json.loads((IT / case / "eval_metadata.json").read_text(encoding="utf-8"))
    for cfg in ["with_skill", "without_skill"]:
        run = IT / case / cfg
        if not (run / "outputs").exists():
            continue
        res = fn(run / "outputs")
        exp = [{"text": a, "passed": bool(p), "evidence": str(e)} for a, (p, e) in zip(meta["assertions"], res)]
        n = sum(e["passed"] for e in exp)
        (run / "grading.json").write_text(json.dumps({
            "expectations": exp,
            "summary": {"passed": n, "failed": len(exp) - n, "total": len(exp),
                        "pass_rate": round(n / len(exp), 3)}}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{case}/{cfg}: {n}/{len(exp)}")
        for e in exp:
            print(f"   {'✔' if e['passed'] else '✘'} {e['text'][:70]} | {e['evidence'][:110]}")
