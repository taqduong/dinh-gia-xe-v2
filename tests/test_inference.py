"""Máy suy diễn tiến: vết, giải quyết xung đột, luật rủi ro, ràng buộc."""
import math

import pytest

from carval.inference import ForwardChainingEngine


@pytest.fixture(scope="module")
def eng(kb):
    return ForwardChainingEngine(kb)


def _dv(**kw):
    dv = {"phien_ban": "toyota-vios-15g-cvt", "nam_sx": 2019, "so_km": 95000, "khu_vuc": "Miền Bắc",
          "tinh_trang": "Tốt", "bao_duong_hang": False, "chay_dich_vu": False, "ngap_nuoc": False, "tai_nan_nang": False}
    dv.update(kw)
    return dv


def test_ca_chinh_vet_va_gia(eng, kich_ban):
    kq = eng.suy_dien(kich_ban["TC01"])
    assert kq.luat_kich_hoat == ["R01", "R02", "R03", "R07", "R17", "R23"]
    assert kq.du_kien["tuoi_xe"] == 7
    assert math.isclose(kq.gia_luat, 545 * 0.57 * 1.03 * 1.05, rel_tol=1e-12)


def test_vet_lien_mach_tu_gia_moi_den_gia_luat(eng, kich_ban):
    for dv in kich_ban.values():
        kq = eng.suy_dien(dv)
        gia = kq.gia_moi
        for b in kq.buoc_tac_dong_gia:
            assert math.isclose(b.gia_truoc, gia)
            gia = b.gia_sau
        assert math.isclose(gia, kq.gia_luat)
        tich = 1.0
        for v in kq.he_so_theo_nhom().values():
            tich *= v
        assert math.isclose(kq.gia_moi * tich, kq.gia_luat)


def test_giai_quyet_xung_dot_theo_uu_tien(eng, kich_ban):
    kq = eng.suy_dien(kich_ban["TC01"])
    b1 = kq.buoc[0]
    assert set(b1.tap_xung_dot) == {"R01", "R03"} and b1.ma_luat == "R01"   # R01 ưu tiên 100 > R03 98
    b4 = kq.buoc[3]
    assert "R25" in b4.tap_xung_dot and b4.ma_luat == "R07"                # R25 ưu tiên thấp nhất phải chờ
    assert "R25" not in kq.luat_kich_hoat                                   # điều kiện trần không còn thỏa


def test_ngap_nuoc(eng):
    kq = eng.suy_dien(_dv(ngap_nuoc=True))
    assert "R20" in kq.luat_kich_hoat and "R22" not in kq.luat_kich_hoat
    assert math.isclose(kq.he_so_theo_nhom()["RUI_RO"], 0.70)
    assert any(c["ma_luat"] == "R20" and c["muc"] == "nghiem_trong" for c in kq.canh_bao)


def test_tai_nan_nang(eng):
    kq = eng.suy_dien(_dv(tai_nan_nang=True))
    assert math.isclose(kq.he_so_theo_nhom()["RUI_RO"], 0.75)
    assert [c["ma_luat"] for c in kq.canh_bao] == ["R21"]


def test_rui_ro_kep_khong_nhan_don(eng):
    kq = eng.suy_dien(_dv(ngap_nuoc=True, tai_nan_nang=True))
    thu_tu = [m for m in kq.luat_kich_hoat if m in ("R20", "R21", "R22")]
    assert thu_tu == ["R22", "R20", "R21"]
    assert math.isclose(kq.he_so_theo_nhom()["RUI_RO"], 0.62)     # không phải 0,70 × 0,75 × 0,62
    buoc = {b.ma_luat: b for b in kq.buoc}
    assert buoc["R20"].he_so == 1.0 and "nhóm loại trừ" in buoc["R20"].ghi_chu
    assert buoc["R21"].he_so == 1.0
    assert {c["ma_luat"] for c in kq.canh_bao} == {"R20", "R21", "R22"}
    assert kq.co_canh_bao_nghiem_trong


def test_nghi_chinh_odo_chan_luat_di_it(eng, kich_ban):
    kq = eng.suy_dien(kich_ban["TC07"])
    assert "R13" in kq.luat_kich_hoat and "R10" not in kq.luat_kich_hoat
    assert kq.du_kien["nghi_tua_odo"] is True
    kq2 = eng.suy_dien(_dv(nam_sx=2024, so_km=5000))   # xe 2 năm đi ít: được cộng R10
    assert "R10" in kq2.luat_kich_hoat and "R13" not in kq2.luat_kich_hoat


def test_tran_gia_95_phan_tram(eng):
    dv = _dv(nam_sx=2026, so_km=500, tinh_trang="Rất tốt", bao_duong_hang=True)
    kq = eng.suy_dien(dv)
    assert "R25" in kq.luat_kich_hoat
    assert math.isclose(kq.gia_luat, 0.95 * 545)


def test_dich_vu_va_so_san(eng, kich_ban):
    kq = eng.suy_dien(kich_ban["TC04"])
    for ma in ("R12", "R15", "R18", "R19"):
        assert ma in kq.luat_kich_hoat
    assert any(c["ma_luat"] == "R19" for c in kq.canh_bao)


def test_moi_luat_chi_chay_mot_lan(eng, kich_ban):
    for dv in kich_ban.values():
        ids = eng.suy_dien(dv).luat_kich_hoat
        assert len(ids) == len(set(ids))
