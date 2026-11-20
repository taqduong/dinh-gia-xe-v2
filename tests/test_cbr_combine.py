"""CBR (truy hồi, ngưỡng, hiệu chỉnh, thiếu ca) và kết hợp (công thức, khoảng giá, mức tin cậy)."""
import math

import numpy as np
import pytest

from carval.cbr import dau_vao_tu_dong


def test_toi_da_k_xe_sap_giam_va_dat_nguong(svc, kich_ban):
    cfg = svc.kb.config["cbr"]
    for ma, dv in kich_ban.items():
        kq = svc.dinh_gia(dv)
        sims = [x.do_tuong_tu for x in kq.cbr.xe]
        assert len(sims) <= cfg["k_toi_da"]
        assert sims == sorted(sims, reverse=True)
        assert all(s >= cfg["nguong_tuong_tu"] - 1e-12 for s in sims)
        for x in kq.cbr.xe:
            assert x.nam_sx - dv["nam_sx"] in range(-cfg["chenh_nam_toi_da"], cfg["chenh_nam_toi_da"] + 1)
            assert svc.kb.phien_ban[x.phien_ban_id].phan_khuc == kq.phien_ban.phan_khuc


def test_do_tuong_tu_cua_chinh_no_bang_1(svc):
    r = svc.kho.df.iloc[0]
    dv = dau_vao_tu_dong(r)
    kq = svc.kho.truy_hoi(dv, svc.engine.suy_dien(dv).gia_luat)
    assert math.isclose(kq.xe[0].do_tuong_tu, 1.0)


def test_hieu_chinh_theo_ty_so_gia_luat(svc, kich_ban):
    kq = svc.dinh_gia(kich_ban["TC03"])
    for x in kq.cbr.xe:
        assert math.isclose(x.gia_hieu_chinh, x.gia_goc * kq.suy_dien.gia_luat / x.gia_luat_ca)
        tich = np.prod([d["ty_so"] for d in svc.kho.can_cu_hieu_chinh(kq.suy_dien, x)])
        assert math.isclose(tich, x.ty_le_hieu_chinh, rel_tol=1e-9)
    s = np.array([x.do_tuong_tu for x in kq.cbr.xe])
    p = np.array([x.gia_hieu_chinh for x in kq.cbr.xe])
    assert math.isclose(kq.cbr.gia_cbr, float((s * p).sum() / s.sum()))


def test_thieu_tinh_huong_dung_gia_luat(svc, kich_ban):
    kq = svc.dinh_gia(kich_ban["TC05"])
    assert kq.cbr.trang_thai == "thieu_du_lieu" and kq.cbr.n == 0 and kq.cbr.gia_cbr is None
    kh = kq.ket_hop
    assert kh.w_cbr == 0 and kh.alpha == 1
    assert math.isclose(kh.gia_de_xuat, kh.gia_luat)
    assert kh.dung_gia_luat_vi_thieu_cbr and kh.muc_tin_cay == "Thấp"
    assert math.isclose(kh.delta, svc.kb.config["khoang_gia"]["delta_khong_cbr"])
    assert any(c["ma_luat"] == "CBR" for c in kq.canh_bao)


def test_nguong_rat_cao_tra_ve_thieu_du_lieu(svc, kich_ban):
    dv = kich_ban["TC06"]
    kq = svc.kho.truy_hoi(dv, svc.engine.suy_dien(dv).gia_luat, nguong=0.999)
    assert kq.trang_thai == "thieu_du_lieu" and "ngưỡng" in kq.ly_do


def test_cong_thuc_ket_hop(svc, kich_ban):
    w_max = svc.kb.config["ket_hop"]["w_cbr_toi_da"]
    for ma, dv in kich_ban.items():
        kh = svc.dinh_gia(dv).ket_hop
        if kh.n == 0:
            continue
        assert math.isclose(kh.w_cbr, w_max * kh.n / kh.k * kh.sim_tb)
        assert math.isclose(kh.gia_de_xuat, (1 - kh.w_cbr) * kh.gia_luat + kh.w_cbr * kh.gia_cbr)
        assert min(kh.gia_luat, kh.gia_cbr) - 1e-9 <= kh.gia_de_xuat <= max(kh.gia_luat, kh.gia_cbr) + 1e-9


def test_khoang_gia_chua_gia_de_xuat(svc, test_df):
    ckg = svc.kb.config["khoang_gia"]
    for _, r in test_df.sample(150, random_state=1).iterrows():
        kh = svc.dinh_gia(dau_vao_tu_dong(r)).ket_hop
        assert kh.khoang_thap <= kh.gia_de_xuat <= kh.khoang_cao
        assert ckg["delta_min"] - 1e-12 <= kh.delta <= ckg["delta_max"] + 1e-12
        assert math.isclose(kh.khoang_thap, kh.gia_de_xuat * (1 - kh.delta))
        assert math.isclose(kh.khoang_cao, kh.gia_de_xuat * (1 + kh.delta))


def test_muc_tin_cay_theo_quy_tac(svc, kich_ban):
    assert svc.dinh_gia(kich_ban["TC03"]).ket_hop.muc_tin_cay == "Thấp"   # ngập nước
    assert svc.dinh_gia(kich_ban["TC06"]).ket_hop.muc_tin_cay == "Thấp"   # rủi ro kép
    assert svc.dinh_gia(kich_ban["TC07"]).ket_hop.muc_tin_cay != "Cao"    # nghi chỉnh đồng hồ
    kh = svc.dinh_gia(kich_ban["TC03"]).ket_hop
    assert math.isclose(kh.cong_rui_ro, svc.kb.config["khoang_gia"]["cong_them_rui_ro"])


def test_tap_test_khong_nam_trong_kho_tinh_huong(svc, test_df):
    assert not set(test_df["ma_tin"]) & set(svc.kho.df["ma_tin"])
