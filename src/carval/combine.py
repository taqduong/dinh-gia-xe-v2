"""Kết hợp giá theo luật và giá CBR; tính khoảng giá tham khảo và mức tin cậy.

Công thức (dùng thống nhất ở mã nguồn, giao diện và báo cáo):

  w_CBR = w_max × (n / k) × Sim_TB      (n = số xe đạt ngưỡng, k = k_toi_da)
  α     = 1 − w_CBR
  P     = α · P_luật + w_CBR · P_CBR    (n = 0  →  w_CBR = 0, P = P_luật)

  d     = |P_luật − P_CBR| / P
  δ     = min(δ_max, max(δ_min, CV, d) + r)    khi n ≥ 1
  δ     = min(δ_max, δ_không_CBR + r)          khi n = 0
  r     = cộng thêm khi có cảnh báo mức nghiêm trọng
  Khoảng tham khảo = [P·(1 − δ); P·(1 + δ)]

Mức tin cậy là phân loại theo quy tắc kinh nghiệm, KHÔNG phải xác suất đúng.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .cbr import KetQuaCBR
from .formatting import fmt_so


@dataclass
class KetQuaKetHop:
    gia_de_xuat: float
    gia_luat: float
    gia_cbr: float | None
    w_cbr: float
    alpha: float
    n: int
    k: int
    sim_tb: float | None
    cv: float | None
    d: float | None
    cong_rui_ro: float
    delta: float
    khoang_thap: float
    khoang_cao: float
    muc_tin_cay: str
    ly_do_tin_cay: list[str] = field(default_factory=list)
    dung_gia_luat_vi_thieu_cbr: bool = False

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def ket_hop(gia_luat: float, cbr: KetQuaCBR, co_nghiem_trong: bool, co_chu_y: bool, config: dict) -> KetQuaKetHop:
    ck = config["ket_hop"]
    ckg = config["khoang_gia"]
    ctc = config["muc_tin_cay"]
    k = cbr.k
    n = cbr.n
    r = ckg["cong_them_rui_ro"] if co_nghiem_trong else 0.0

    if n == 0 or cbr.gia_cbr is None:
        w = 0.0
        p = gia_luat
        d = None
        delta = min(ckg["delta_max"], ckg["delta_khong_cbr"] + r)
    else:
        w = ck["w_cbr_toi_da"] * (min(n, k) / k) * cbr.sim_tb
        p = (1 - w) * gia_luat + w * cbr.gia_cbr
        d = abs(gia_luat - cbr.gia_cbr) / p
        delta = min(ckg["delta_max"], max(ckg["delta_min"], cbr.cv or 0.0, d) + r)

    # Mức tin cậy theo quy tắc
    ly_do: list[str] = []
    if co_nghiem_trong:
        ly_do.append("Có cảnh báo rủi ro nghiêm trọng (ngập nước/tai nạn nặng).")
    if n == 0:
        ly_do.append("Không có xe tương tự đạt ngưỡng; giá chỉ dựa trên luật.")
    if d is not None and d > ctc["thap_chenh_lech_tren"]:
        ly_do.append(f"Giá luật và giá CBR chênh {fmt_so(d * 100, 1)}% (> {fmt_so(ctc['thap_chenh_lech_tren'] * 100, 0)}%).")
    if ly_do:
        muc = "Thấp"
    elif (n >= ctc["cao_so_xe_toi_thieu"] and cbr.sim_tb is not None and cbr.sim_tb >= ctc["cao_sim_tb_toi_thieu"]
          and d is not None and d <= ctc["cao_chenh_lech_toi_da"] and not co_chu_y):
        muc = "Cao"
        ly_do.append(f"{n} xe tương tự, Sim TB {fmt_so(cbr.sim_tb, 3)} ≥ {fmt_so(ctc['cao_sim_tb_toi_thieu'], 2)}, "
                     f"luật và CBR chênh {fmt_so(d * 100, 1)}% ≤ {fmt_so(ctc['cao_chenh_lech_toi_da'] * 100, 0)}%, không cảnh báo.")
    else:
        muc = "Trung bình"
        if n < ctc["cao_so_xe_toi_thieu"]:
            ly_do.append(f"Chỉ có {n} xe tương tự (mức Cao cần ≥ {ctc['cao_so_xe_toi_thieu']}).")
        if cbr.sim_tb is not None and cbr.sim_tb < ctc["cao_sim_tb_toi_thieu"]:
            ly_do.append(f"Sim TB {fmt_so(cbr.sim_tb, 3)} < {fmt_so(ctc['cao_sim_tb_toi_thieu'], 2)}.")
        if d is not None and d > ctc["cao_chenh_lech_toi_da"]:
            ly_do.append(f"Luật và CBR chênh {fmt_so(d * 100, 1)}% (> {fmt_so(ctc['cao_chenh_lech_toi_da'] * 100, 0)}%).")
        if co_chu_y:
            ly_do.append("Có cảnh báo mức chú ý cần kiểm tra thêm.")

    return KetQuaKetHop(
        gia_de_xuat=p, gia_luat=gia_luat, gia_cbr=cbr.gia_cbr, w_cbr=w, alpha=1 - w, n=n, k=k,
        sim_tb=cbr.sim_tb, cv=cbr.cv, d=d, cong_rui_ro=r, delta=delta,
        khoang_thap=max(0.0, p * (1 - delta)), khoang_cao=p * (1 + delta),
        muc_tin_cay=muc, ly_do_tin_cay=ly_do, dung_gia_luat_vi_thieu_cbr=(n == 0),
    )
