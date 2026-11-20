"""Thư viện nhỏ dựng báo cáo DOCX bằng python-docx.

- Định dạng: A4, Times New Roman 13, giãn dòng 1,3; lề trái 3 cm, lề còn lại 2 cm.
- Đánh số hình/bảng/công thức theo chương; danh mục hình/bảng và mục lục là TRƯỜNG Word (TOC) có sẵn
  nội dung (số trang lấy từ bản PDF đã dựng) – trong Word có thể bấm chuột phải → Update Field để cập nhật.
- Công thức là OMML (Office Math) – chỉnh sửa được trong Word.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Times New Roman"
FONT_CODE = "Consolas"
CO_CHU = 13
RONG_VAN_BAN_CM = 16.0  # 21 − 3 − 2
NS_M = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" ' \
       'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


# ------------------------------------------------------------------ OMML
def _r(t: str, kieu: str = "it") -> str:
    pr = {"it": "", "nor": "<m:rPr><m:nor/></m:rPr>", "p": '<m:rPr><m:sty m:val="p"/></m:rPr>'}[kieu]
    return f'<m:r>{pr}<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr><m:t xml:space="preserve">{escape(t)}</m:t></m:r>'


def V(t):           # biến (nghiêng)
    return _r(t, "it")


def T(t):           # chữ/định danh nhiều ký tự (thẳng)
    return _r(t, "nor")


def O(t):           # toán tử, số
    return _r(t, "p")


def sub(b, s):
    return f"<m:sSub><m:e>{b}</m:e><m:sub>{s}</m:sub></m:sSub>"


def sup(b, s):
    return f"<m:sSup><m:e>{b}</m:e><m:sup>{s}</m:sup></m:sSup>"


def frac(n, d):
    return f"<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>"


def nary(ky_tu, duoi, tren, than):
    an = "" if tren else '<m:supHide m:val="1"/>'
    return (f'<m:nary><m:naryPr><m:chr m:val="{ky_tu}"/><m:limLoc m:val="undOvr"/>{an}</m:naryPr>'
            f"<m:sub>{duoi}</m:sub><m:sup>{tren or ''}</m:sup><m:e>{than}</m:e></m:nary>")


def ngoac(than, mo="(", dong=")"):
    return f'<m:d><m:dPr><m:begChr m:val="{escape(mo)}"/><m:endChr m:val="{escape(dong)}"/></m:dPr><m:e>{than}</m:e></m:d>'


def omath(*phan) -> str:
    return f"<m:oMath {NS_M}>" + "".join(phan) + "</m:oMath>"


# ------------------------------------------------------------------ tiện ích XML
_THU_TU_SECTPR = ["headerReference", "footerReference", "footnotePr", "endnotePr", "type", "pgSz", "pgMar", "paperSrc",
                  "pgBorders", "lnNumType", "pgNumType", "cols", "formProt", "vAlign", "noEndnote", "titlePg",
                  "textDirection", "bidi", "rtlGutter", "docGrid", "printerSettings", "sectPrChange"]


def chen_sectpr(sectpr, el):
    """Chèn phần tử con vào w:sectPr đúng thứ tự lược đồ OOXML (Word không chấp nhận sai thứ tự)."""
    ten = el.tag.split("}")[1]
    sau = _THU_TU_SECTPR[_THU_TU_SECTPR.index(ten) + 1:]
    for con in sectpr:
        if con.tag.split("}")[1] in sau:
            con.addprevious(el)
            return el
    sectpr.append(el)
    return el


# ------------------------------------------------------------------ tài liệu
@dataclass
class MucDanhMuc:
    loai: str          # "h1" | "h2" | "h3" | "hinh" | "bang"
    van_ban: str
    khoa_tim: str      # chuỗi dùng để tìm trang trong PDF
    trang: str = ""


@dataclass
class BaoCao:
    so_trang: dict = field(default_factory=dict)   # khoa_tim -> số trang (chuỗi)
    doc: Document = None
    muc: list = field(default_factory=list)
    chuong: int = 0
    dem_hinh: int = 0
    dem_bang: int = 0
    dem_ct: int = 0
    dem_code: int = 0

    def __post_init__(self):
        self.doc = Document()
        zoom = self.doc.settings.element.find(qn("w:zoom"))
        if zoom is not None and zoom.get(qn("w:percent")) is None:
            zoom.set(qn("w:percent"), "100")
        self._thiet_lap_kieu()
        s = self.doc.sections[0]
        s.page_height, s.page_width = Cm(29.7), Cm(21.0)
        s.left_margin, s.right_margin, s.top_margin, s.bottom_margin = Cm(3), Cm(2), Cm(2), Cm(2)
        s.header_distance, s.footer_distance = Cm(1.0), Cm(1.0)

    # ---------------------------------------------------------------- kiểu
    @staticmethod
    def _font(style_or_run, ten=FONT, co=None, dam=None, nghieng=None, mau=None):
        f = style_or_run.font
        f.name = ten
        if co:
            f.size = Pt(co)
        if dam is not None:
            f.bold = dam
        if nghieng is not None:
            f.italic = nghieng
        if mau is not None:
            f.color.rgb = RGBColor.from_string(mau)
        rpr = style_or_run.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rfonts.set(qn(a), ten)
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rfonts.get(qn(a)) is not None:
                del rfonts.attrib[qn(a)]

    def _thiet_lap_kieu(self):
        st = self.doc.styles
        n = st["Normal"]
        self._font(n, co=CO_CHU)
        pf = n.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pf.line_spacing = 1.3
        pf.space_before, pf.space_after = Pt(0), Pt(6)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.first_line_indent = Cm(1.0)
        pf.widow_control = True
        cau_hinh = {
            "Heading 1": dict(co=14, dam=True, can=WD_ALIGN_PARAGRAPH.CENTER, truoc=0, sau=18, hoa=True),
            "Heading 2": dict(co=13, dam=True, can=WD_ALIGN_PARAGRAPH.LEFT, truoc=12, sau=6, hoa=False),
            "Heading 3": dict(co=13, dam=True, nghieng=True, can=WD_ALIGN_PARAGRAPH.LEFT, truoc=8, sau=4, hoa=False),
        }
        for ten, c in cau_hinh.items():
            s = st[ten]
            self._font(s, co=c["co"], dam=c["dam"], nghieng=c.get("nghieng", False), mau="000000")
            s.paragraph_format.alignment = c["can"]
            s.paragraph_format.space_before = Pt(c["truoc"])
            s.paragraph_format.space_after = Pt(c["sau"])
            s.paragraph_format.first_line_indent = Cm(0)
            s.paragraph_format.keep_with_next = True
            s.paragraph_format.line_spacing = 1.2
            s.font.all_caps = c["hoa"]
        for ten, can in (("Chu thich hinh", WD_ALIGN_PARAGRAPH.CENTER), ("Chu thich bang", WD_ALIGN_PARAGRAPH.CENTER)):
            s = st.add_style(ten, WD_STYLE_TYPE.PARAGRAPH)
            s.base_style = n
            self._font(s, co=12, nghieng=True)
            s.paragraph_format.alignment = can
            s.paragraph_format.first_line_indent = Cm(0)
            s.paragraph_format.space_before = Pt(3)
            s.paragraph_format.space_after = Pt(10)
            s.paragraph_format.line_spacing = 1.15
        st["Chu thich bang"].paragraph_format.keep_with_next = True
        st["Chu thich bang"].paragraph_format.space_after = Pt(4)
        s = st.add_style("Bang noi dung", WD_STYLE_TYPE.PARAGRAPH)
        s.base_style = n
        self._font(s, co=11.5)
        s.paragraph_format.first_line_indent = Cm(0)
        s.paragraph_format.space_after = Pt(0)
        s.paragraph_format.line_spacing = 1.1
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        s = st.add_style("Ma nguon", WD_STYLE_TYPE.PARAGRAPH)
        s.base_style = n
        self._font(s, ten=FONT_CODE, co=8)
        s.paragraph_format.first_line_indent = Cm(0)
        s.paragraph_format.space_after = Pt(0)
        s.paragraph_format.line_spacing = 1.0
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        s = st.add_style("Muc luc", WD_STYLE_TYPE.PARAGRAPH)
        s.base_style = n
        s.paragraph_format.first_line_indent = Cm(0)
        s.paragraph_format.space_after = Pt(2)
        s.paragraph_format.line_spacing = 1.15
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for ten in ("List Bullet", "List Number"):
            s = st[ten]
            self._font(s, co=CO_CHU)
            s.paragraph_format.line_spacing = 1.3
            s.paragraph_format.space_after = Pt(3)
            s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # ---------------------------------------------------------------- văn bản có định dạng
    _MAU = re.compile(r"(\*\*.+?\*\*|\*.+?\*|`.+?`|~.+?~|\^.+?\^)")

    def _them_run(self, p, van_ban: str, dam=False, nghieng=False, co=None):
        for phan in self._MAU.split(van_ban):
            if not phan:
                continue
            r = None
            if phan.startswith("**") and phan.endswith("**"):
                r = p.add_run(phan[2:-2])
                r.bold = True
            elif phan.startswith("*") and phan.endswith("*") and len(phan) > 2:
                r = p.add_run(phan[1:-1])
                r.italic = True
            elif phan.startswith("`") and phan.endswith("`"):
                r = p.add_run(phan[1:-1])
                self._font(r, ten=FONT_CODE, co=(co or CO_CHU) - 2)
            elif phan.startswith("~") and phan.endswith("~"):
                r = p.add_run(phan[1:-1])
                r.font.subscript = True
            elif phan.startswith("^") and phan.endswith("^"):
                r = p.add_run(phan[1:-1])
                r.font.superscript = True
            else:
                r = p.add_run(phan)
            if dam:
                r.bold = True
            if nghieng:
                r.italic = True
            if co:
                r.font.size = Pt(co)
        return p

    def doan(self, van_ban: str, can=None, thut_dau=True, dam=False, nghieng=False, co=None, sau=None, giu_tiep=False):
        p = self.doc.add_paragraph()
        self._them_run(p, van_ban, dam, nghieng, co)
        if can is not None:
            p.alignment = can
        if not thut_dau:
            p.paragraph_format.first_line_indent = Cm(0)
        if sau is not None:
            p.paragraph_format.space_after = Pt(sau)
        if giu_tiep or van_ban.rstrip().endswith(":"):
            p.paragraph_format.keep_with_next = True   # câu dẫn luôn đi cùng công thức/bảng/mã ngay sau
        return p

    def gach_dau_dong(self, cac_y: list[str], so: bool = False):
        for y in cac_y:
            p = self.doc.add_paragraph(style="List Number" if so else "List Bullet")
            self._them_run(p, y)

    def tieu_de(self, van_ban: str, cap: int, vao_muc_luc: bool = True, trang_moi: bool = False):
        if trang_moi:
            self.ngat_trang()
        if cap == 1 and van_ban.upper().startswith("CHƯƠNG"):
            self.chuong += 1
            self.dem_hinh = self.dem_bang = self.dem_ct = self.dem_code = 0
        h = self.doc.add_heading(level=cap)
        h.add_run(van_ban)
        if vao_muc_luc:
            self.muc.append(MucDanhMuc(f"h{cap}", van_ban, van_ban))
        return h

    def tieu_de_phu(self, van_ban: str):
        """Tiêu đề trang không đưa vào mục lục (MỤC LỤC, DANH MỤC…)."""
        p = self.doc.add_paragraph()
        r = p.add_run(van_ban.upper())
        r.bold = True
        r.font.size = Pt(14)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(14)
        return p

    def ngat_trang(self):
        p = self.doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(0)
        p.add_run().add_break(WD_BREAK.PAGE)

    # ---------------------------------------------------------------- hình, bảng, công thức, mã nguồn
    def so_hinh_tiep(self) -> str:
        return f"{self.chuong}.{self.dem_hinh + 1}"

    def so_bang_tiep(self) -> str:
        return f"{self.chuong}.{self.dem_bang + 1}"

    def hinh(self, duong_dan: Path, chu_thich: str, rong_cm: float = RONG_VAN_BAN_CM, cao_toi_da_cm: float = 21.5) -> str:
        from PIL import Image
        with Image.open(duong_dan) as im:
            w, h = im.size
        rong = min(rong_cm, RONG_VAN_BAN_CM)
        if rong * h / w > cao_toi_da_cm:
            rong = cao_toi_da_cm * w / h
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        p.add_run().add_picture(str(duong_dan), width=Cm(rong))
        self.dem_hinh += 1
        so = f"{self.chuong}.{self.dem_hinh}"
        nhan = f"Hình {so}. {chu_thich}"
        c = self.doc.add_paragraph(style="Chu thich hinh")
        c.add_run(nhan)
        self.muc.append(MucDanhMuc("hinh", nhan, f"Hình {so}. {chu_thich[:40]}"))
        return so

    def bang(self, tieu_de: str, hang: list[list], rong_cot_cm: list[float], can_phai: set[int] = frozenset(),
             can_giua: set[int] = frozenset(), co: float = 11.5, dong_dam: set[int] = frozenset()) -> str:
        self.dem_bang += 1
        so = f"{self.chuong}.{self.dem_bang}"
        nhan = f"Bảng {so}. {tieu_de}"
        c = self.doc.add_paragraph(style="Chu thich bang")
        c.add_run(nhan)
        self.muc.append(MucDanhMuc("bang", nhan, f"Bảng {so}. {tieu_de[:40]}"))
        t = self.doc.add_table(rows=len(hang), cols=len(hang[0]))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.style = "Table Grid"
        t.autofit = False
        for i, dong in enumerate(hang):
            tr = t.rows[i]
            if i == 0:
                trpr = tr._tr.get_or_add_trPr()
                el = OxmlElement("w:tblHeader")
                el.set(qn("w:val"), "true")
                trpr.append(el)
            trpr = tr._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit")
            cs.set(qn("w:val"), "true")
            trpr.append(cs)
            for j, gt in enumerate(dong):
                o = tr.cells[j]
                o.width = Cm(rong_cot_cm[j])
                p = o.paragraphs[0]
                p.style = "Bang noi dung"
                self._them_run(p, str(gt), dam=(i == 0 or i in dong_dam), co=co)
                if i == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    tcpr = o._tc.get_or_add_tcPr()
                    sh = OxmlElement("w:shd")
                    sh.set(qn("w:val"), "clear")
                    sh.set(qn("w:color"), "auto")
                    sh.set(qn("w:fill"), "DCE6F2")
                    tcpr.append(sh)
                elif j in can_phai:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                elif j in can_giua:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                tcpr = o._tc.get_or_add_tcPr()
                mar = OxmlElement("w:tcMar")
                for canh, v in (("top", 30), ("left", 70), ("bottom", 30), ("right", 70)):   # đúng thứ tự lược đồ
                    e = OxmlElement(f"w:{canh}")
                    e.set(qn("w:w"), str(v))
                    e.set(qn("w:type"), "dxa")
                    mar.append(e)
                tcpr.append(mar)
        # bảng ngắn: giữ cả bảng trên một trang (giữ dòng với dòng kế tiếp)
        if len(hang) <= 14:
            for tr in t.rows[:-1]:
                for o in tr.cells:
                    for p in o.paragraphs:
                        p.paragraph_format.keep_with_next = True
        # độ rộng lưới bảng
        grid = t._tbl.tblGrid
        for gc, w in zip(grid.findall(qn("w:gridCol")), rong_cot_cm):
            gc.set(qn("w:w"), str(int(w * 567)))
        sau = self.doc.add_paragraph()
        sau.paragraph_format.space_after = Pt(4)
        sau.paragraph_format.line_spacing = 0.8
        return so

    def cong_thuc(self, omml: str) -> str:
        self.dem_ct += 1
        so = f"({self.chuong}.{self.dem_ct})"
        p = self.doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(RONG_VAN_BAN_CM / 2), WD_TAB_ALIGNMENT.CENTER)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(RONG_VAN_BAN_CM), WD_TAB_ALIGNMENT.RIGHT)
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(6)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.add_run("\t")
        p._p.append(parse_xml(omml))
        p.add_run("\t" + so)
        return so

    def ma_nguon(self, dong: list[str], chu_thich: str):
        self.dem_code += 1
        so = f"{self.chuong}.{self.dem_code}"
        c = self.doc.add_paragraph(style="Chu thich bang")
        c.add_run(f"Đoạn mã {so}. {chu_thich}")
        for i, d in enumerate(dong):
            p = self.doc.add_paragraph(style="Ma nguon")
            p.add_run(d.replace("\t", "    ") if d else " ")
            ppr = p._p.get_or_add_pPr()
            sh = OxmlElement("w:shd")
            sh.set(qn("w:val"), "clear")
            sh.set(qn("w:color"), "auto")
            sh.set(qn("w:fill"), "F3F5F9")
            ppr.append(sh)
            p.paragraph_format.left_indent = Cm(0.3)
            if i < len(dong) - 1:
                p.paragraph_format.keep_with_next = True
        sau = self.doc.add_paragraph()
        sau.paragraph_format.space_after = Pt(4)
        sau.paragraph_format.line_spacing = 0.8
        return so

    # ---------------------------------------------------------------- mục lục / danh mục dạng trường Word
    def _run_truong(self, p, loai: str, lenh: str = ""):
        r = p.add_run()
        if loai == "begin":
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), "begin")
            fc.set(qn("w:dirty"), "false")
            r._r.append(fc)
        elif loai == "instr":
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = lenh
            r._r.append(it)
        else:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), loai)
            r._r.append(fc)

    def danh_muc(self, loai: set[str], lenh: str):
        """Chèn trường TOC với nội dung sẵn (văn bản ... số trang)."""
        muc = [m for m in self.muc_du_kien if m.loai in loai]
        if not muc:
            self.doan("(Chưa có mục)")
            return
        for i, m in enumerate(muc):
            p = self.doc.add_paragraph(style="Muc luc")
            thut = {"h1": 0, "h2": 0.6, "h3": 1.2}.get(m.loai, 0)
            p.paragraph_format.left_indent = Cm(thut)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(RONG_VAN_BAN_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
            if i == 0:
                self._run_truong(p, "begin")
                self._run_truong(p, "instr", lenh)
                self._run_truong(p, "separate")
            r = p.add_run(m.van_ban)
            if m.loai == "h1":
                r.bold = True
            p.add_run("\t" + self.so_trang.get(m.khoa_tim, "0"))
            if i == len(muc) - 1:
                self._run_truong(p, "end")

    # ---------------------------------------------------------------- đánh số trang
    def _chan_trang(self, section, dinh_dang: str | None, bat_dau: int | None):
        section.footer.is_linked_to_previous = False
        ft = section.footer
        p = ft.paragraphs[0] if ft.paragraphs else ft.add_paragraph()
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
        sectpr = section._sectPr
        for e in sectpr.findall(qn("w:pgNumType")):
            sectpr.remove(e)
        if dinh_dang is None:
            return
        pg = OxmlElement("w:pgNumType")
        pg.set(qn("w:fmt"), dinh_dang)
        if bat_dau is not None:
            pg.set(qn("w:start"), str(bat_dau))
        chen_sectpr(sectpr, pg)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        self._run_truong(p, "begin")
        self._run_truong(p, "instr", " PAGE ")
        self._run_truong(p, "separate")
        r = p.add_run("1")
        r.font.size = Pt(12)
        self._run_truong(p, "end")

    def phan_moi(self, dinh_dang: str | None, bat_dau: int | None = 1):
        s = self.doc.add_section(WD_SECTION.NEW_PAGE)
        s.page_height, s.page_width = Cm(29.7), Cm(21.0)
        s.left_margin, s.right_margin, s.top_margin, s.bottom_margin = Cm(3), Cm(2), Cm(2), Cm(2)
        for e in s._sectPr.findall(qn("w:pgBorders")):   # viền trang chỉ dành cho bìa
            s._sectPr.remove(e)
        self._chan_trang(s, dinh_dang, bat_dau)
        return s

    def an_so_trang_phan_dau(self):
        self._chan_trang(self.doc.sections[0], None, None)

    def luu(self, duong_dan: Path):
        duong_dan.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(duong_dan))
