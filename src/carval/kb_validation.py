"""Kiểm tra cơ sở tri thức: cấu trúc, kiểu dữ liệu, tham chiếu chéo và nhất quán logic.

Mọi vấn đề được trả về dưới dạng danh sách có chỉ rõ đối tượng cần sửa (luật, khung, kịch bản,
tình huống) để hiển thị trên trang Quản trị tri thức.

Lưu ý: kiểm tra chồng lấn/bao phủ dựa trên lưới điểm biên hữu hạn sinh từ các ngưỡng trong luật,
không phải chứng minh hình thức cho mọi biểu thức.
"""
from __future__ import annotations

import itertools
import re
from dataclasses import asdict, dataclass

from .inference import HAM_SUY_DIEN, LOAI_HANH_DONG, PHEP_SO, PHEP_SO_SANH, ForwardChainingEngine
from .kb import DieuKien, KnowledgeBase

TRUONG_BAT_BUOC_LUAT = ["id", "nhom", "ten", "uu_tien", "dieu_kien", "hanh_dong", "giai_thich"]
HE_SO_TOI_DA = 1.5


@dataclass
class VanDe:
    muc: str          # "loi" | "canh_bao"
    loai: str         # nhóm kiểm tra
    doi_tuong: str    # "Luật R06", "Khung toyota-vios-15g-cvt", ...
    thong_diep: str

    def to_dict(self) -> dict:
        return asdict(self)


def _thoa_tat_ca(dieu_kien: list[DieuKien], wm: dict) -> bool:
    try:
        return all(ForwardChainingEngine.thoa(dk, wm) for dk in dieu_kien)
    except (ValueError, TypeError):
        return False


def _la_so(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class KiemTraTriThuc:
    def __init__(self, frames: dict, rules: dict, config: dict, scenarios: dict | None = None):
        self.frames = frames
        self.rules = rules
        self.config = config
        self.scenarios = scenarios or {"kich_ban": []}
        self.van_de: list[VanDe] = []
        self.da_kiem_tra: list[dict] = []
        self.du_kien = config.get("du_kien", {})
        self.gia_tri_hop_le = config.get("gia_tri_hop_le", {})
        self.ten_hang = {h.get("ten") for h in frames.get("hang_xe", [])}
        self.ten_dong = {d.get("ten") for h in frames.get("hang_xe", []) for d in h.get("dong_xe", [])}
        self.ma_phan_khuc = {p.get("ma") for p in frames.get("phan_khuc", [])}
        self.ma_phien_ban = {
            p.get("id") for h in frames.get("hang_xe", []) for d in h.get("dong_xe", []) for p in d.get("phien_ban", [])
        }

    # ------------------------------------------------------------- tiện ích
    def _loi(self, loai, doi_tuong, thong_diep):
        self.van_de.append(VanDe("loi", loai, doi_tuong, thong_diep))

    def _canh_bao(self, loai, doi_tuong, thong_diep):
        self.van_de.append(VanDe("canh_bao", loai, doi_tuong, thong_diep))

    def _ghi(self, ten: str, so_doi_tuong: int, loai: str):
        loi = sum(1 for v in self.van_de if v.loai == loai and v.muc == "loi")
        cb = sum(1 for v in self.van_de if v.loai == loai and v.muc == "canh_bao")
        self.da_kiem_tra.append({"kiem_tra": ten, "so_doi_tuong": so_doi_tuong, "so_loi": loi, "so_canh_bao": cb})

    def _gia_tri_cho_phep(self, du_kien: str):
        """Tập giá trị hợp lệ của dữ kiện phân loại (None nếu không giới hạn)."""
        if du_kien == "hang":
            return self.ten_hang
        if du_kien == "dong_xe":
            return self.ten_dong
        if du_kien == "phan_khuc":
            return self.ma_phan_khuc
        if du_kien == "phien_ban":
            return self.ma_phien_ban
        khoa = self.du_kien.get(du_kien, {}).get("gia_tri")
        if khoa:
            return set(self.gia_tri_hop_le.get(khoa, []))
        return None

    def _kiem_gia_tri(self, ma: str, du_kien: str, kieu: str, v) -> None:
        dt = f"Luật {ma}"
        if kieu == "so" and not _la_so(v):
            self._loi("Kiểu dữ liệu", dt, f"Điều kiện trên '{du_kien}' (kiểu số) có giá trị {v!r} không phải số.")
        elif kieu == "logic" and not isinstance(v, bool):
            self._loi("Kiểu dữ liệu", dt, f"Điều kiện trên '{du_kien}' (kiểu logic) phải là true/false, nhận {v!r}.")
        elif kieu == "chuoi":
            if not isinstance(v, str):
                self._loi("Kiểu dữ liệu", dt, f"Điều kiện trên '{du_kien}' (kiểu chuỗi) nhận {v!r}.")
                return
            cho_phep = self._gia_tri_cho_phep(du_kien)
            if cho_phep is not None and v not in cho_phep:
                self._loi("Tham chiếu", dt,
                          f"Giá trị '{v}' của '{du_kien}' không có trong khung/cấu hình "
                          f"(hợp lệ: {', '.join(sorted(cho_phep))[:160]}).")

    # ------------------------------------------------------------- tập luật
    def kiem_tra_cau_truc_luat(self):
        luat = self.rules.get("luat", [])
        loai = "Cấu trúc luật"
        if not luat:
            self._loi(loai, "Tập luật", "Tệp luật không có luật nào.")
        dem: dict[str, int] = {}
        for i, r in enumerate(luat):
            ma = r.get("id") or f"#{i + 1}"
            for t in TRUONG_BAT_BUOC_LUAT:
                if t not in r or r[t] in (None, "", []):
                    self._loi(loai, f"Luật {ma}", f"Thiếu trường bắt buộc '{t}'.")
            if r.get("id") and not re.fullmatch(r"R\d{2,3}", r["id"]):
                self._canh_bao(loai, f"Luật {ma}", "Mã luật nên có dạng R + 2–3 chữ số.")
            dem[ma] = dem.get(ma, 0) + 1
            if r.get("nhom") and r["nhom"] not in self.config.get("nhom_luat", {}):
                self._loi(loai, f"Luật {ma}", f"Nhóm '{r['nhom']}' chưa khai báo trong config.nhom_luat.")
            if "uu_tien" in r and not (isinstance(r["uu_tien"], int) and not isinstance(r["uu_tien"], bool)):
                self._loi(loai, f"Luật {ma}", "Độ ưu tiên phải là số nguyên.")
        for ma, n in dem.items():
            if n > 1:
                self._loi("Mã trùng", f"Luật {ma}", f"Mã luật bị dùng {n} lần; mỗi luật cần mã duy nhất.")
        self._ghi("Cấu trúc và trường bắt buộc của luật", len(luat), loai)
        self._ghi("Mã luật duy nhất", len(luat), "Mã trùng")

    def kiem_tra_dieu_kien(self):
        so_dk = 0
        for r in self.rules.get("luat", []):
            ma = r.get("id", "?")
            for dk in r.get("dieu_kien", []) or []:
                so_dk += 1
                ten = dk.get("du_kien")
                phep = dk.get("phep")
                if ten not in self.du_kien:
                    self._loi("Tham chiếu", f"Luật {ma}", f"Dữ kiện '{ten}' chưa khai báo trong config.du_kien.")
                    continue
                if phep not in PHEP_SO_SANH:
                    self._loi("Kiểu dữ liệu", f"Luật {ma}", f"Phép so sánh '{phep}' không hỗ trợ.")
                    continue
                kieu = self.du_kien[ten]["kieu"]
                if phep in ("ton_tai", "khong_ton_tai"):
                    continue
                if phep in PHEP_SO and kieu != "so":
                    self._loi("Kiểu dữ liệu", f"Luật {ma}", f"Phép '{phep}' chỉ dùng cho dữ kiện số, '{ten}' là {kieu}.")
                    continue
                if "tham_chieu" in dk:
                    tc = dk["tham_chieu"]
                    if tc not in self.du_kien:
                        self._loi("Tham chiếu", f"Luật {ma}", f"Dữ kiện tham chiếu '{tc}' chưa khai báo.")
                    elif self.du_kien[tc]["kieu"] != "so":
                        self._loi("Kiểu dữ liệu", f"Luật {ma}", f"Dữ kiện tham chiếu '{tc}' phải là số.")
                    if not _la_so(dk.get("he_so", 1.0)):
                        self._loi("Kiểu dữ liệu", f"Luật {ma}", "Hệ số của tham chiếu phải là số.")
                    continue
                if "gia_tri" not in dk:
                    self._loi("Cấu trúc luật", f"Luật {ma}", f"Điều kiện trên '{ten}' thiếu 'gia_tri' hoặc 'tham_chieu'.")
                    continue
                v = dk["gia_tri"]
                if phep in ("trong", "ngoai"):
                    if not isinstance(v, list):
                        self._loi("Kiểu dữ liệu", f"Luật {ma}", f"Phép '{phep}' cần danh sách giá trị.")
                        continue
                    for x in v:
                        self._kiem_gia_tri(ma, ten, kieu, x)
                else:
                    self._kiem_gia_tri(ma, ten, kieu, v)
        self._ghi("Điều kiện: dữ kiện đã khai báo, phép so sánh, kiểu giá trị", so_dk, "Kiểu dữ liệu")
        self._ghi("Tham chiếu tới khung và giá trị hợp lệ", so_dk, "Tham chiếu")

    def kiem_tra_hanh_dong(self):
        so_hd = 0
        loai = "Hành động"
        for r in self.rules.get("luat", []):
            ma = r.get("id", "?")
            hds = r.get("hanh_dong", []) or []
            co_nhan_gia = False
            for hd in hds:
                so_hd += 1
                l = hd.get("loai")
                if l not in LOAI_HANH_DONG:
                    self._loi(loai, f"Luật {ma}", f"Loại hành động '{l}' không hỗ trợ (hợp lệ: {', '.join(sorted(LOAI_HANH_DONG))}).")
                    continue
                if l in ("nhan_gia", "dat_gia"):
                    hs = hd.get("he_so", 1.0 if l == "dat_gia" else None)
                    if not _la_so(hs):
                        self._loi(loai, f"Luật {ma}", f"Hệ số của '{l}' phải là số, nhận {hs!r}.")
                    elif not (0 < hs <= HE_SO_TOI_DA):
                        self._loi(loai, f"Luật {ma}", f"Hệ số {str(hs).replace('.', ',')} ngoài khoảng (0; {str(HE_SO_TOI_DA).replace('.', ',')}].")
                    if l == "nhan_gia":
                        co_nhan_gia = True
                    if l == "dat_gia":
                        theo = hd.get("theo")
                        if theo not in self.du_kien or self.du_kien[theo]["kieu"] != "so":
                            self._loi("Tham chiếu", f"Luật {ma}", f"'dat_gia' tham chiếu dữ kiện số không hợp lệ: {theo!r}.")
                elif l == "suy_dien":
                    if hd.get("ham") not in HAM_SUY_DIEN:
                        self._loi("Tham chiếu", f"Luật {ma}",
                                  f"Hàm suy diễn '{hd.get('ham')}' không tồn tại (có: {', '.join(HAM_SUY_DIEN)}).")
                    dk = hd.get("du_kien")
                    if dk not in self.du_kien:
                        self._loi("Tham chiếu", f"Luật {ma}", f"Dữ kiện đích '{dk}' chưa khai báo.")
                    elif self.du_kien[dk].get("nguon") != "suy_dien":
                        self._loi(loai, f"Luật {ma}", f"Dữ kiện '{dk}' không thuộc nguồn 'suy_dien', không được ghi đè.")
                elif l == "canh_bao":
                    if hd.get("muc") not in self.gia_tri_hop_le.get("muc_canh_bao", []):
                        self._loi(loai, f"Luật {ma}", f"Mức cảnh báo '{hd.get('muc')}' không hợp lệ.")
                    if not hd.get("noi_dung"):
                        self._loi(loai, f"Luật {ma}", "Cảnh báo thiếu nội dung.")
            if r.get("nhom_loai_tru") and not co_nhan_gia:
                self._canh_bao(loai, f"Luật {ma}", "Khai báo nhóm loại trừ nhưng không có hành động nhân giá.")
            # mẫu giải thích
            for ph in re.findall(r"\{(\w+)\}", r.get("giai_thich", "") or ""):
                if ph not in self.du_kien:
                    self._loi("Tham chiếu", f"Luật {ma}", f"Mẫu giải thích dùng biến '{{{ph}}}' chưa khai báo.")
        self._ghi("Hành động: loại, hệ số trong (0; 1,5], hàm suy diễn tồn tại", so_hd, loai)

    def kiem_tra_logic(self):
        luat_list = self.rules.get("luat", [])
        loai = "Logic"
        # 1) Điều kiện mâu thuẫn trên cùng dữ kiện số
        for r in luat_list:
            ma = r.get("id", "?")
            duoi: dict[str, float] = {}
            tren: dict[str, float] = {}
            for dk in r.get("dieu_kien", []) or []:
                v = dk.get("gia_tri")
                if not _la_so(v):
                    continue
                t = dk.get("du_kien")
                if dk.get("phep") in (">", ">="):
                    duoi[t] = max(duoi.get(t, float("-inf")), v)
                elif dk.get("phep") in ("<", "<="):
                    tren[t] = min(tren.get(t, float("inf")), v)
            for t in duoi:
                if t in tren and duoi[t] > tren[t]:
                    self._loi(loai, f"Luật {ma}",
                              f"Điều kiện không thể đồng thời thỏa: cận dưới của {t} ({duoi[t]}) lớn hơn cận trên ({tren[t]}) → luật không bao giờ kích hoạt.")
        # 2) Hai luật có tập điều kiện giống hệt nhau
        chu_ky: dict[str, str] = {}
        for r in luat_list:
            khoa = repr(sorted((d.get("du_kien"), d.get("phep"), repr(d.get("gia_tri")), d.get("tham_chieu"))
                               for d in r.get("dieu_kien", []) or []))
            if khoa in chu_ky:
                self._canh_bao(loai, f"Luật {r.get('id')}", f"Có cùng tập điều kiện với luật {chu_ky[khoa]} (có thể dư thừa).")
            else:
                chu_ky[khoa] = r.get("id")
        # 3) Dữ kiện suy diễn được dùng nhưng không luật nào sinh ra
        sinh_ra = {hd.get("du_kien") for r in luat_list for hd in r.get("hanh_dong", []) or [] if hd.get("loai") == "suy_dien"}
        sinh_ra.add("gia")
        for r in luat_list:
            for dk in r.get("dieu_kien", []) or []:
                t = dk.get("du_kien")
                if t in self.du_kien and self.du_kien[t].get("nguon") == "suy_dien" and t not in sinh_ra \
                        and dk.get("phep") != "khong_ton_tai":
                    self._loi(loai, f"Luật {r.get('id')}", f"Dữ kiện suy diễn '{t}' không được luật nào sinh ra → luật không thể kích hoạt.")
        self._ghi("Điều kiện mâu thuẫn, luật trùng điều kiện, dữ kiện không được sinh ra", len(luat_list), loai)

    def _luoi_diem(self, luat_nhom: list[DieuKien]) -> tuple[list[str], list[list]]:
        """Sinh lưới điểm kiểm tra từ các ngưỡng xuất hiện trong điều kiện."""
        cac_du_kien: dict[str, set] = {}
        for dk in luat_nhom:
            t = dk.du_kien
            if t not in self.du_kien:
                continue
            kieu = self.du_kien[t]["kieu"]
            s = cac_du_kien.setdefault(t, set())
            if dk.phep in ("ton_tai", "khong_ton_tai"):
                s.add(None)
                s.add(True if kieu == "logic" else (1 if kieu == "so" else "x"))
            elif kieu == "so" and _la_so(dk.gia_tri):
                for eps in (-0.01, 0, 0.01):
                    s.add(round(dk.gia_tri + eps, 4))
                s.update({0, 1000})
            elif kieu == "logic":
                s.update({True, False})
            elif kieu == "chuoi":
                cho_phep = self._gia_tri_cho_phep(t)
                if cho_phep:
                    s.update(cho_phep)
                elif isinstance(dk.gia_tri, str):
                    s.add(dk.gia_tri)
        ten = list(cac_du_kien)
        gia_tri = [sorted(cac_du_kien[t], key=lambda x: (x is None, x if isinstance(x, str) else (float(x) if x is not None else 0.0)))
                   for t in ten]
        return ten, gia_tri

    def kiem_tra_loai_tru_va_bao_phu(self, kb: KnowledgeBase):
        loai = "Chồng lấn/bao phủ"
        so_diem = 0
        for nhom in self.config.get("nhom_loai_tru_theo_dieu_kien", []):
            luat_nhom = [l for l in kb.luat if l.nhom == nhom]
            if len(luat_nhom) < 2:
                continue
            ten, gia_tri = self._luoi_diem([dk for l in luat_nhom for dk in l.dieu_kien])
            da_bao: set[tuple] = set()
            for diem in itertools.product(*gia_tri):
                so_diem += 1
                wm = {t: v for t, v in zip(ten, diem) if v is not None}
                kich_hoat = [l.id for l in luat_nhom if _thoa_tat_ca(l.dieu_kien, wm)]
                if len(kich_hoat) > 1:
                    cap = tuple(sorted(kich_hoat))
                    if cap in da_bao:
                        continue
                    da_bao.add(cap)
                    mo_ta = ", ".join(f"{t}={v}" for t, v in wm.items())
                    self._loi(loai, f"Luật {' & '.join(cap)}",
                              f"Nhóm {nhom} phải loại trừ lẫn nhau nhưng cùng kích hoạt tại {mo_ta}.")
        nhom_tuoi = self.config.get("nhom_bao_phu_tuoi")
        if nhom_tuoi:
            luat_tuoi = [l for l in kb.luat if l.nhom == nhom_tuoi]
            thieu = []
            for tuoi in range(0, 41):
                so_diem += 1
                n = sum(1 for l in luat_tuoi if _thoa_tat_ca(l.dieu_kien, {"tuoi_xe": tuoi}))
                if n == 0:
                    thieu.append(tuoi)
            if thieu:
                self._loi(loai, f"Nhóm {nhom_tuoi}",
                          f"Không có luật khấu hao cho tuổi xe: {', '.join(map(str, thieu[:15]))}{'…' if len(thieu) > 15 else ''}.")
        self._ghi("Loại trừ lẫn nhau trong nhóm và bao phủ tuổi 0–40 (lưới điểm biên)", so_diem, loai)

    # ------------------------------------------------------------- khung
    def kiem_tra_khung(self):
        loai = "Khung"
        so = 0
        thay: dict[str, int] = {}
        nam_dg = self.config.get("nam_dinh_gia", 2026)
        hop_le = self.gia_tri_hop_le
        for h in self.frames.get("hang_xe", []):
            thay[h.get("id")] = thay.get(h.get("id"), 0) + 1
            if h.get("nhom_giu_gia") not in hop_le.get("nhom_giu_gia", []):
                self._loi(loai, f"Khung hãng {h.get('id')}", f"Nhóm giữ giá '{h.get('nhom_giu_gia')}' không hợp lệ.")
            for d in h.get("dong_xe", []):
                thay[d.get("id")] = thay.get(d.get("id"), 0) + 1
                if d.get("phan_khuc") not in self.ma_phan_khuc:
                    self._loi(loai, f"Khung dòng {d.get('id')}", f"Phân khúc '{d.get('phan_khuc')}' chưa khai báo trong danh sách phân khúc.")
                if not d.get("phien_ban"):
                    self._loi(loai, f"Khung dòng {d.get('id')}", "Dòng xe chưa có phiên bản nào.")
                for p in d.get("phien_ban", []):
                    so += 1
                    pid = p.get("id")
                    thay[pid] = thay.get(pid, 0) + 1
                    dt = f"Khung {pid}"
                    g = p.get("gia_moi")
                    if not _la_so(g) or g <= 0:
                        self._loi(loai, dt, f"Giá xe mới tham chiếu không hợp lệ: {g!r}.")
                    if not (_la_so(p.get("nam_tu")) and _la_so(p.get("nam_den"))) or p["nam_tu"] > p["nam_den"]:
                        self._loi(loai, dt, "Khoảng năm sản xuất (nam_tu, nam_den) không hợp lệ.")
                    elif p["nam_tu"] > nam_dg:
                        self._loi(loai, dt, f"Năm bắt đầu {p['nam_tu']} sau năm định giá {nam_dg}.")
                    if p.get("hop_so") not in hop_le.get("hop_so", []):
                        self._loi(loai, dt, f"Hộp số '{p.get('hop_so')}' không hợp lệ.")
                    if p.get("nhien_lieu") not in hop_le.get("nhien_lieu", []):
                        self._loi(loai, dt, f"Nhiên liệu '{p.get('nhien_lieu')}' không hợp lệ.")
        for k, n in thay.items():
            if n > 1:
                self._loi("Mã trùng", f"Khung {k}", f"Mã khung bị dùng {n} lần.")
        self._ghi("Khung: mã duy nhất, giá mới > 0, năm, hộp số, phân khúc", so, loai)

    def kiem_tra_kich_ban(self, kb: KnowledgeBase):
        loai = "Kịch bản"
        ds = self.scenarios.get("kich_ban", [])
        from .validation import kiem_tra_dau_vao
        for s in ds:
            dv = s.get("dau_vao", {})
            if dv.get("phien_ban") not in self.ma_phien_ban:
                self._loi("Tham chiếu", f"Kịch bản {s.get('id')}", f"Phiên bản '{dv.get('phien_ban')}' không có trong khung.")
                continue
            loi, _ = kiem_tra_dau_vao(dv, kb)
            for truong, msg in loi.items():
                self._loi(loai, f"Kịch bản {s.get('id')}", f"{truong}: {msg}")
        self._ghi("Kịch bản mẫu tham chiếu phiên bản tồn tại và đầu vào hợp lệ", len(ds), loai)

    def kiem_tra_kho_tinh_huong(self, df) -> None:
        loai = "Kho tình huống"
        if df is None:
            return
        sai = df[~df["phien_ban_id"].isin(self.ma_phien_ban)]
        for _, r in sai.head(10).iterrows():
            self._loi("Tham chiếu", f"Tình huống {r.get('ma_tin')}", f"Phiên bản '{r['phien_ban_id']}' không có trong khung.")
        gia_sai = df[df["gia"] <= 0]
        for _, r in gia_sai.head(10).iterrows():
            self._loi(loai, f"Tình huống {r.get('ma_tin')}", "Giá giao dịch không dương.")
        self._ghi("Kho tình huống tham chiếu phiên bản trong khung, giá > 0", len(df), loai)

    # ------------------------------------------------------------- chạy
    def chay(self, kb: KnowledgeBase | None = None, kho_tinh_huong=None) -> dict:
        self.kiem_tra_cau_truc_luat()
        self.kiem_tra_dieu_kien()
        self.kiem_tra_hanh_dong()
        self.kiem_tra_logic()
        self.kiem_tra_khung()
        if kb is None:
            try:
                kb = KnowledgeBase.tu_du_lieu(self.frames, self.rules, self.config, self.scenarios)
            except Exception as exc:  # pragma: no cover - dữ liệu hỏng nặng
                self._loi("Cấu trúc luật", "Tập luật", f"Không dựng được cơ sở tri thức: {exc}")
                kb = None
        if kb is not None:
            self.kiem_tra_loai_tru_va_bao_phu(kb)
            if self.scenarios.get("kich_ban"):
                self.kiem_tra_kich_ban(kb)
        if kho_tinh_huong is not None:
            self.kiem_tra_kho_tinh_huong(kho_tinh_huong)
        so_loi = sum(1 for v in self.van_de if v.muc == "loi")
        so_cb = sum(1 for v in self.van_de if v.muc == "canh_bao")
        return {
            "hop_le": so_loi == 0,
            "so_loi": so_loi,
            "so_canh_bao": so_cb,
            "van_de": [v.to_dict() for v in self.van_de],
            "da_kiem_tra": self.da_kiem_tra,
        }


def kiem_tra_co_so_tri_thuc(kb: KnowledgeBase, kho_tinh_huong=None, rules_raw: dict | None = None) -> dict:
    """Kiểm tra toàn bộ cơ sở tri thức. Có thể truyền rules_raw khác (ví dụ tệp minh họa chứa lỗi)."""
    rules = rules_raw if rules_raw is not None else kb.rules_raw
    kt = KiemTraTriThuc(kb.frames, rules, kb.config, kb.scenarios_raw if rules_raw is None else None)
    kb_kt = kb if rules_raw is None else None
    return kt.chay(kb_kt, kho_tinh_huong)
