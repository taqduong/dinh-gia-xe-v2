"""Dựng báo cáo Word (DOCX) và PDF từ kết quả thực nghiệm, ảnh giao diện và mã nguồn thực tế.

Chạy từ thư mục gốc (sau khi đã chạy thực nghiệm, vẽ biểu đồ và chụp ảnh):
    python scripts/build_report.py            # tạo DOCX + PDF (cần LibreOffice để xuất PDF và đánh số trang mục lục)
    python scripts/build_report.py --no-pdf   # chỉ tạo DOCX (số trang trong mục lục để 0; mở Word → Update Field)

Quy trình: dựng DOCX → xuất PDF bằng LibreOffice → đọc số trang của tiêu đề/hình/bảng trong PDF →
dựng lại DOCX với mục lục có số trang → xuất PDF lần cuối và kiểm tra số trang không đổi.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

from carval.formatting import fmt_so  # noqa: E402
from carval.kb import KnowledgeBase  # noqa: E402
from report_docx import O, T, V, BaoCao, chen_sectpr, frac, nary, ngoac, omath, sub, sup  # noqa: E402

RES = ROOT / "outputs" / "results"
CHARTS = ROOT / "outputs" / "charts"
SHOTS = ROOT / "outputs" / "screenshots"
OUT = ROOT / "outputs" / "report"
ASSET = OUT / "_assets"
TEN = "BaoCao_KBDSS_DinhGiaXeCu_Nhom4"


# ------------------------------------------------------------------ dữ liệu đầu vào
def doc_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


KB = KnowledgeBase.tu_thu_muc()
CFG = KB.config
M = doc_json(RES / "metrics.json")
DEMO = {d["id"]: d for d in doc_json(RES / "demo_cases.json")}
TUNE = doc_json(RES / "tuning_summary.json")
CLEAN = doc_json(ROOT / "data" / "processed" / "cleaning_log.json")
GEN = doc_json(ROOT / "data" / "raw" / "generation_log.json")
GCFG = doc_json(ROOT / "data" / "generator_config.json")
ENV = doc_json(RES / "environment.json")
BY_GROUP = pd.read_csv(RES / "metrics_by_group.csv")
BY_CONF = pd.read_csv(RES / "metrics_by_confidence.csv")
SAME = pd.read_csv(RES / "metrics_same_subset.csv")
TIMING = pd.read_csv(RES / "timing.csv")
TEST_LOG = (RES / "test_report.txt").read_text(encoding="utf-8") if (RES / "test_report.txt").exists() else ""
BANG = {d["phuong_phap"]: d for d in M["bang_chinh"]}
PP = ["Chỉ luật", "Chỉ CBR", "Random Forest", "Hệ lai luật + CBR"]


def f(x, n=1):
    return fmt_so(x, n)


def pt(x, n=1):
    return fmt_so(x, n) + "%"


# ------------------------------------------------------------------ trích mã nguồn thật
def trich(tep: str, ten: str, tu: str | None = None, den: str | None = None, lop: str | None = None) -> tuple[list[str], int]:
    """Trích nguyên văn mã của hàm/phương thức `ten` (có thể cắt từ dòng chứa `tu` đến dòng chứa `den`)."""
    path = ROOT / tep
    src = path.read_text(encoding="utf-8")
    dong = src.splitlines()
    cay = ast.parse(src)
    nut = None
    for n in ast.walk(cay):
        if isinstance(n, ast.ClassDef) and lop and n.name == lop:
            for c in n.body:
                if isinstance(c, ast.FunctionDef) and c.name == ten:
                    nut = c
        elif isinstance(n, ast.FunctionDef) and n.name == ten and not lop:
            nut = n
    if nut is None:
        raise KeyError(f"Không tìm thấy {ten} trong {tep}")
    a, b = nut.lineno, nut.end_lineno
    if nut.decorator_list:
        a = nut.decorator_list[0].lineno
    if tu:
        a = next(i for i in range(a, b + 1) if tu in dong[i - 1])
    if den:
        b = next(i for i in range(a, b + 1) if den in dong[i - 1])
    doan = dong[a - 1:b]
    lui = min(len(x) - len(x.lstrip()) for x in doan if x.strip())
    return [x[lui:] for x in doan], a


def trich_json_luat(ma: str) -> tuple[list[str], int]:
    dong = (ROOT / "kb" / "rules.json").read_text(encoding="utf-8").splitlines()
    a = next(i for i, x in enumerate(dong) if f'"id": "{ma}"' in x)
    while not dong[a].strip().startswith("{"):
        a -= 1
    lui = len(dong[a]) - len(dong[a].lstrip())
    b = next(i for i in range(a + 1, len(dong)) if dong[i].startswith(" " * lui + "}"))
    return [x[lui:] for x in dong[a:b + 1]], a + 1


# ------------------------------------------------------------------ ảnh (thu nhỏ để DOCX gọn)
def _cat_menu(im: Image.Image) -> Image.Image:
    """Bỏ thanh menu bên trái và lề nền hai bên của ảnh chụp toàn trang để chữ lớn hơn khi in."""
    import numpy as np
    a = np.asarray(im).astype(int)
    nen = np.array([245, 247, 251])
    x0 = int(im.width * 300 / 1440)                 # thanh menu Streamlit rộng 300 px CSS ở khung 1440 px
    khac = (np.abs(a[:, x0 + 10:, :] - nen).sum(axis=2) > 30).any(axis=0)
    cot = np.nonzero(khac)[0]
    if len(cot) == 0:
        return im
    trai = max(x0, x0 + 10 + int(cot[0]) - 24)
    phai = min(im.width, x0 + 10 + int(cot[-1]) + 24)
    return im.crop((trai, 0, phai, im.height))


def anh(p: Path, rong_px: int = 1900, cat_menu: bool = False) -> Path:
    ASSET.mkdir(parents=True, exist_ok=True)
    dich = ASSET / (p.stem + ("_cat" if cat_menu else "") + p.suffix)
    if not dich.exists() or dich.stat().st_mtime < p.stat().st_mtime:
        with Image.open(p) as im:
            im = im.convert("RGB")
            if cat_menu:
                im = _cat_menu(im)
            if im.width > rong_px:
                im = im.resize((rong_px, round(im.height * rong_px / im.width)), Image.LANCZOS)
            im.save(dich, optimize=True)
    return dich


# ------------------------------------------------------------------ nội dung
def bia(bc: BaoCao):
    d = bc.doc
    s = d.sections[0]
    pb = OxmlElement("w:pgBorders")
    pb.set(qn("w:offsetFrom"), "page")
    for canh in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{canh}")
        e.set(qn("w:val"), "double")
        e.set(qn("w:sz"), "6")
        e.set(qn("w:space"), "24")
        e.set(qn("w:color"), "1F3B73")
        pb.append(e)
    chen_sectpr(s._sectPr, pb)

    def dong(text, co=13, dam=False, nghieng=False, sau=4, mau=None, hoa=False):
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(sau)
        p.paragraph_format.line_spacing = 1.15
        r = p.add_run(text.upper() if hoa else text)
        r.bold, r.italic = dam, nghieng
        r.font.size = Pt(co)
        if mau:
            r.font.color.rgb = RGBColor.from_string(mau)
        return p

    dong("BỘ CÔNG THƯƠNG", 13, True, sau=0)
    dong("TRƯỜNG ĐẠI HỌC CÔNG NGHIỆP HÀ NỘI", 14, True, sau=0)
    dong("[Điền tên Khoa/Trường thành viên]", 13, False, True, sau=2, mau="7F7F7F")
    dong("――――――――――――", 13, sau=36)
    dong("[Vị trí chèn logo trường]", 11, False, True, sau=40, mau="9F9F9F")
    dong("BÁO CÁO BÀI TẬP LỚN", 18, True, sau=6)
    dong("HỌC PHẦN: CÔNG NGHỆ TRI THỨC", 15, True, sau=30)
    dong("ĐỀ TÀI", 13, True, sau=6)
    dong("HỆ HỖ TRỢ QUYẾT ĐỊNH DỰA TRÊN TRI THỨC", 17, True, sau=0, mau="1F3B73")
    dong("CHO ĐỊNH GIÁ XE Ô TÔ CŨ", 17, True, sau=0, mau="1F3B73")
    dong("TẠI THỊ TRƯỜNG VIỆT NAM", 17, True, sau=36, mau="1F3B73")
    for nhan, gt in (("Giảng viên hướng dẫn:", "[Điền họ tên, học hàm/học vị giảng viên]"),
                     ("Lớp học phần:", "[Điền mã lớp học phần]"), ("Nhóm thực hiện:", "Nhóm 4")):
        p = d.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(2.2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(nhan + " ")
        r.bold = True
        r2 = p.add_run(gt)
        if gt.startswith("["):
            r2.italic = True
            r2.font.color.rgb = RGBColor.from_string("7F7F7F")
    sp = d.add_paragraph()
    sp.paragraph_format.space_after = Pt(4)
    t = d.add_table(rows=5, cols=3)
    t.style = "Table Grid"
    t.alignment = 1
    rong = [1.4, 7.0, 4.2]
    for i, row in enumerate([["STT", "Họ và tên", "Mã sinh viên"]] +
                            [[str(k), f"[Họ và tên thành viên {k}]", "[Mã sinh viên]"] for k in range(1, 5)]):
        for j, v in enumerate(row):
            o = t.rows[i].cells[j]
            o.width = Cm(rong[j])
            p = o.paragraphs[0]
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j != 1 else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(v)
            r.font.size = Pt(12)
            r.bold = i == 0
            if v.startswith("["):
                r.italic = True
                r.font.color.rgb = RGBColor.from_string("7F7F7F")
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), rong):
        gc.set(qn("w:w"), str(int(w * 567)))
    dong("", sau=40)
    dong("Hà Nội, tháng 11 năm 2026", 13, False, True, sau=0)


def phan_dau(bc: BaoCao):
    bc.phan_moi("lowerRoman", 1)
    bc.tieu_de_phu("Mục lục")
    bc.danh_muc({"h1", "h2", "h3"}, ' TOC \\o "1-3" \\h \\z \\u ')
    bc.ngat_trang()
    bc.tieu_de_phu("Danh mục hình")
    bc.danh_muc({"hinh"}, ' TOC \\h \\z \\t "Chu thich hinh,1" ')
    bc.ngat_trang()
    bc.tieu_de_phu("Danh mục bảng")
    bc.danh_muc({"bang"}, ' TOC \\h \\z \\t "Chu thich bang,1" ')
    bc.ngat_trang()
    bc.tieu_de_phu("Danh mục từ viết tắt")
    viet_tat = [
        ["Từ viết tắt", "Tiếng Anh", "Ý nghĩa"],
        ["AT / CVT / MT", "Automatic / Continuously Variable / Manual Transmission", "Hộp số tự động / vô cấp / số sàn"],
        ["CBR", "Case-Based Reasoning", "Lập luận dựa trên tình huống"],
        ["CSTT", "—", "Cơ sở tri thức"],
        ["CV", "Coefficient of Variation", "Hệ số biến thiên"],
        ["DSS", "Decision Support System", "Hệ hỗ trợ quyết định"],
        ["IQR", "Interquartile Range", "Khoảng tứ phân vị"],
        ["KB-DSS", "Knowledge-Based Decision Support System", "Hệ hỗ trợ quyết định dựa trên tri thức"],
        ["MAE", "Mean Absolute Error", "Sai số tuyệt đối trung bình"],
        ["MAPE", "Mean Absolute Percentage Error", "Sai số phần trăm tuyệt đối trung bình"],
        ["MPV / SUV", "Multi-Purpose / Sport Utility Vehicle", "Xe đa dụng / xe thể thao đa dụng"],
        ["ODO", "Odometer", "Đồng hồ đo quãng đường (số km)"],
        ["R²", "Coefficient of determination", "Hệ số xác định"],
        ["RF", "Random Forest", "Rừng ngẫu nhiên"],
        ["Sim", "Similarity", "Độ tương tự"],
        ["WM", "Working Memory", "Bộ nhớ làm việc của máy suy diễn"],
    ]
    t = bc.doc.add_table(rows=len(viet_tat), cols=3)
    t.style = "Table Grid"
    t.alignment = 1
    rong = [3.2, 6.4, 6.4]
    for i, row in enumerate(viet_tat):
        for j, v in enumerate(row):
            o = t.rows[i].cells[j]
            o.width = Cm(rong[j])
            p = o.paragraphs[0]
            p.style = "Bang noi dung"
            r = p.add_run(v)
            r.bold = i == 0
            if i == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), rong):
        gc.set(qn("w:w"), str(int(w * 567)))


def mo_dau(bc: BaoCao):
    bc.phan_moi("decimal", 1)
    bc.tieu_de("MỞ ĐẦU", 1)
    bc.tieu_de("1. Lý do chọn đề tài", 2)
    bc.doan("Thị trường xe ô tô đã qua sử dụng tại Việt Nam có số lượng giao dịch lớn nhưng giá cả thiếu minh bạch. "
            "Cùng một dòng xe, giá rao có thể chênh lệch hàng chục triệu đồng do khác biệt về đời xe, số km, tình trạng, "
            "lịch sử bảo dưỡng hay các rủi ro khó phát hiện như ngập nước, tai nạn. Người mua thường thiếu kinh nghiệm "
            "để định giá, còn người bán dựa vào cảm tính hoặc giá rao của tin khác. Một hệ thống vừa đưa ra giá tham khảo, "
            "vừa *giải thích được* vì sao có mức giá đó sẽ giúp hai bên ra quyết định có căn cứ hơn.")
    bc.doan("Bài toán này phù hợp với học phần Công nghệ tri thức vì tri thức định giá của chuyên gia (khấu hao theo tuổi, "
            "điều chỉnh theo km, tình trạng, rủi ro) có thể biểu diễn tường minh bằng khung và luật sản xuất, trong khi "
            "kinh nghiệm từ các giao dịch tương tự có thể khai thác bằng lập luận dựa trên tình huống (CBR). Kết hợp hai "
            "nguồn tri thức này cho phép xây dựng một hệ hỗ trợ quyết định dựa trên tri thức (KB-DSS) có khả năng giải thích.")
    bc.tieu_de("2. Mục tiêu", 2)
    bc.gach_dau_dong([
        "Xây dựng cơ sở tri thức gồm khung Hãng → Dòng → Phiên bản và tập 25 luật sản xuất được nạp từ tệp cấu hình, có kiểm tra nhất quán.",
        "Cài đặt máy suy diễn tiến có so khớp, giải quyết xung đột, cập nhật dữ kiện và ghi vết từng luật tác động lên giá.",
        "Cài đặt CBR truy hồi tối đa 5 xe tương tự bằng độ tương tự có trọng số, hiệu chỉnh giá theo khác biệt và xử lý trường hợp thiếu ca.",
        "Kết hợp giá theo luật và giá CBR thành giá đề xuất kèm khoảng giá tham khảo, mức tin cậy theo quy tắc, cảnh báo và lời giải thích.",
        "Xây dựng giao diện Streamlit tiếng Việt và đánh giá thực nghiệm so với Random Forest trên cùng tập kiểm thử.",
    ])
    bc.tieu_de("3. Đối tượng và phạm vi", 2)
    tk = KB.thong_ke()
    bc.doan(f"Đối tượng là xe ô tô con đã qua sử dụng phổ biến tại Việt Nam. Cơ sở tri thức hiện gồm {tk['so_hang']} hãng, "
            f"{tk['so_dong']} dòng xe và {tk['so_phien_ban']} phiên bản thuộc {len(KB.frames['phan_khuc'])} phân khúc. "
            f"Năm định giá được cố định là {KB.nam_dinh_gia} để kết quả tái lập được.")
    bc.doan("**Giới hạn quan trọng về dữ liệu:** nhóm chưa có dữ liệu giao dịch hay tin rao thực tế được phép sử dụng. "
            f"Vì vậy toàn bộ {f(M['so_train'] + M['so_test'], 0)} bản ghi dùng cho kho tình huống và thực nghiệm là **dữ liệu mô phỏng** "
            "do chương trình sinh với seed cố định. Giá xe mới tham chiếu, hệ số và ngưỡng trong luật là **giả định** của nhóm, "
            "chưa được hiệu chỉnh bằng dữ liệu thị trường hay khảo sát chuyên gia. Báo cáo không tuyên bố độ chính xác "
            "trên thị trường thực.")
    bc.tieu_de("4. Phương pháp thực hiện", 2)
    bc.gach_dau_dong([
        "Phân tích bài toán, thu thập tri thức dạng giả định chuyên gia và biểu diễn bằng khung, luật sản xuất (JSON).",
        "Thiết kế và cài đặt hệ thống theo mô-đun bằng Python: suy diễn tiến, CBR, kết hợp, giao diện Streamlit và Plotly.",
        "Sinh dữ liệu mô phỏng, làm sạch, chia train/test; chọn tham số chỉ trên tập validation tách từ train.",
        "So sánh bốn phương pháp (chỉ luật, chỉ CBR, Random Forest, hệ lai) bằng MAE, MAPE, R², tỷ lệ nằm trong khoảng và thời gian xử lý.",
        "Kiểm thử tự động (pytest, Streamlit AppTest) và chụp ảnh giao diện thật bằng Playwright.",
    ])
    bc.tieu_de("5. Kết quả đạt được", 2)
    hl = BANG["Hệ lai luật + CBR"]
    bc.doan(f"Nhóm đã xây dựng ứng dụng chạy được với 4 trang chức năng, {tk['so_kich_ban']} kịch bản mẫu và bộ kiểm thử 40 ca đạt. "
            f"Trên {M['so_test']} ca kiểm thử mô phỏng, hệ lai đạt MAE {f(hl['MAE'])} triệu đồng, MAPE {pt(hl['MAPE'], 2)}; "
            "mức chênh với Random Forest và CBR không có ý nghĩa thống kê (mục 4.3). Kết quả này chỉ phản ánh dữ liệu mô phỏng.")
    bc.tieu_de("6. Cấu trúc báo cáo", 2)
    bc.doan("Ngoài phần mở đầu và kết luận, báo cáo gồm bốn chương: Chương 1 trình bày bài toán và cơ sở lý thuyết; "
            "Chương 2 phân tích, thiết kế hệ thống và cơ sở tri thức; Chương 3 trình bày cài đặt và giao diện theo luồng "
            "người dùng; Chương 4 trình bày dữ liệu, thực nghiệm, phân tích ca demo và các giới hạn.")


def chuong1(bc: BaoCao):
    bc.tieu_de("CHƯƠNG 1. BÀI TOÁN VÀ CƠ SỞ LÝ THUYẾT", 1, trang_moi=True)
    bc.tieu_de("1.1. Bài toán định giá xe ô tô cũ", 2)
    bc.doan("Đầu vào của bài toán là mô tả một chiếc xe cần định giá: hãng, dòng, phiên bản, năm sản xuất, số km, khu vực, "
            "tình trạng và lịch sử sử dụng (bảo dưỡng tại hãng, từng chạy dịch vụ, ngập nước, tai nạn nặng). Đầu ra là một "
            "giá đề xuất, khoảng giá tham khảo, mức tin cậy, các cảnh báo và lời giải thích cho người dùng.")
    bc.doan("Các yếu tố ảnh hưởng đến giá có thể chia thành ba nhóm: (1) đặc điểm cố định của phiên bản như giá xe mới, phân "
            "khúc, hộp số, thương hiệu; (2) mức độ sử dụng như tuổi xe và số km; (3) tình trạng và rủi ro như hao mòn, lịch sử "
            "bảo dưỡng, ngập nước, tai nạn. Khó khăn chính là thông tin bất cân xứng, dữ liệu giao dịch thật khó thu thập và "
            "các rủi ro ẩn có tác động lớn nhưng hiếm gặp. Hệ thống chỉ **hỗ trợ** quyết định; người dùng vẫn cần kiểm tra xe thực tế.")
    bc.tieu_de("1.2. Hệ hỗ trợ quyết định dựa trên tri thức", 2)
    bc.doan("Hệ hỗ trợ quyết định (DSS) là hệ thống máy tính giúp người ra quyết định sử dụng dữ liệu và mô hình để giải quyết "
            "các bài toán bán cấu trúc [1]. Một DSS thường gồm thành phần quản lý dữ liệu, thành phần mô hình, giao diện "
            "người dùng và – với KB-DSS – thêm thành phần tri thức cùng cơ chế suy diễn. Điểm khác biệt của KB-DSS so với mô "
            "hình học máy hộp đen là tri thức được biểu diễn tường minh, nên hệ thống có thể giải thích từng bước lập luận.")
    bc.tieu_de("1.3. Biểu diễn tri thức bằng khung và luật sản xuất", 2)
    bc.doan("**Khung (frame)** do Minsky đề xuất [3] là cấu trúc dữ liệu mô tả một khái niệm điển hình bằng các khe (slot) và "
            "giá trị. Các khung liên kết theo quan hệ phân cấp, khung con kế thừa giá trị của khung cha. Trong đề tài, khung "
            "Hãng → Dòng xe → Phiên bản giúp phiên bản kế thừa phân khúc từ dòng xe và nhóm giữ giá từ hãng.")
    bc.doan("**Luật sản xuất** có dạng NẾU <điều kiện> THÌ <hành động>. Hệ luật gồm cơ sở luật, bộ nhớ làm việc (WM) chứa "
            "dữ kiện và máy suy diễn [2], [4]. Ưu điểm của luật là mô-đun hóa, dễ đọc với chuyên gia và mỗi luật kèm lời giải thích.")
    bc.tieu_de("1.4. Suy diễn tiến và giải quyết xung đột", 2)
    bc.doan("Suy diễn tiến xuất phát từ dữ kiện đã biết, lặp chu trình *nhận dạng – chọn – thực hiện*: (1) so khớp điều kiện "
            "của mọi luật với WM để tạo tập xung đột; (2) chọn một luật theo chiến lược giải quyết xung đột; (3) thực thi hành "
            "động, cập nhật WM. Chu trình dừng khi tập xung đột rỗng [2], [4]. Các chiến lược thường dùng gồm độ ưu tiên "
            "(salience), độ cụ thể (luật nhiều điều kiện hơn được chọn trước) và refraction (mỗi luật chỉ chạy một lần với "
            "cùng dữ kiện). Với tập luật lớn, thuật toán Rete [5] giúp so khớp hiệu quả; tập 25 luật của đề tài đủ nhỏ để so "
            "khớp trực tiếp ở mỗi chu kỳ.")
    bc.doan("Suy diễn tiến phù hợp bài toán định giá vì mục tiêu không phải chứng minh một giả thuyết cho trước (như suy diễn "
            "lùi) mà là lần lượt áp dụng mọi điều chỉnh liên quan từ dữ kiện đầu vào để đi đến giá.")
    bc.tieu_de("1.5. Lập luận dựa trên tình huống (CBR)", 2)
    bc.doan("CBR giải bài toán mới bằng cách tái sử dụng lời giải của các tình huống tương tự đã biết. Aamodt và Plaza [6] mô tả "
            "chu trình 4R: **Truy hồi** (Retrieve) các ca tương tự, **Tái sử dụng** (Reuse) lời giải, **Điều chỉnh** (Revise) "
            "cho phù hợp và **Lưu giữ** (Retain) ca mới. Độ tương tự toàn cục thường là trung bình có trọng số của các độ "
            "tương tự cục bộ theo từng thuộc tính [7]. Bước điều chỉnh có thể dùng tri thức miền – trong đề tài là chính tập luật.")
    bc.tieu_de("1.6. Lý do kết hợp luật và CBR", 2)
    bc.gach_dau_dong([
        "Luật biểu diễn tri thức khái quát, giải thích rõ nhưng dùng bậc rời rạc nên khó bắt các khác biệt tinh tế của thị trường.",
        "CBR bám sát các giao dịch cụ thể, nhưng giá thô của xe tương tự chưa phản ánh khác biệt với xe cần định giá và sẽ thất bại khi thiếu ca.",
        "Kết hợp: luật dùng để **hiệu chỉnh** giá xe tương tự về đặc điểm xe cần định giá; khi thiếu ca, hệ thống quay về giá theo luật và nói rõ lý do.",
        f"Random Forest [8], [9] chỉ dùng làm **mô hình đối chứng** trong thực nghiệm vì là hộp đen và không giải thích từng bước như KB-DSS.",
    ])


def chuong2(bc: BaoCao):
    bc.tieu_de("CHƯƠNG 2. PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG", 1, trang_moi=True)
    bc.tieu_de("2.1. Yêu cầu hệ thống", 2)
    bc.bang("Yêu cầu chức năng", [
        ["Mã", "Chức năng", "Mô tả"],
        ["F1", "Nhập thông tin xe", "Chọn Hãng → Dòng → Phiên bản lọc phụ thuộc; nhập năm, km, khu vực, tình trạng, lịch sử; kiểm tra lỗi ngay cạnh trường."],
        ["F2", "Kịch bản mẫu", f"{KB.thong_ke()['so_kich_ban']} kịch bản tự điền biểu mẫu: bình thường, bảo dưỡng hãng, ngập nước, dịch vụ, thiếu ca, rủi ro kép, nghi chỉnh đồng hồ."],
        ["F3", "Định giá", "Suy diễn tiến, CBR, kết hợp; trả về giá đề xuất, khoảng giá, mức tin cậy, cảnh báo."],
        ["F4", "Giải thích", "Yếu tố ảnh hưởng mạnh nhất, vết suy diễn, waterfall, bảng xe tương tự, căn cứ hiệu chỉnh, công thức kết hợp."],
        ["F5", "Phân tích dữ liệu", "Lọc theo hãng, phân khúc, đời xe; thống kê và biểu đồ có nhãn dữ liệu mô phỏng."],
        ["F6", "Quản trị tri thức", "Xem tập luật theo nhóm, khung xe, kho tình huống; kiểm tra nhất quán và chỉ rõ đối tượng cần sửa."],
    ], [1.2, 3.6, 11.2])
    bc.doan("Yêu cầu phi chức năng: giao diện tiếng Việt, đọc rõ khi trình chiếu; thời gian định giá dưới 1 giây; chạy bằng "
            "đường dẫn tương đối trên Windows/Linux; tri thức tách khỏi mã nguồn để chỉnh sửa không cần lập trình; kết quả "
            "tái lập được nhờ seed cố định.")
    bc.tieu_de("2.2. Kiến trúc tổng thể", 2)
    bc.doan("Hệ thống được tổ chức thành ba tầng (Hình 2.1). Tầng giao diện chỉ gọi dịch vụ định giá; tầng nghiệp vụ gồm các "
            "mô-đun độc lập có thể kiểm thử riêng; tầng tri thức và dữ liệu là các tệp JSON/CSV.")
    bc.hinh(anh(CHARTS / "so_do_kien_truc.png"), "Sơ đồ kiến trúc ba tầng của hệ thống", 15.5)
    bc.tieu_de("2.3. Luồng xử lý định giá", 2)
    bc.doan("Hình 2.2 mô tả luồng xử lý từ khi người dùng bấm Định giá. Giá theo luật của xe cần định giá được dùng hai lần: "
            "làm một thành phần của giá đề xuất và làm mẫu số hiệu chỉnh giá các xe tương tự trong CBR.")
    bc.hinh(anh(CHARTS / "so_do_luong_xu_ly.png"), "Luồng xử lý một yêu cầu định giá", 15.5)
    bc.tieu_de("2.4. Thiết kế cơ sở tri thức", 2)
    bc.tieu_de("2.4.1. Khung Hãng → Dòng xe → Phiên bản", 3)
    bc.doan("Tệp `kb/frames.json` lưu ba cấp khung. Bảng 2.2 liệt kê các khe; khe nào không khai báo ở phiên bản sẽ được kế "
            "thừa từ dòng xe hoặc hãng khi nạp (phương thức `KnowledgeBase._phang_hoa_khung`).")
    bc.bang("Các khe của khung tri thức", [
        ["Cấp khung", "Khe", "Ý nghĩa / ví dụ"],
        ["Hãng", "id, ten, quoc_gia, nhom_giu_gia", "toyota, Toyota, Nhật Bản, cao (giả định)"],
        ["Dòng xe", "id, ten, phan_khuc, kieu_dang", "toyota-vios, Vios, B, Sedan"],
        ["Phiên bản", "id, ten, dong_co, hop_so, nhien_lieu, so_cho, xuat_xu, gia_moi, nam_tu, nam_den",
         "toyota-vios-15g-cvt, 1.5G CVT, 1.5L xăng, CVT, Xăng, 5, Lắp ráp, 545 triệu, 2014–2026"],
        ["Kế thừa", "phan_khuc, kieu_dang ← Dòng; nhom_giu_gia ← Hãng", "Phiên bản 1.5G CVT kế thừa phân khúc B và nhóm giữ giá cao"],
    ], [2.6, 6.4, 7.0])
    dong = [["Hãng (nhóm giữ giá)", "Dòng xe (phân khúc)", "Phiên bản – giá xe mới tham chiếu (triệu đồng)"]]
    for h in KB.frames["hang_xe"]:
        for i, d in enumerate(h["dong_xe"]):
            dong.append([f"{h['ten']} ({h['nhom_giu_gia'].replace('_', ' ')})" if i == 0 else "",
                         f"{d['ten']} ({d['phan_khuc']})",
                         "; ".join(f"{p['ten']} – {f(p['gia_moi'], 0)}" for p in d["phien_ban"])])
    bc.doan(f"Bảng 2.3 liệt kê {KB.thong_ke()['so_phien_ban']} phiên bản. **Giá xe mới là mốc tham chiếu giả định** do nhóm đặt "
            "gần với mức niêm yết từng được công bố nhưng chưa đối chiếu bảng giá chính thức, và dùng chung cho mọi đời xe "
            "của phiên bản. Nhóm giữ giá của hãng cũng là giả định của nhóm.")
    bc.bang("Khung xe trong cơ sở tri thức (giá mới là giả định)", dong, [3.6, 3.6, 8.8], co=10.5)
    bc.tieu_de("2.4.2. Lược đồ dữ kiện", 3)
    nhom_dk = {"dau_vao": "Đầu vào", "khung": "Kế thừa từ khung", "he_thong": "Hệ thống", "suy_dien": "Suy diễn"}
    hang = [["Nguồn", "Dữ kiện", "Kiểu"]]
    for ma, ten in nhom_dk.items():
        ds = [k for k, v in CFG["du_kien"].items() if v["nguon"] == ma]
        kieu = sorted({{"so": "số", "chuoi": "chuỗi", "logic": "logic"}[CFG["du_kien"][k]["kieu"]] for k in ds})
        hang.append([ten, ", ".join(ds), ", ".join(kieu)])
    bc.doan("Mọi dữ kiện mà luật được phép dùng được khai báo trong `kb/config.json` kèm kiểu (số, chuỗi, logic) và nguồn. "
            "Bộ kiểm tra nhất quán dựa vào lược đồ này để phát hiện luật tham chiếu dữ kiện chưa khai báo hoặc sai kiểu.")
    bc.bang("Lược đồ dữ kiện của bộ nhớ làm việc", hang, [3.2, 10.0, 2.8], co=11)
    bc.doan("Hai dữ kiện suy diễn quan trọng được tính bởi luật R01 và R02:")
    bc.cong_thuc(omath(V("t"), O(" = "), sub(V("N"), T("đg")), O(" − "), sub(V("N"), T("sx")), O(",    "),
                       sub(V("r"), T("km")), O(" = "), frac(T("km"), O("15 000 × ") + T("max") + ngoac(O("1, ") + V("t")))))
    bc.doan(f"trong đó *t* là tuổi xe, N~đg~ = {KB.nam_dinh_gia} là năm định giá, N~sx~ là năm sản xuất, r~km~ là tỷ lệ số km thực "
            "tế so với km chuẩn 15.000 km/năm (giả định). Dùng max(1, t) để xe 0 tuổi không gây chia cho 0.", thut_dau=False)
    bc.tieu_de("2.4.3. Tập luật sản xuất", 3)
    bc.doan(f"Tập luật gồm {len(KB.luat)} luật thuộc {len(CFG['nhom_luat'])} nhóm, lưu trong `kb/rules.json` và được nạp khi khởi "
            "động; giao diện không chứa luật viết cứng. Mỗi luật có mã, nhóm, tên, mô tả, độ ưu tiên, danh sách điều kiện "
            "(hội AND), danh sách hành động, mẫu lời giải thích và nguồn tri thức. Có bốn loại hành động: `suy_dien` "
            "(tính dữ kiện mới bằng hàm đã đăng ký), `dat_gia`, `nhan_gia` (nhân giá với hệ số) và `canh_bao`. "
            f"Bảng {bc.so_bang_tiep()} liệt kê toàn bộ luật; mọi hệ số và ngưỡng là **giả định của nhóm**.")
    from carval.ui.page_admin import mo_ta_dieu_kien, mo_ta_hanh_dong
    hang = [["Mã", "Nhóm", "Ưu tiên", "Điều kiện (AND)", "Hành động"]]
    for r in KB.rules_raw["luat"]:
        hang.append([r["id"], r["nhom"], str(r["uu_tien"]), " ∧ ".join(mo_ta_dieu_kien(d) for d in r["dieu_kien"]),
                     "; ".join(mo_ta_hanh_dong(h) for h in r["hanh_dong"]) + (f" [loại trừ: {r['nhom_loai_tru']}]" if r.get("nhom_loai_tru") else "")])
    bc.bang("Tập 25 luật trong kb/rules.json (theo thứ tự trong tệp)", hang, [1.2, 2.8, 1.5, 6.0, 4.5], can_giua={0, 2}, co=10)
    bc.doan("Giá theo luật vì vậy có dạng tích các hệ số của những luật đã thực thi, trừ khi luật ràng buộc R25 giới hạn trần:")
    bc.cong_thuc(omath(sub(V("P"), T("luật")), O(" = "), sub(V("P"), T("mới")), O(" × "),
                       nary("∏", V("r") + O(" ∈ ") + V("R"), None, sub(V("k"), V("r"))),
                       O(",    "), sub(V("P"), T("luật")), O(" ≤ 0,95 · "), sub(V("P"), T("mới"))))
    bc.doan("trong đó *R* là tập luật nhân giá đã được thực thi và k~r~ là hệ số của luật *r*.", thut_dau=False)
    bc.tieu_de("2.4.4. Giải quyết xung đột và xử lý nhiều luật rủi ro", 3)
    for d in KB.rules_raw["chien_luoc_giai_quyet_xung_dot"]:
        bc.doan(d.split(". ", 1)[1] if d[:2].strip(". ").isdigit() else d)
    bc.doan("Ví dụ: R13 (ưu tiên 85) đặt dữ kiện `nghi_tua_odo` khi xe từ 5 năm tuổi có tỷ lệ km dưới 0,25; nhờ cập nhật dữ "
            "kiện này, R10 (đi ít, điều kiện `nghi_tua_odo` chưa tồn tại) không còn thỏa – minh họa việc một luật chặn luật "
            "khác qua bộ nhớ làm việc. Luật trần giá R25 có ưu tiên thấp nhất nên luôn chạy sau mọi hệ số khác.")
    bc.tieu_de("2.4.5. Kiểm tra nhất quán cơ sở tri thức", 3)
    bc.gach_dau_dong([
        "Cấu trúc: đủ trường bắt buộc, mã luật duy nhất, nhóm luật đã khai báo, độ ưu tiên là số nguyên.",
        "Kiểu dữ liệu: dữ kiện trong điều kiện phải được khai báo; phép so sánh hợp lệ; giá trị đúng kiểu; hệ số trong (0; 1,5].",
        "Tham chiếu: giá trị chuỗi phải có trong khung/cấu hình (hãng, phân khúc, tình trạng…); hàm suy diễn phải tồn tại; kịch bản và kho tình huống phải tham chiếu phiên bản có trong khung.",
        "Logic: điều kiện mâu thuẫn, luật trùng điều kiện, dữ kiện suy diễn không có luật nào sinh ra; các nhóm TUOI_XE, SO_KM, TINH_TRANG phải loại trừ lẫn nhau và nhóm TUOI_XE phải phủ mọi tuổi 0–40, kiểm tra trên lưới điểm biên sinh từ ngưỡng của luật.",
    ])
    bc.doan("Kiểm tra trên lưới điểm biên là kiểm tra hữu hạn, không phải chứng minh hình thức cho mọi biểu thức.")
    bc.tieu_de("2.5. Thiết kế CBR", 2)
    cb = CFG["cbr"]
    bc.doan(f"Mỗi tình huống là một bản ghi của tập train (thuộc tính xe và giá). Truy hồi gồm hai bước: **lọc cứng** giữ các "
            f"xe cùng phân khúc và chênh năm sản xuất không quá {cb['chenh_nam_toi_da']}; sau đó tính **độ tương tự toàn cục**:")
    bc.cong_thuc(omath(T("Sim"), ngoac(V("Q") + O(", ") + V("C")), O(" = "),
                       frac(nary("∑", V("i") + O("=1"), O("7"), sub(V("w"), V("i")) + O("·") + sub(T("sim"), V("i")) + ngoac(V("Q") + O(", ") + V("C"))),
                            nary("∑", V("i") + O("=1"), O("7"), sub(V("w"), V("i"))))))
    sp = cb["tuong_tu_phien_ban"]
    w = cb["trong_so"]
    bc.bang("Hàm tương tự cục bộ và trọng số (giả định thiết kế)", [
        ["Tiêu chí", "Hàm tương tự cục bộ sim~i~", "Trọng số w~i~"],
        ["Phiên bản/dòng xe", f"{f(sp['cung_phien_ban'], 2)} cùng phiên bản; {f(sp['cung_dong_xe'], 2)} cùng dòng; {f(sp['cung_hang_cung_phan_khuc'], 2)} cùng hãng và phân khúc; {f(sp['cung_phan_khuc'], 2)} chỉ cùng phân khúc", f(w["phien_ban"], 2)],
        ["Năm sản xuất", f"max(0; 1 − |ΔN| / {cb['thang_do_nam']})", f(w["nam_sx"], 2)],
        ["Số km", f"max(0; 1 − |Δkm| / {f(cb['thang_do_km'], 0)})", f(w["so_km"], 2)],
        ["Tình trạng", "1 − |Δmức| / 3 (Kém = 0, Trung bình = 1, Tốt = 2, Rất tốt = 3)", f(w["tinh_trang"], 2)],
        ["Khu vực", f"1 nếu cùng khu vực, {f(cb['tuong_tu_khu_vuc_khac'], 1)} nếu khác", f(w["khu_vuc"], 2)],
        ["Bảo dưỡng hãng, dịch vụ", "Trung bình của hai phép so khớp đúng/sai", f(w["lich_su"], 2)],
        ["Ngập nước, tai nạn nặng", "Trung bình của hai phép so khớp đúng/sai", f(w["rui_ro"], 2)],
    ], [3.8, 9.8, 2.4], can_giua={2})
    bc.doan(f"Các xe có Sim ≥ θ được sắp giảm dần; hòa nhau thì ưu tiên chênh km nhỏ hơn. Hệ thống lấy tối đa k xe. "
            f"k = {cb['k_toi_da']} được cố định theo yêu cầu thiết kế (bảng giải thích không quá 5 dòng); ngưỡng θ = {f(cb['nguong_tuong_tu'], 2)} "
            "được chọn trên tập validation (mục 4.2). Giá từng xe được **hiệu chỉnh** về đặc điểm của xe cần định giá Q bằng tỷ số "
            "giá theo luật, rồi lấy trung bình có trọng số theo độ tương tự:")
    bc.cong_thuc(omath(sub(V("P'"), V("j")), O(" = "), sub(V("P"), V("j")), O(" × "),
                       frac(sub(V("P"), T("luật")) + ngoac(V("Q")), sub(V("P"), T("luật")) + ngoac(sub(V("C"), V("j"))))))
    bc.cong_thuc(omath(sub(V("P"), T("CBR")), O(" = "),
                       frac(nary("∑", V("j"), None, sub(T("Sim"), V("j")) + O("·") + sub(V("P'"), V("j"))),
                            nary("∑", V("j"), None, sub(T("Sim"), V("j"))))))
    bc.doan("Vì giá theo luật là tích các hệ số, tỷ số hiệu chỉnh phân rã được thành tích các tỷ số theo từng nhóm luật "
            "(giá mới, tuổi, km, tình trạng, lịch sử, rủi ro, thương hiệu), giúp giải thích vì sao giá từng xe được nâng hay hạ. "
            "Nếu không có xe nào đạt ngưỡng, CBR trả về trạng thái **thiếu dữ liệu** kèm lý do (không có ứng viên sau lọc cứng "
            "hoặc độ tương tự cao nhất chưa đạt θ).")
    bc.tieu_de("2.6. Thiết kế bước kết hợp, khoảng giá và mức tin cậy", 2)
    bc.doan("Trọng số của CBR tăng theo số xe tìm được n và độ tương tự trung bình; khi n = 0 thì w~CBR~ = 0 và giá đề xuất "
            "bằng giá theo luật:")
    bc.cong_thuc(omath(sub(V("w"), T("CBR")), O(" = "), sub(V("w"), T("max")), O(" · "), frac(V("n"), V("k")), O(" · "),
                       sub(T("Sim"), T("TB")), O(",    "), V("α"), O(" = 1 − "), sub(V("w"), T("CBR"))))
    bc.cong_thuc(omath(V("P"), O(" = "), V("α"), O(" · "), sub(V("P"), T("luật")), O(" + "), sub(V("w"), T("CBR")), O(" · "), sub(V("P"), T("CBR"))))
    kg = CFG["khoang_gia"]
    bc.doan("Khoảng giá tham khảo dùng một công thức thống nhất trong mã nguồn (`combine.py`), giao diện và báo cáo:")
    bc.cong_thuc(omath(V("δ"), O(" = "), T("min"), ngoac(sub(V("δ"), T("max")) + O("; ") + T("max") + ngoac(sub(V("δ"), T("min")) + O("; ") + T("CV") + O("; ") + V("d")) + O(" + ") + V("r")),
                       O(",    "), V("d"), O(" = "), frac(ngoac(sub(V("P"), T("luật")) + O(" − ") + sub(V("P"), T("CBR")), "|", "|"), V("P"))))
    bc.cong_thuc(omath(T("Khoảng"), O(" = "), ngoac(V("P") + ngoac(O("1 − ") + V("δ")) + O("; ") + V("P") + ngoac(O("1 + ") + V("δ")), "[", "]")))
    bc.doan(f"trong đó CV là hệ số biến thiên có trọng số của các giá đã hiệu chỉnh, d là độ chênh tương đối giữa hai nguồn, "
            f"r = {f(kg['cong_them_rui_ro'], 2)} khi có cảnh báo nghiêm trọng; δ~min~ = {f(kg['delta_min'], 2)} (chọn trên validation), "
            f"δ~max~ = {f(kg['delta_max'], 2)}. Khi không có CBR, δ = min(δ~max~; {f(kg['delta_khong_cbr'], 2)} + r). Đây là "
            "**khoảng kinh nghiệm**, không phải khoảng tin cậy thống kê.", thut_dau=False)
    tc = CFG["muc_tin_cay"]
    bc.bang("Quy tắc phân loại mức tin cậy (chỉ số kinh nghiệm, không phải xác suất)", [
        ["Mức", "Điều kiện"],
        ["Thấp", f"Có cảnh báo nghiêm trọng (ngập nước/tai nạn nặng), hoặc n = 0, hoặc d > {f(tc['thap_chenh_lech_tren'], 2)}"],
        ["Cao", f"n ≥ {tc['cao_so_xe_toi_thieu']}, Sim TB ≥ {f(tc['cao_sim_tb_toi_thieu'], 2)}, d ≤ {f(tc['cao_chenh_lech_toi_da'], 2)} và không có cảnh báo mức chú ý"],
        ["Trung bình", "Các trường hợp còn lại; giao diện liệt kê lý do không đạt mức Cao"],
    ], [3.0, 13.0])
    bc.tieu_de("2.7. Thiết kế giao diện", 2)
    bc.doan("Giao diện Streamlit chế độ rộng, nền sáng, màu chính xanh đậm, màu cam dành riêng cho giá đề xuất. Menu bên trái "
            "có bốn mục: Định giá, Kết quả và giải thích, Phân tích dữ liệu, Quản trị tri thức; cuối menu hiển thị số luật, "
            "số phiên bản và số ca so sánh thực sự được nạp. Kết quả định giá được giữ trong trạng thái phiên khi chuyển trang; "
            "nếu đầu vào thay đổi sau lần tính gần nhất, hệ thống nhắc tính lại và ghi rõ giá đang hiển thị thuộc lần tính trước.")


def chuong3(bc: BaoCao):
    bc.tieu_de("CHƯƠNG 3. CÀI ĐẶT VÀ GIAO DIỆN", 1, trang_moi=True)
    bc.tieu_de("3.1. Môi trường và công nghệ", 2)
    bc.bang("Công nghệ sử dụng (phiên bản đã kiểm tra)", [
        ["Thành phần", "Công nghệ", "Vai trò"],
        ["Ngôn ngữ", f"Python {ENV['python']}", "Toàn bộ hệ thống, script thực nghiệm và dựng báo cáo"],
        ["Giao diện", f"Streamlit {ENV['streamlit']}, Plotly", "Ứng dụng web 4 trang, biểu đồ tương tác"],
        ["Xử lý dữ liệu", f"pandas {ENV['pandas']}, NumPy {ENV['numpy']}", "Kho tình huống, độ tương tự dạng véc-tơ"],
        ["Đối chứng", f"scikit-learn {ENV['scikit_learn']}", "Random Forest, chia tập phân tầng"],
        ["Kiểm thử", "pytest, Streamlit AppTest, Playwright", "Kiểm thử nghiệp vụ, giao diện và chụp ảnh thật"],
        ["Báo cáo", "matplotlib, python-docx, LibreOffice", "Biểu đồ từ tệp kết quả, DOCX, xuất PDF"],
    ], [3.0, 5.5, 7.5])
    bc.tieu_de("3.2. Tổ chức mã nguồn", 2)
    bc.bang("Các mô-đun chính", [
        ["Tệp", "Nội dung"],
        ["kb/frames.json, rules.json, config.json, scenarios.json", "Khung xe, 25 luật, lược đồ dữ kiện và tham số, kịch bản demo"],
        ["src/carval/kb.py", "Nạp tri thức, kế thừa khung, truy vấn hãng/dòng/phiên bản"],
        ["src/carval/inference.py", "Máy suy diễn tiến: so khớp, giải quyết xung đột, hành động, vết"],
        ["src/carval/kb_validation.py", "Kiểm tra cấu trúc, kiểu, tham chiếu, logic của cơ sở tri thức"],
        ["src/carval/cbr.py", "Kho tình huống, độ tương tự, truy hồi, hiệu chỉnh, căn cứ hiệu chỉnh"],
        ["src/carval/combine.py", "Kết hợp, khoảng giá, mức tin cậy"],
        ["src/carval/validation.py, service.py, explain.py", "Kiểm tra đầu vào, điều phối, sinh lời giải thích"],
        ["src/carval/datagen.py, cleaning.py, evaluation.py", "Sinh dữ liệu mô phỏng, làm sạch/chia tập, chỉ số và Random Forest"],
        ["src/app.py, src/carval/ui/", "Giao diện Streamlit: theme, biểu đồ, 4 trang"],
        ["scripts/", "Sinh dữ liệu, làm sạch, chọn tham số, thực nghiệm, biểu đồ, chụp ảnh, dựng báo cáo"],
        ["tests/", "40 ca kiểm thử nghiệp vụ và giao diện"],
    ], [6.5, 9.5], co=11)
    bc.tieu_de("3.3. Cài đặt các thành phần chính", 2)
    dong, a = trich_json_luat("R22")
    bc.doan(f"Đoạn mã 3.1 là luật R22 trích nguyên văn từ `kb/rules.json` (dòng {a}): luật có khai báo nhóm loại trừ "
            "`RUI_RO_NANG` và hai hành động.")
    bc.ma_nguon(dong, f"Luật R22 trong kb/rules.json (từ dòng {a})")
    d1, a1 = trich("src/carval/inference.py", "khop", lop="ForwardChainingEngine")
    d2, a2 = trich("src/carval/inference.py", "khoa_chon", lop="ForwardChainingEngine")
    bc.doan(f"Đoạn mã 3.2 cho thấy điều kiện ngầm định của luật tác động giá và khóa giải quyết xung đột "
            f"(`src/carval/inference.py`, dòng {a1} và {a2}).")
    bc.ma_nguon(d1 + [""] + d2, "So khớp luật và khóa giải quyết xung đột")
    d3, a3 = trich("src/carval/inference.py", "suy_dien", tu="while True:", den="b.gia_truoc, b.gia_sau, b.he_so = truoc, sau", lop="ForwardChainingEngine")
    bc.doan(f"Đoạn mã 3.3 là phần lõi của chu trình nhận dạng – hành động (dòng {a3} trở đi): tính tập xung đột, sắp theo khóa, "
            "thực thi hành động và áp dụng nhóm loại trừ.")
    bc.ma_nguon(d3, "Chu trình suy diễn tiến (trích)")
    d4, a4 = trich("src/carval/cbr.py", "tuong_tu_cuc_bo", lop="KhoTinhHuong")
    bc.doan(f"Độ tương tự cục bộ được tính dạng véc-tơ trên toàn bộ ứng viên sau lọc cứng (`src/carval/cbr.py`, dòng {a4}):")
    bc.ma_nguon(d4, "Độ tương tự cục bộ theo 7 tiêu chí")
    d5, a5 = trich("src/carval/cbr.py", "truy_hoi", tu="gia_luat_c = float(", den="trang_thai = ", lop="KhoTinhHuong")
    bc.doan(f"Bước hiệu chỉnh và tính giá CBR (dòng {a5} trở đi):")
    bc.ma_nguon(d5, "Hiệu chỉnh giá xe tương tự và giá CBR (trích)")
    d6, a6 = trich("src/carval/combine.py", "ket_hop", tu="if n == 0 or cbr.gia_cbr is None:", den="delta = min(ckg[\"delta_max\"], max(")
    bc.doan(f"Công thức kết hợp và khoảng giá trong `src/carval/combine.py` (dòng {a6}) khớp với công thức (2.6)–(2.8):")
    bc.ma_nguon(d6, "Kết hợp giá luật và giá CBR")

    tc1 = DEMO["TC01"]
    bc.tieu_de("3.4. Giao diện theo luồng người dùng", 2)
    bc.doan("Các hình trong mục này được chụp tự động bằng Playwright từ ứng dụng đang chạy (`scripts/capture_screenshots.py`, "
            "khung nhìn rộng 1440 px). Hình 3.1 đến Hình 3.8 dùng cùng ca chính TC01 – Toyota Vios 1.5G CVT đời 2019, "
            "95.000 km – để người đọc đối chiếu các con số qua từng bước.")
    bc.tieu_de("3.4.1. Nhập thông tin xe", 3)
    bc.doan("Trang Định giá sắp xếp từ trên xuống: tiêu đề, ghi chú dữ liệu mô phỏng, ô chọn kịch bản mẫu, biểu mẫu ba cột "
            "và nút Định giá. Cột trái chọn Hãng → Dòng → Phiên bản (danh sách lọc theo lựa chọn trước) và hiển thị phân khúc, "
            "giá mới tham chiếu; cột giữa nhập năm, số km, khu vực và hiện tuổi xe; cột phải chọn tình trạng và bốn thông tin "
            "lịch sử. Hãy chú ý ô ghi chú màu cam ở đầu trang ghi rõ dữ liệu là mô phỏng.")
    bc.hinh(anh(SHOTS / "01_trang_nhap_thong_tin_xe.png"), "Trang Định giá với kịch bản TC01 được điền sẵn")
    bc.doan("Dữ liệu nhập được kiểm tra ngay khi thay đổi. Hình 3.2 cho thấy khi nhập năm 2030, thông báo lỗi xuất hiện ngay "
            "dưới trường Năm sản xuất; bấm Định giá lúc này chỉ hiện thông báo tổng hợp và không tạo kết quả.")
    bc.hinh(anh(SHOTS / "11_loi_nhap_lieu.png"), "Thông báo lỗi hiển thị cạnh trường cần sửa", 14)
    bc.tieu_de("3.4.2. Kết quả định giá và khoảng giá", 3)
    bc.doan(f"Sau khi bấm Định giá và chọn “Xem kết quả và giải thích”, trang kết quả hiển thị thông tin xe, hàng bốn ô số: giá "
            f"đề xuất {f(tc1['gia_de_xuat'])} triệu (viền cam), giá theo luật {f(tc1['gia_luat'])} triệu, giá CBR {f(tc1['gia_cbr'])} triệu "
            f"và mức tin cậy {tc1['muc_tin_cay']} (ghi rõ là chỉ số kinh nghiệm). Thanh khoảng giá bên dưới đánh dấu giá thấp "
            f"{f(tc1['khoang_thap'])}, giá cao {f(tc1['khoang_cao'])} và vị trí của ba mức giá.")
    bc.hinh(anh(SHOTS / "02_ket_qua_va_khoang_gia.png", cat_menu=True), "Kết quả định giá TC01: bốn ô số chính và thanh khoảng giá")
    bc.tieu_de("3.4.3. Giải thích và phép tính giá đề xuất", 3)
    bc.doan("Tab Giải thích mở mặc định. Cột trái liệt kê các yếu tố ảnh hưởng mạnh nhất, giá theo luật, giá CBR, trọng số và "
            "phép tính; cột phải là biểu đồ tác động của từng luật (đỏ: giảm, xanh: tăng). Khung “Phép tính giá đề xuất” trình "
            "bày công thức với đúng các số của lần tính.")
    bc.hinh(anh(SHOTS / "03_tab_giai_thich.png"), "Tab Giải thích: yếu tố ảnh hưởng, biểu đồ tác động và công thức")
    bc.tieu_de("3.4.4. Vết suy diễn", 3)
    bc.doan("Tab Vết suy diễn bắt đầu bằng biểu đồ waterfall từ giá xe mới đến giá theo luật (Hình 3.5), ngay dưới là bảng "
            "Mã luật | Lý do | Giá trước | Thay đổi | Giá sau (Hình 3.6). Các luật suy dẫn R01, R02 không đổi giá nhưng vẫn "
            "được ghi vết với phép tính cụ thể. Phần mở rộng “Tập xung đột…” hiển thị luật được chọn ở từng chu kỳ.")
    bc.hinh(anh(SHOTS / "04a_bieu_do_waterfall.png"), "Biểu đồ waterfall từ giá xe mới đến giá theo luật (TC01)")
    bc.hinh(anh(SHOTS / "04b_bang_vet_suy_dien.png"), "Bảng vết suy diễn và bước kết hợp với CBR (TC01)")
    bc.tieu_de("3.4.5. Xe tương tự và căn cứ hiệu chỉnh", 3)
    bc.doan(f"Tab Xe tương tự cho biết số ứng viên sau lọc cứng ({tc1['so_ung_vien_cbr']} xe), số xe đạt ngưỡng ({tc1['so_dat_nguong_cbr']} xe) "
            "và bảng tối đa 5 xe sắp theo độ tương tự giảm dần (Hình 3.7). Khi chọn một xe, hai bảng bên dưới trình bày độ tương "
            "tự theo từng tiêu chí và tỷ số hiệu chỉnh theo từng nhóm luật (Hình 3.8). Trong hình, xe #3 có tình trạng Trung bình "
            "nên giá được nâng theo tỷ số 1/0,92.")
    bc.hinh(anh(SHOTS / "05a_bang_xe_tuong_tu.png"), "Bảng 5 xe tương tự với giá gốc, giá hiệu chỉnh và độ tương tự")
    bc.hinh(anh(SHOTS / "05b_can_cu_hieu_chinh.png"), "Căn cứ so sánh và hiệu chỉnh giá của xe tương tự #3")
    bc.tieu_de("3.4.6. Cảnh báo rủi ro và trường hợp thiếu tình huống", 3)
    tc3, tc5, tc6 = DEMO["TC03"], DEMO["TC05"], DEMO["TC06"]
    bc.doan(f"Với kịch bản TC03 (Hyundai Accent ngập nước), luật R20 phát cảnh báo nghiêm trọng, mức tin cậy chuyển sang "
            f"{tc3['muc_tin_cay']} và khoảng giá được mở rộng thêm r: δ = {pt(tc3['delta'] * 100)} (Hình 3.9).")
    bc.hinh(anh(SHOTS / "08_ca_ngap_nuoc_canh_bao.png", cat_menu=True), "Kết quả ca ngập nước TC03 có cảnh báo R20")
    bc.doan("Với TC06 (vừa ngập nước vừa tai nạn nặng), bảng vết cho thấy R22 được chọn trước nhờ ưu tiên 95 và áp dụng hệ số "
            "gộp 0,62; R20, R21 vẫn được ghi nhận và phát cảnh báo nhưng thay đổi bằng 0 do nhóm loại trừ (Hình 3.10).")
    bc.hinh(anh(SHOTS / "10b_rui_ro_kep_bang_vet.png"), "Vết suy diễn ca rủi ro kép TC06: giải quyết xung đột giữa R22, R20, R21")
    bc.doan(f"Với TC05 (Toyota Land Cruiser, phân khúc SUV-F không có trong kho), CBR trả về trạng thái thiếu dữ liệu. Ô Giá CBR "
            f"ghi “Không đủ dữ liệu”, cảnh báo nêu lý do, hệ thống dùng giá theo luật (α = 1) với δ = {pt(tc5['delta'] * 100)} và mức tin cậy {tc5['muc_tin_cay']} (Hình 3.11).")
    bc.hinh(anh(SHOTS / "09_thieu_tinh_huong_tuong_tu.png", cat_menu=True), "Ca thiếu tình huống tương tự TC05: dùng giá theo luật và nêu lý do")
    bc.tieu_de("3.4.7. Phân tích dữ liệu", 3)
    bc.doan("Trang Phân tích dữ liệu có nhãn “Dữ liệu mô phỏng” cạnh tiêu đề, bộ lọc hãng, phân khúc, đời xe ở đầu trang; "
            "bốn ô thống kê; hai biểu đồ phân bố giá và giá trung vị theo phân khúc; biểu đồ quan hệ tuổi xe – giá ở dưới cùng. "
            "Mọi thống kê cập nhật theo bộ lọc; nếu bộ lọc không có mẫu, trang hiện thông báo thay cho biểu đồ.")
    bc.hinh(anh(SHOTS / "06_phan_tich_du_lieu.png", cat_menu=True), "Trang Phân tích dữ liệu (dữ liệu mô phỏng đã làm sạch)")
    bc.tieu_de("3.4.8. Quản trị tri thức", 3)
    bc.doan("Trang Quản trị tri thức hiển thị số luật, số khung xe, số tình huống và trạng thái kiểm tra nhất quán; bốn tab "
            f"Tập luật (lọc theo nhóm), Khung xe, Kho tình huống và Kiểm tra nhất quán. Hình {bc.so_hinh_tiep()} là kết quả kiểm "
            "tra cơ sở tri thức đang dùng: 10 hạng mục đều đạt.")
    bc.hinh(anh(SHOTS / "07_quan_tri_tri_thuc_kiem_tra.png", cat_menu=True), "Trang Quản trị tri thức – kiểm tra nhất quán cơ sở tri thức đang dùng")
    bc.doan("Để minh họa khả năng phát hiện lỗi, tab này cho phép kiểm tra tệp `kb/examples/rules_invalid_demo.json` chứa lỗi "
            f"cố ý. Hình {bc.so_hinh_tiep()} cho thấy hệ thống chỉ rõ luật cần sửa: mã trùng R06, giá trị sai kiểu ở R14, tham chiếu hãng/phân "
            "khúc không có trong khung ở R15, hàm suy diễn không tồn tại ở R02, khoảng tuổi chồng lấn giữa R05 và R06…")
    bc.hinh(anh(SHOTS / "07b_kiem_tra_tep_loi_minh_hoa.png"), "Kết quả kiểm tra tệp luật minh họa chứa lỗi cố ý")
    bc.tieu_de("3.5. Kiểm thử", 2)
    so_pass = len(re.findall(r" PASSED", TEST_LOG))
    so_fail = len(re.findall(r" FAILED", TEST_LOG))
    bc.doan(f"Bộ kiểm thử gồm 40 ca (lần chạy cuối: {so_pass} đạt, {so_fail} lỗi; nhật ký tại `outputs/results/test_report.txt`). "
            "Kiểm thử giao diện dùng Streamlit AppTest – chạy chính tệp `src/app.py` và thao tác lên widget.")
    bc.bang("Nhóm kiểm thử tự động", [
        ["Tệp", "Nội dung kiểm tra", "Số ca"],
        ["test_kb.py", "Nạp 25 luật/35 phiên bản; kế thừa khung; tri thức hiện tại nhất quán; phát hiện lỗi tệp minh họa, khung và kịch bản lỗi; bao phủ tuổi", "6"],
        ["test_inference.py", "Vết và giá TC01; vết liền mạch; thứ tự giải quyết xung đột; ngập nước; tai nạn; rủi ro kép không nhân dồn; chặn R10 khi nghi chỉnh ODO; trần 95%; xe dịch vụ; refraction", "10"],
        ["test_cbr_combine.py", "≤ 5 xe, sắp giảm, đạt ngưỡng, đúng lọc cứng; Sim tự thân = 1; hiệu chỉnh và phân rã; thiếu ca; ngưỡng cao; công thức kết hợp; khoảng chứa giá đề xuất; mức tin cậy; test không nằm trong kho", "9"],
        ["test_validation_data.py", "Năm/km không hợp lệ; cảnh báo km bất thường; dịch vụ từ chối đầu vào lỗi; tách train/test; dữ liệu tham chiếu khung; bộ sinh tái lập", "7"],
        ["test_app.py", "Trang mặc định; chọn hãng cập nhật dòng; luồng định giá → kết quả; lỗi nhập; nhắc tính lại; kịch bản ngập nước có cảnh báo; trang kết quả khi chưa có kết quả; phân tích (bộ lọc rỗng) và quản trị", "8"],
    ], [3.8, 10.6, 1.6], can_giua={2}, co=11)
    bc.tieu_de("3.6. Cách chạy", 2)
    bc.doan("Hướng dẫn chi tiết cho Windows và VS Code nằm trong `README.md`. Tóm tắt: tạo môi trường ảo `.venv`, cài "
            "`requirements.txt`, chạy `streamlit run src/app.py` từ thư mục gốc. Dữ liệu, kết quả, ảnh và báo cáo có thể tái "
            "lập bằng các script trong `scripts/`.")


def chuong4(bc: BaoCao):
    bc.tieu_de("CHƯƠNG 4. THỰC NGHIỆM VÀ ĐÁNH GIÁ", 1, trang_moi=True)
    bc.tieu_de("4.1. Dữ liệu", 2)
    bc.tieu_de("4.1.1. Nguồn gốc và quy trình sinh dữ liệu", 3)
    bc.doan(f"Do chưa có dữ liệu thực được phép sử dụng, nhóm sinh **dữ liệu mô phỏng** bằng `scripts/generate_data.py` với "
            f"seed {GEN['seed']}. Dữ liệu **không** được thu thập từ website rao bán, sàn giao dịch hay khảo sát chuyên gia. "
            f"Bộ sinh tạo {f(GEN['so_ban_ghi_sinh'], 0)} tin, chọn phiên bản theo độ phổ biến giả định, chọn tuổi xe theo phân bố "
            f"lệch về 3–8 năm, số km theo phân phối log-chuẩn, tình trạng phụ thuộc tuổi, các cờ lịch sử theo xác suất giả "
            f"định, rồi tính giá bằng một **hàm giá ẩn** liên tục (Bảng 4.1). Land Cruiser có độ phổ biến 0 để minh họa thiếu ca.")
    h = GCFG["ham_gia_an"]
    bc.bang("Tham số giả định của bộ sinh dữ liệu (data/generator_config.json)", [
        ["Thành phần", "Giả định"],
        ["Khấu hao theo tuổi", f"{f(h['giu_gia_nam_dau'], 2)}·exp(−λ·(t − 1)), λ theo phân khúc từ {f(min(h['lambda_khau_hao_theo_phan_khuc'].values()), 3)} đến {f(max(h['lambda_khau_hao_theo_phan_khuc'].values()), 3)}; xe 0 tuổi giữ {f(h['giu_gia_xe_moi_0_tuoi'], 2)}"],
        ["Hệ số hãng", "Liên tục theo từng hãng: " + ", ".join(f"{k} {f(v, 3)}" for k, v in h["he_so_hang"].items())],
        ["Số km", f"exp(−{f(h['do_doc_km'], 3)}·(r~km~ − 1)), giới hạn trong [{f(h['he_so_km_min'], 2)}; {f(h['he_so_km_max'], 2)}]; km/năm trung vị {f(GCFG['km_moi_nam']['trung_vi'], 0)} (dịch vụ {f(GCFG['km_moi_nam_dich_vu']['trung_vi'], 0)})"],
        ["Tình trạng", ", ".join(f"{k} {f(v, 3)}" for k, v in h["he_so_tinh_trang"].items())],
        ["Lịch sử, rủi ro", f"bảo dưỡng hãng {f(h['bao_duong_hang'], 3)}; dịch vụ {f(h['chay_dich_vu'], 2)}; ngập {f(h['ngap_nuoc'], 2)}; tai nạn {f(h['tai_nan_nang'], 2)}; cả hai {f(h['ngap_va_tai_nan'], 2)}; số sàn {f(h['hop_so_san'], 3)}"],
        ["Khu vực, mùa vụ", f"Bắc {f(h['he_so_khu_vuc']['Miền Bắc'], 2)}, Trung {f(h['he_so_khu_vuc']['Miền Trung'], 2)}, Nam {f(h['he_so_khu_vuc']['Miền Nam'], 2)}; dao động mùa vụ ±{pt(h['bien_do_mua_vu'] * 100)}"],
        ["Nhiễu", f"nhân exp(ε), ε ~ N(0; {f(h['sigma_nhieu_log'], 3)}); 1,2% xe từ 5 tuổi bị hạ số km hiển thị còn 8–20% (giá vẫn theo km thật)"],
    ], [3.4, 12.6], co=10.5)
    bc.doan("Hàm giá ẩn **khác** tập luật (khấu hao mũ liên tục thay cho bậc tuổi; hệ số riêng từng hãng thay cho 3 nhóm; hệ số "
            "km liên tục; có nhiễu và khu vực) nhưng **chia sẻ cùng loại giả định** với luật (tuổi, km, tình trạng, rủi ro làm "
            "giảm giá). Vì vậy kết quả thực nghiệm chỉ kiểm tra kiến trúc và hành vi thuật toán, không chứng minh độ chính xác "
            "trên thị trường thật.")
    bc.tieu_de("4.1.2. Trường dữ liệu, làm sạch và chia tập", 3)
    bc.bang("Các trường của dữ liệu sau làm sạch", [
        ["Trường", "Kiểu / đơn vị", "Mô tả"],
        ["ma_tin", "chuỗi", "Mã bản ghi (MPxxxxx)"],
        ["hang, dong_xe, phien_ban, phien_ban_id", "chuỗi", "Tên và mã khung phiên bản đã đối chiếu"],
        ["phan_khuc, gia_moi", "chuỗi; triệu đồng", "Kế thừa từ khung (giá mới là giả định)"],
        ["nam_sx, tuoi_xe", "năm", f"Năm sản xuất; tuổi = {KB.nam_dinh_gia} − năm sản xuất"],
        ["so_km", "km", "Số km trên đồng hồ"],
        ["khu_vuc, tinh_trang", "chuỗi", "Miền Bắc/Trung/Nam; Rất tốt/Tốt/Trung bình/Kém"],
        ["bao_duong_hang, chay_dich_vu, ngap_nuoc, tai_nan_nang", "logic", "Lịch sử sử dụng và rủi ro"],
        ["gia, ty_le_gia", "triệu đồng; tỷ lệ", "Giá mô phỏng; giá / giá mới"],
        ["ngay_ghi_nhan, nguon_du_lieu", "ngày; chuỗi", "Tháng 1–10/2026; luôn là “Mô phỏng (seed 2026)”"],
    ], [6.0, 3.6, 6.4], co=10.5)
    hang = [["Bước", "Trước", "Sau", "Loại", "Mô tả"]]
    for b in CLEAN["cac_buoc"]:
        mo = b["mo_ta"] + (f" ({b['so_o_chuan_hoa']} ô được chuẩn hóa)" if "so_o_chuan_hoa" in b else "")
        hang.append([b["buoc"], f(b["truoc"], 0), f(b["sau"], 0), f(b["bi_loai"], 0), mo])
    ct = CLEAN["chia_tap"]
    bc.doan(f"Để minh họa quy trình làm sạch, bộ sinh cố ý chèn lỗi thường gặp của tin rao (giá trị thiếu, tin trùng, gõ nhầm "
            f"giá, năm/km sai, phiên bản lạ, biến thể chữ). `scripts/clean_split.py` loại theo từng bước và ghi số lượng trước/sau "
            f"(Bảng 4.3, Hình 4.1). Bước lọc giá ngoại lai chỉ loại {CLEAN['so_xe_rui_ro_bi_loai_do_ngoai_lai']} xe có cờ rủi ro.")
    bc.bang("Số bản ghi trước/sau từng bước làm sạch", hang, [4.4, 1.4, 1.4, 1.2, 7.6], can_phai={1, 2, 3}, co=10.5)
    bc.doan(f"Dữ liệu sạch gồm {f(ct['so_sach'], 0)} bản ghi, chia **phân tầng theo phân khúc** thành {f(ct['so_train'], 0)} train và "
            f"{f(ct['so_test'], 0)} test (seed 42). Tập test **không** được nạp vào kho tình huống, không dùng huấn luyện RF và "
            "không dùng chọn tham số; kiểm thử tự động xác nhận hai tập không giao nhau.")
    bc.hinh(anh(CHARTS / "ch08_lam_sach_chia_tap.png"), "Số bản ghi sau từng bước làm sạch và phân bố train/test theo phân khúc")
    bc.tieu_de("4.2. Thiết lập thực nghiệm", 2)
    bc.tieu_de("4.2.1. Các phương pháp so sánh", 3)
    bc.gach_dau_dong([
        "**Chỉ luật:** giá theo luật P~luật~ từ máy suy diễn tiến.",
        "**Chỉ CBR:** giá P~CBR~ từ tối đa 5 xe tương tự đã hiệu chỉnh. Lưu ý bước hiệu chỉnh dùng tỷ số giá luật, nên “chỉ CBR” không hoàn toàn độc lập với luật; vì vậy báo cáo thêm biến thể CBR không hiệu chỉnh để đối chiếu.",
        f"**Random Forest:** dự đoán tỷ lệ giá/giá mới từ các đặc trưng xe (mã hóa one-hot), {TUNE['da_chon']['rf']['n_estimators']} cây, tham số chọn trên validation; huấn luyện trên tập train.",
        "**Hệ lai luật + CBR:** giá đề xuất P theo công thức (2.7) – đúng hàm `dinh_gia()` mà giao diện sử dụng.",
    ])
    bc.tieu_de("4.2.2. Chọn tham số trên tập validation", 3)
    tv = TUNE["tap_validation"]
    dc = TUNE["da_chon"]
    bc.doan(f"Tập train được tách tiếp thành {f(tv['so_sub_train'], 0)} bản ghi làm kho tình huống tạm và {f(tv['so_validation'], 0)} "
            "bản ghi validation (phân tầng, seed 7). Quy tắc chọn được ghi trong `scripts/tune_parameters.py`: k cố định bằng 5; "
            "θ là ngưỡng lớn nhất có MAE của CBR không vượt quá MAE tốt nhất 1% và CBR trả kết quả cho ít nhất 95% ca; w~max~ "
            "cho MAE hệ lai nhỏ nhất; δ~min~ nhỏ nhất đạt tỷ lệ trong khoảng ≥ 80%. Quy tắc dung sai 1% cho θ được thêm sau lần "
            "chạy đầu khi thấy MAE gần như không đổi với θ từ 0,60 đến 0,75; việc chọn chỉ dùng validation.")
    bc.hinh(anh(CHARTS / "ch06_chon_tham_so.png"), "Chọn θ, k, w_max và δ_min trên tập validation")
    bc.bang("Tham số của hệ thống và nguồn gốc", [
        ["Tham số", "Giá trị", "Nguồn"],
        ["k (số xe tương tự tối đa)", str(dc["k"]), "Yêu cầu thiết kế; validation cho thấy k = 7 có MAE thấp hơn một chút"],
        ["θ (ngưỡng tương tự)", f(dc["theta"], 2), "Chọn trên validation"],
        ["w_max (trọng số CBR tối đa)", f(dc["w_max"], 2), "Chọn trên validation"],
        ["δ_min", f(dc["delta_min"], 2), "Chọn trên validation (mục tiêu ≥ 80% trong khoảng)"],
        ["δ_max, δ_không_CBR, r", f"{f(CFG['khoang_gia']['delta_max'], 2)}; {f(CFG['khoang_gia']['delta_khong_cbr'], 2)}; {f(CFG['khoang_gia']['cong_them_rui_ro'], 2)}", "Giả định"],
        ["Trọng số 7 tiêu chí, thang đo năm/km", "Bảng 2.6", "Giả định thiết kế"],
        ["RF: min_samples_leaf, max_features", f"{dc['rf']['min_samples_leaf']}; {dc['rf']['max_features']}", "Chọn trên validation (lưới 3 × 3)"],
    ], [5.2, 2.6, 8.2], co=11)
    bc.tieu_de("4.2.3. Chỉ số đánh giá và cách đo", 3)
    bc.doan("Với y~i~ là giá thật, ŷ~i~ là giá dự đoán, n là số ca:")
    bc.cong_thuc(omath(T("MAE"), O(" = "), frac(O("1"), V("n")), nary("∑", V("i"), None, ngoac(sub(V("ŷ"), V("i")) + O(" − ") + sub(V("y"), V("i")), "|", "|")),
                       O(",    "), T("MAPE"), O(" = "), frac(O("100%"), V("n")), nary("∑", V("i"), None, frac(ngoac(sub(V("ŷ"), V("i")) + O(" − ") + sub(V("y"), V("i")), "|", "|"), sub(V("y"), V("i"))))))
    bc.cong_thuc(omath(sup(V("R"), O("2")), O(" = 1 − "), frac(nary("∑", V("i"), None, ngoac(sub(V("y"), V("i")) + O(" − ") + sub(V("ŷ"), V("i"))) + O("²")),
                                                           nary("∑", V("i"), None, ngoac(sub(V("y"), V("i")) + O(" − ") + V("ȳ")) + O("²")))))
    bc.doan(f"Ngoài ra đo tỷ lệ giá thật nằm trong khoảng tham khảo và độ rộng trung bình của khoảng (chỉ với hệ lai). Thời gian "
            f"xử lý đo bằng `time.perf_counter` quanh lệnh dự đoán từng ca, chạy tuần tự trong một tiến trình, bỏ qua 20 ca khởi "
            f"động; RF dự đoán từng ca với 1 luồng. Môi trường: {ENV['cpu']}, {ENV['so_luong_cpu']} CPU, Python {ENV['python']}, "
            f"{ENV['he_dieu_hanh'].split('-with')[0]}; lần chạy {ENV['thoi_diem_chay']}. Thời gian không gồm việc vẽ giao diện "
            "và thay đổi theo máy.")
    bc.tieu_de("4.3. Kết quả", 2)
    hang = [["Phương pháp", "Phạm vi (n)", "MAE (tr)", "MAPE", "R²", "Sai số ≤ 10%", "TG TB (ms)", "TG P95 (ms)"]]
    for p in PP:
        b = BANG[p]
        tg = TIMING[TIMING["phuong_phap"] == p].iloc[0]
        hang.append([p, f"{'có CBR' if p == 'Chỉ CBR' else 'toàn bộ'} ({b['n']})", f(b["MAE"], 2), pt(b["MAPE"], 2), f(b["R2"], 4),
                     pt(b["ty_le_sai_so_duoi_10"]), f(tg["tb_ms"], 2), f(tg["p95_ms"], 2)])
    for ten in ("Chỉ CBR (thiếu ca → giá luật)", "CBR không hiệu chỉnh (ablation)"):
        b = BANG[ten]
        hang.append([ten, f"{'toàn bộ' if 'thiếu ca' in ten else 'có CBR'} ({b['n']})", f(b["MAE"], 2), pt(b["MAPE"], 2), f(b["R2"], 4),
                     pt(b["ty_le_sai_so_duoi_10"]), "—", "—"])
    hl, rf, lu, cbr = BANG["Hệ lai luật + CBR"], BANG["Random Forest"], BANG["Chỉ luật"], BANG["Chỉ CBR"]
    bc.doan(f"Bảng 4.5 là kết quả trên {M['so_test']} ca test. CBR không trả kết quả cho {M['so_ca_test_thieu_cbr']} ca "
            "(một xe Innova đời 2022 không có xe cùng phân khúc đạt ngưỡng), nên dòng “Chỉ CBR” tính trên "
            f"{cbr['n']} ca; dòng “thiếu ca → giá luật” dùng giá luật cho ca đó để so sánh trên toàn bộ tập.")
    bc.bang(f"Kết quả trên tập test ({M['so_test']} ca, dữ liệu mô phỏng)", hang, [4.4, 2.2, 1.6, 1.5, 1.6, 1.7, 1.5, 1.5],
            can_phai={2, 3, 4, 5, 6, 7}, co=10, dong_dam={4})
    bc.hinh(anh(CHARTS / "ch01_so_sanh_sai_so.png"), "So sánh MAE, MAPE và R² của bốn phương pháp")
    hang = [["Phương pháp", "n", "MAE (tr)", "MAPE", "R²"]]
    for _, r in SAME.iterrows():
        hang.append([r["phuong_phap"], str(int(r["n"])), f(r["MAE"], 2), pt(r["MAPE"], 2), f(r["R2"], 4)])
    bc.bang("So sánh bốn phương pháp trên cùng tập con có kết quả CBR", hang, [5.6, 1.6, 2.6, 2.6, 2.6], can_phai={1, 2, 3, 4})
    bs = M["bootstrap_chenh_MAE_he_lai_tru"]
    hang = [["So với", "Chênh MAE (hệ lai − khác)", "Khoảng 95% bootstrap", "Kết luận"]]
    for ten, v in bs.items():
        co_y_nghia = v["ci95_cao"] < 0 or v["ci95_thap"] > 0
        hang.append([ten, f(v["chenh_MAE"], 2) + " tr", f"[{f(v['ci95_thap'], 2)}; {f(v['ci95_cao'], 2)}]",
                     "Khác biệt có ý nghĩa" if co_y_nghia else "Chưa đủ bằng chứng khác biệt"])
    bc.doan("Để biết chênh lệch MAE có đáng tin hay không, nhóm dùng bootstrap ghép cặp 2.000 lần trên tập test (Bảng 4.7). "
            "Khoảng chứa 0 nghĩa là chưa đủ bằng chứng cho thấy hai phương pháp khác nhau.")
    bc.bang("Bootstrap ghép cặp cho chênh lệch MAE", hang, [5.2, 3.6, 3.6, 3.6], can_phai={1, 2})
    bc.hinh(anh(CHARTS / "ch02_thuc_te_du_doan.png"), "Giá thực tế và giá dự đoán trên tập test", 14.5)
    bc.hinh(anh(CHARTS / "ch03_phan_bo_sai_so.png"), "Phân bố sai số phần trăm theo phương pháp")
    g = BY_GROUP
    hang = [["Nhóm ca", "n"] + PP]
    for nhom in ["Thông thường", "Chạy dịch vụ", "Ngập nước/tai nạn nặng"]:
        d = g[g["nhom"] == nhom].set_index("phuong_phap")
        hang.append([nhom, str(int(d.loc["Hệ lai luật + CBR", "n"]))] + [pt(d.loc[p, "MAPE"], 2) for p in PP])
    bc.bang("MAPE theo nhóm ca trên tập test", hang, [4.4, 1.2, 2.5, 2.5, 2.7, 2.7], can_phai={1, 2, 3, 4, 5})
    bc.hinh(anh(CHARTS / "ch04_sai_so_theo_nhom.png"), "MAPE theo nhóm ca: thông thường, chạy dịch vụ, ngập nước/tai nạn nặng")
    kgh = M["khoang_gia_he_lai"]
    hang = [["Mức tin cậy", "Số ca", "MAPE", "Trong khoảng", "Độ rộng TB"]]
    for _, r in BY_CONF.iterrows():
        hang.append([r["muc_tin_cay"], str(int(r["n"])), pt(r["MAPE"], 2), pt(r["ty_le_trong_khoang"]), pt(r["do_rong_tb_phan_tram"])])
    bc.doan(f"Khoảng tham khảo của hệ lai chứa giá thật ở {pt(kgh['ty_le_trong_khoang'])} số ca test, độ rộng trung bình "
            f"{f(kgh['do_rong_tb_trieu'])} triệu đồng ({pt(kgh['do_rong_tb_phan_tram'])} giá đề xuất). Bảng {bc.so_bang_tiep()} "
            f"và Hình {bc.so_hinh_tiep()} phân tích theo mức tin cậy.")
    bc.bang("Kết quả hệ lai theo mức tin cậy", hang, [3.4, 2.0, 3.0, 3.6, 3.6], can_phai={1, 2, 3, 4})
    bc.hinh(anh(CHARTS / "ch07_theo_muc_tin_cay.png"), "MAPE, tỷ lệ trong khoảng và độ rộng khoảng theo mức tin cậy")
    bc.hinh(anh(CHARTS / "ch05_thoi_gian.png"), "Thời gian xử lý mỗi ca trên tập test")

    # ------------------------------------------------------------ ca demo chính
    tc = DEMO["TC01"]
    bc.tieu_de("4.4. Phân tích ca demo chính TC01", 2)
    dv = tc["dau_vao"]
    bc.doan(f"**Đầu vào.** {tc['xe']} đời {dv['nam_sx']}, {f(dv['so_km'], 0)} km, {dv['khu_vuc']}, tình trạng {dv['tinh_trang']}, "
            "có bảo dưỡng tại hãng, không chạy dịch vụ, không ngập nước, không tai nạn (Hình 3.1). Từ khung, hệ thống nạp giá "
            f"mới tham chiếu {f(tc['gia_moi'], 0)} triệu (giả định), phân khúc B, hộp số CVT và nhóm giữ giá “cao” của Toyota.")
    hang = [["Chu kỳ", "Luật", "Điều kiện thỏa", "Giá trước", "Giá sau"]]
    for b in tc["vet"]:
        hang.append([str(b["chu_ky"]), b["ma_luat"], "; ".join(b["dieu_kien_thoa"]),
                     "—" if b["gia_truoc"] is None else f(b["gia_truoc"]), "—" if b["gia_sau"] is None else f(b["gia_sau"])])
    bc.doan("**Suy diễn tiến.** Ở chu kỳ 1, tập xung đột gồm R01 và R03 (giá mới > 0); R01 được chọn vì ưu tiên 100 > 98. "
            "R01 tính tuổi 7 năm, R02 tính tỷ lệ km 95.000 / 105.000 = 0,90 (không thuộc ngưỡng đi ít/đi nhiều). Từ chu kỳ 4, "
            "R25 (trần giá) có mặt trong tập xung đột vì giá tạm 545 > 0,95 × 545 nhưng có ưu tiên thấp nhất; sau khi R07 nhân "
            "0,57 thì điều kiện không còn thỏa nên R25 không bao giờ chạy.")
    bc.bang("Vết suy diễn ca TC01", hang, [1.4, 1.3, 8.7, 2.3, 2.3], can_giua={0, 1}, can_phai={3, 4}, co=10.5)
    bc.doan(f"Giá theo luật: 545 × 0,57 × 1,03 × 1,05 = **{f(tc['gia_luat'], 2)} triệu**, tức giữ {pt(tc['gia_luat'] / tc['gia_moi'] * 100)} giá mới.")
    x3 = tc["xe_tuong_tu"][2]
    bc.doan(f"**Truy hồi CBR.** Lọc cứng phân khúc B, đời 2016–2022 cho {tc['so_ung_vien_cbr']} ứng viên; {tc['so_dat_nguong_cbr']} xe đạt "
            f"Sim ≥ {f(CFG['cbr']['nguong_tuong_tu'], 2)}; hệ thống chọn 5 xe có Sim cao nhất (Bảng 4.11, Hình 3.7).")
    hang = [["#", "Mã tin", "Năm", "Số km", "Tình trạng", "Khu vực", "Giá gốc", "Tỷ số", "Giá hiệu chỉnh", "Sim"]]
    for i, x in enumerate(tc["xe_tuong_tu"], 1):
        hang.append([str(i), x["ma_tin"], str(x["nam_sx"]), f(x["so_km"], 0), x["tinh_trang"], x["khu_vuc"].replace("Miền ", ""),
                     f(x["gia_goc"]), f(x["ty_le_hieu_chinh"], 3), f(x["gia_hieu_chinh"]), f(x["do_tuong_tu"], 4)])
    bc.bang("Năm xe tương tự của TC01 (giá: triệu đồng)", hang, [0.7, 1.8, 1.1, 1.7, 2.0, 1.4, 1.6, 1.4, 2.3, 1.6],
            can_phai={2, 3, 6, 7, 8, 9}, can_giua={0}, co=10)
    w = CFG["cbr"]["trong_so"]
    tcb = x3["tuong_tu_cuc_bo"]
    ten_tc = {"phien_ban": "Phiên bản", "nam_sx": "Năm sản xuất", "so_km": "Số km", "tinh_trang": "Tình trạng",
              "khu_vuc": "Khu vực", "lich_su": "Bảo dưỡng, dịch vụ", "rui_ro": "Ngập, tai nạn"}
    giai = {"phien_ban": "cùng phiên bản → 1", "nam_sx": "cùng 2019 → 1", "so_km": f"1 − |95.000 − {f(x3['so_km'], 0)}| / 100.000",
            "tinh_trang": "Tốt (2) và Trung bình (1): 1 − 1/3", "khu_vuc": "cùng Miền Bắc → 1", "lich_su": "khớp cả hai → 1",
            "rui_ro": "khớp cả hai → 1"}
    hang = [["Tiêu chí", "Cách tính", "sim~i~", "w~i~", "w~i~·sim~i~"]]
    for k in w:
        hang.append([ten_tc[k], giai[k], f(tcb[k], 3), f(w[k], 2), f(w[k] * tcb[k], 4)])
    hang.append(["Tổng", "Σw = 1,00", "", f(sum(w.values()), 2), f(x3["do_tuong_tu"], 4)])
    bc.doan(f"**Ví dụ tính độ tương tự** cho xe #3 ({x3['ma_tin']}: Vios 1.5G CVT 2019, {f(x3['so_km'], 0)} km, tình trạng Trung bình):")
    bc.bang("Tính độ tương tự của xe #3 so với xe TC01", hang, [3.4, 6.4, 2.0, 1.8, 2.4], can_phai={2, 3, 4}, co=10.5, dong_dam={len(hang) - 1})
    tile = x3["ty_le_hieu_chinh"]
    bc.doan(f"**Hiệu chỉnh giá xe #3.** Hai xe chỉ khác nhau về tình trạng: xe cần định giá có tình trạng Tốt (hệ số 1), xe #3 "
            f"Trung bình (R15: 0,92). Do đó P~luật~(C~3~) = {f(x3['gia_luat_ca'], 2)} và tỷ số hiệu chỉnh = {f(tc['gia_luat'], 2)} / "
            f"{f(x3['gia_luat_ca'], 2)} = {f(tile, 4)} = 1/0,92. Giá hiệu chỉnh: {f(x3['gia_goc'])} × {f(tile, 4)} = "
            f"**{f(x3['gia_hieu_chinh'], 2)} triệu** (Hình 3.8). Hai xe #1, #2 cùng mọi yếu tố trong luật nên tỷ số bằng 1; xe #4 đời "
            "2018 (8 tuổi) vẫn thuộc nhóm tuổi 6–8 nên tỷ số cũng bằng 1 – đây là hệ quả của luật dạng bậc.")
    s = [x["do_tuong_tu"] for x in tc["xe_tuong_tu"]]
    p = [x["gia_hieu_chinh"] for x in tc["xe_tuong_tu"]]
    bc.doan(f"**Giá CBR** = Σ Sim·P′ / Σ Sim = {f(sum(a * b for a, b in zip(s, p)), 2)} / {f(sum(s), 4)} = **{f(tc['gia_cbr'], 2)} triệu**; "
            f"Sim TB = {f(tc['sim_tb'], 4)}; CV = {f(tc['cv'], 4)}.")
    bc.doan(f"**Kết hợp.** w~CBR~ = {f(CFG['ket_hop']['w_cbr_toi_da'], 2)} × 5/5 × {f(tc['sim_tb'], 4)} = {f(tc['w_cbr'], 4)}; α = {f(tc['alpha'], 4)}. "
            f"Giá đề xuất P = {f(tc['alpha'], 4)} × {f(tc['gia_luat'], 2)} + {f(tc['w_cbr'], 4)} × {f(tc['gia_cbr'], 2)} = "
            f"**{f(tc['gia_de_xuat'], 2)} triệu**.")
    bc.doan(f"**Khoảng tham khảo.** d = |{f(tc['gia_luat'], 2)} − {f(tc['gia_cbr'], 2)}| / {f(tc['gia_de_xuat'], 2)} = {f(tc['d'], 4)}; "
            f"δ = min(0,25; max(0,10; {f(tc['cv'], 4)}; {f(tc['d'], 4)}) + 0) = {f(tc['delta'], 2)}. Khoảng = "
            f"[{f(tc['khoang_thap'], 1)}; {f(tc['khoang_cao'], 1)}] triệu đồng – đúng như thanh khoảng giá ở Hình 3.3.")
    bc.doan(f"**Mức tin cậy {tc['muc_tin_cay']}:** {' '.join(tc['ly_do_tin_cay'])} Đây là phân loại theo quy tắc, không phải "
            "xác suất giá đúng.")
    bc.tieu_de("4.5. Kết quả các kịch bản mẫu", 2)
    hang = [["Ca", "Xe", "P~luật~", "P~CBR~", "n", "P", "Khoảng", "Tin cậy", "Luật/cảnh báo đáng chú ý"]]
    noi_bat = {"TC01": "R07, R17, R23", "TC02": "R06, R10, R14, R17, R23", "TC03": "R20 (×0,70), cảnh báo nghiêm trọng",
               "TC04": "R12, R15, R18, R19; cảnh báo dịch vụ", "TC05": "Thiếu CBR → α = 1", "TC06": "R22 (×0,62); R20, R21 chỉ cảnh báo",
               "TC07": "R13 chặn R10; nghi chỉnh ODO"}
    for k, c in DEMO.items():
        hang.append([k, c["xe"].replace("Toyota ", "").replace("Hyundai ", "").replace("Mazda ", "").replace("Honda ", "").replace("Kia ", ""),
                     f(c["gia_luat"]), "—" if c["gia_cbr"] is None else f(c["gia_cbr"]), str(c["n_xe_tuong_tu"]),
                     f(c["gia_de_xuat"]), f"{f(c['khoang_thap'])}–{f(c['khoang_cao'])}", c["muc_tin_cay"], noi_bat[k]])
    bc.bang("Kết quả 7 kịch bản mẫu (triệu đồng; lấy từ outputs/results/demo_cases.json)", hang,
            [1.1, 2.6, 1.5, 1.5, 0.7, 1.5, 2.4, 1.6, 3.1], can_phai={2, 3, 5}, can_giua={0, 4}, co=9.5)
    tc7 = DEMO["TC07"]
    bc.doan(f"TC07 cho thấy một trường hợp đáng lưu ý: Mazda3 đời 2018 chỉ 15.000 km bị R13 gắn nghi vấn chỉnh đồng hồ và "
            f"không được cộng điểm đi ít. Giá CBR ({f(tc7['gia_cbr'])}) thấp hơn giá luật ({f(tc7['gia_luat'])}) do các xe tương tự "
            f"có số km bình thường; độ chênh d = {f(tc7['d'], 3)} > 0,10 nên mức tin cậy chỉ là {tc7['muc_tin_cay']} và khoảng giá "
            "rộng hơn – hệ thống thể hiện đúng sự không chắc chắn thay vì đưa ra một con số “đẹp”.")
    bc.tieu_de("4.6. Đánh giá và thảo luận", 2)
    bc.gach_dau_dong([
        f"**Hệ lai tốt hơn rõ rệt so với chỉ luật** (MAE {f(hl['MAE'], 2)} so với {f(lu['MAE'], 2)} triệu; khoảng bootstrap của chênh lệch không chứa 0). Luật dạng bậc là xấp xỉ thô của hàm giá liên tục.",
        f"**Hệ lai, CBR và Random Forest có sai số tương đương.** MAE hệ lai thấp hơn RF {f(abs(bs['Random Forest']['chenh_MAE']), 2)} triệu và thấp hơn CBR {f(abs(bs['Chỉ CBR (thiếu ca → giá luật)']['chenh_MAE']), 2)} triệu, nhưng khoảng 95% bootstrap đều chứa 0 nên **không thể kết luận hệ lai chính xác hơn**. Ưu điểm thực sự của hệ lai là khả năng giải thích và xử lý ca thiếu dữ liệu.",
        f"**Bước hiệu chỉnh bằng luật là quan trọng:** CBR không hiệu chỉnh có MAPE {pt(BANG['CBR không hiệu chỉnh (ablation)']['MAPE'], 2)}, cao hơn nhiều so với {pt(cbr['MAPE'], 2)} khi có hiệu chỉnh.",
        f"**Random Forest yếu ở nhóm rủi ro hiếm** (ngập nước/tai nạn nặng, n = {int(g[(g['nhom'] == 'Ngập nước/tai nạn nặng') & (g['phuong_phap'] == 'Random Forest')]['n'].iloc[0])}): MAPE {pt(g[(g['nhom'] == 'Ngập nước/tai nạn nặng') & (g['phuong_phap'] == 'Random Forest')]['MAPE'].iloc[0], 2)} so với {pt(g[(g['nhom'] == 'Ngập nước/tai nạn nặng') & (g['phuong_phap'] == 'Hệ lai luật + CBR')]['MAPE'].iloc[0], 2)} của hệ lai, vì có ít mẫu huấn luyện; tri thức luật bù đắp được phần này. Ngược lại, ở nhóm thông thường RF có MAPE thấp nhất.",
        f"**Khoảng tham khảo** đạt {pt(kgh['ty_le_trong_khoang'])} trên test, gần mục tiêu 80% đặt trên validation, nhưng đây là hiệu chỉnh kinh nghiệm, không phải khoảng tin cậy thống kê.",
        "**Mức tin cậy theo quy tắc chưa phân biệt được sai số:** MAPE của nhóm Cao, Trung bình và Thấp gần như nhau (Bảng 4.9). Quy tắc hiện có tác dụng chủ yếu là mở rộng khoảng giá và nhắc người dùng thận trọng; cần hiệu chỉnh lại khi có dữ liệu thực.",
        f"**Thời gian xử lý** của hệ lai khoảng {f(TIMING[TIMING['phuong_phap'] == 'Hệ lai luật + CBR']['tb_ms'].iloc[0], 2)} ms/ca, đáp ứng yêu cầu tương tác; RF dự đoán từng ca chậm hơn do chi phí gọi mô hình cho một dòng dữ liệu.",
    ])
    bc.tieu_de("4.7. Giới hạn", 2)
    bc.gach_dau_dong([
        "Dữ liệu là mô phỏng; hàm giá ẩn chia sẻ loại giả định với luật nên kết quả có thể lạc quan hơn so với dữ liệu thực và không chứng minh độ chính xác thị trường.",
        "Giá xe mới, hệ số luật, trọng số độ tương tự là giả định chưa được chuyên gia hoặc dữ liệu xác nhận; một giá mới được dùng cho mọi đời xe.",
        "Chưa mô hình hóa biến động giá theo thời gian, khác biệt thế hệ xe, màu sắc, số chủ, tùy chọn trang bị.",
        "Kiểm tra nhất quán dựa trên lưới điểm hữu hạn; trang quản trị chưa có phân quyền và chưa cho phép chỉnh sửa luật trực tiếp.",
        "Chưa cài bước Retain của CBR (lưu giao dịch mới vào kho) vì chưa có giao dịch thật để xác nhận.",
    ])


def ket_luan(bc: BaoCao):
    bc.tieu_de("KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", 1, trang_moi=True)
    bc.tieu_de("1. Kết quả đạt được", 2)
    bc.doan(f"Nhóm đã xây dựng hoàn chỉnh một KB-DSS định giá xe ô tô cũ gồm khung {KB.thong_ke()['so_phien_ban']} phiên bản, "
            f"tập {len(KB.luat)} luật nạp từ tệp cấu hình có kiểm tra nhất quán, máy suy diễn tiến có giải quyết xung đột và ghi "
            "vết, CBR có trọng số với bước hiệu chỉnh dựa trên luật và cơ chế xử lý thiếu ca, cùng bước kết hợp cho giá đề xuất, "
            "khoảng giá, mức tin cậy theo quy tắc và lời giải thích. Ứng dụng Streamlit bốn trang chạy được, có 7 kịch bản demo, "
            "40 ca kiểm thử tự động đạt và ảnh giao diện chụp từ ứng dụng thật.")
    bc.doan(f"Trên dữ liệu mô phỏng, hệ lai đạt MAE {f(BANG['Hệ lai luật + CBR']['MAE'], 2)} triệu đồng và MAPE "
            f"{pt(BANG['Hệ lai luật + CBR']['MAPE'], 2)}, tốt hơn rõ rệt so với chỉ dùng luật và tương đương Random Forest, "
            "đồng thời giải thích được từng bước. Các kết quả này cần được kiểm chứng lại trên dữ liệu thực.")
    bc.tieu_de("2. Hạn chế", 2)
    bc.doan("Hạn chế lớn nhất là dữ liệu và hệ số đều là giả định; mức tin cậy theo quy tắc chưa phân biệt được sai số; "
            "chưa có bước Retain và phân quyền quản trị (chi tiết ở mục 4.7).")
    bc.tieu_de("3. Hướng phát triển", 2)
    bc.gach_dau_dong([
        "Thu thập dữ liệu giao dịch thực một cách hợp lệ (được phép của nguồn dữ liệu, tuân thủ điều khoản sử dụng), làm sạch và đánh giá lại; giữ tách tập test theo xe/tin trùng.",
        "Phỏng vấn, khảo sát chuyên gia định giá để hiệu chỉnh hệ số luật, trọng số độ tương tự và giá xe mới theo từng đời.",
        "Bổ sung yếu tố thời gian (xu hướng giá), số chủ sở hữu, thế hệ xe; học trọng số độ tương tự từ dữ liệu.",
        "Cài bước Retain có xác nhận giao dịch, nhật ký thay đổi tri thức và phân quyền cho trang quản trị.",
        "Hiệu chuẩn mức tin cậy và khoảng giá trên dữ liệu thực (ví dụ hồi quy phân vị hoặc conformal prediction).",
    ])


def tai_lieu(bc: BaoCao):
    bc.tieu_de("TÀI LIỆU THAM KHẢO", 1, trang_moi=True)
    ds = [
        "D. J. Power, *Decision Support Systems: Concepts and Resources for Managers*. Westport, CT: Quorum Books, 2002. ISBN 156720497X.",
        "S. Russell and P. Norvig, *Artificial Intelligence: A Modern Approach*, 4th ed. Hoboken, NJ: Pearson, 2020. ISBN 9780134610993.",
        "M. Minsky, “A Framework for Representing Knowledge,” MIT Artificial Intelligence Laboratory, AI Memo 306, June 1974. Online: https://dspace.mit.edu/handle/1721.1/6089",
        "J. C. Giarratano and G. D. Riley, *Expert Systems: Principles and Programming*, 4th ed. Boston, MA: Thomson Course Technology, 2005. ISBN 0534384471.",
        "C. L. Forgy, “Rete: A fast algorithm for the many pattern/many object pattern match problem,” *Artificial Intelligence*, vol. 19, no. 1, pp. 17–37, 1982. DOI: 10.1016/0004-3702(82)90020-0.",
        "A. Aamodt and E. Plaza, “Case-based reasoning: Foundational issues, methodological variations, and system approaches,” *AI Communications*, vol. 7, no. 1, pp. 39–59, 1994. DOI: 10.3233/AIC-1994-7104.",
        "J. L. Kolodner, *Case-Based Reasoning*. San Mateo, CA: Morgan Kaufmann, 1993. ISBN 1558602372.",
        "L. Breiman, “Random forests,” *Machine Learning*, vol. 45, no. 1, pp. 5–32, 2001. DOI: 10.1023/A:1010933404324.",
        "F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” *Journal of Machine Learning Research*, vol. 12, pp. 2825–2830, 2011.",
        "Streamlit Inc., “Streamlit documentation” (bao gồm st.testing.v1.AppTest). Online: https://docs.streamlit.io (truy cập 11/2026).",
        "Plotly Technologies Inc., “Plotly Python Open Source Graphing Library.” Online: https://plotly.com/python/ (truy cập 11/2026).",
        "Microsoft, “Playwright for Python.” Online: https://playwright.dev/python/ (truy cập 11/2026).",
        "python-docx contributors, “python-docx documentation.” Online: https://python-docx.readthedocs.io (truy cập 11/2026).",
    ]
    for i, t in enumerate(ds, 1):
        p = bc.doan(f"[{i}] {t}", thut_dau=False, can=WD_ALIGN_PARAGRAPH.LEFT)
        p.paragraph_format.left_indent = Cm(0.9)
        p.paragraph_format.first_line_indent = Cm(-0.9)


def dung(so_trang: dict, muc_du_kien: list) -> BaoCao:
    bc = BaoCao(so_trang=so_trang)
    bc.muc_du_kien = muc_du_kien
    bc.doc.core_properties.title = "Hệ hỗ trợ quyết định dựa trên tri thức cho định giá xe ô tô cũ"
    bc.doc.core_properties.author = "Nhóm 4 – Công nghệ tri thức"
    bc.an_so_trang_phan_dau()
    bia(bc)
    phan_dau(bc)
    mo_dau(bc)
    chuong1(bc)
    chuong2(bc)
    chuong3(bc)
    chuong4(bc)
    ket_luan(bc)
    tai_lieu(bc)
    return bc


# ------------------------------------------------------------------ PDF và số trang
def xuat_pdf(docx: Path) -> Path:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        for c in (r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
            if Path(c).exists():
                soffice = c
    if not soffice:
        raise FileNotFoundError("Không tìm thấy LibreOffice (soffice) để xuất PDF.")
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)],
                   check=True, capture_output=True, timeout=600)
    return docx.with_suffix(".pdf")


def _gon(s: str) -> str:
    return re.sub(r"\s+", "", s).casefold()


def doc_trang_pdf(pdf: Path) -> list[str]:
    try:
        from pypdf import PdfReader
        return [p.extract_text() or "" for p in PdfReader(str(pdf)).pages]
    except ImportError:
        out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
        return out.split("\f")


def tim_so_trang(pdf: Path, muc: list) -> dict:
    trang = [_gon(t) for t in doc_trang_pdf(pdf)]
    # trang đầu phần nội dung: trang có "MỞ ĐẦU" xuất hiện SAU trang danh mục từ viết tắt
    i_vt = next(i for i, t in enumerate(trang) if _gon("DANH MỤC TỪ VIẾT TẮT") in t)
    i_dau = next(i for i in range(i_vt + 1, len(trang)) if trang[i].startswith(_gon("MỞ ĐẦU")) or _gon("MỞ ĐẦU1.Lýdo") in trang[i])
    kq = {}
    vi_tri = i_dau
    for m in muc:
        khoa = _gon(m.khoa_tim)[:42]
        tim = None
        for i in range(vi_tri, len(trang)):
            if khoa in trang[i]:
                tim = i
                break
        if tim is None:
            raise RuntimeError(f"Không tìm thấy '{m.khoa_tim}' trong PDF")
        kq[m.khoa_tim] = str(tim - i_dau + 1)
        if m.loai.startswith("h"):
            vi_tri = tim  # tiêu đề theo thứ tự; hình/bảng có thể nằm cùng trang
    return kq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    docx = OUT / f"{TEN}.docx"
    nhap = dung({}, [])                       # lượt 1: thu thập danh sách tiêu đề, hình, bảng
    muc = nhap.muc
    bc = dung({}, muc)                        # lượt 2: có mục lục (số trang tạm)
    bc.luu(docx)
    if args.no_pdf:
        print("Đã tạo", docx)
        return
    so = tim_so_trang(xuat_pdf(docx), muc)
    for lan in range(3):                      # lượt 3+: điền số trang, kiểm tra ổn định
        bc = dung(so, muc)
        bc.luu(docx)
        moi = tim_so_trang(xuat_pdf(docx), muc)
        if moi == so:
            break
        so = moi
    else:
        print("CẢNH BÁO: số trang trong mục lục chưa ổn định sau 3 lượt.")
    pdf = docx.with_suffix(".pdf")
    tong = len(doc_trang_pdf(pdf))
    with open(OUT / "report_build_log.json", "w", encoding="utf-8") as fh:
        json.dump({"docx": docx.name, "pdf": pdf.name, "so_trang_pdf": tong, "so_hinh": sum(m.loai == "hinh" for m in muc),
                   "so_bang": sum(m.loai == "bang" for m in muc), "so_trang_muc_luc_on_dinh": moi == so,
                   "so_trang": so}, fh, ensure_ascii=False, indent=2)
    print(f"Đã tạo {docx.name} và {pdf.name} ({tong} trang PDF, {sum(m.loai == 'hinh' for m in muc)} hình, "
          f"{sum(m.loai == 'bang' for m in muc)} bảng).")


if __name__ == "__main__":
    main()
