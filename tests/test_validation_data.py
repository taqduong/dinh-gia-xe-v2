"""Kiểm tra dữ liệu nhập và quy trình dữ liệu."""
import json

import pandas as pd

from carval.datagen import doc_cau_hinh, sinh_du_lieu_sach
from carval.paths import CLEAN_CSV, PROCESSED_DIR, TEST_CSV, TRAIN_CSV
from carval.validation import kiem_tra_dau_vao


def test_dau_vao_hop_le(kb, kich_ban):
    for dv in kich_ban.values():
        loi, _ = kiem_tra_dau_vao(dv, kb)
        assert loi == {}


def test_nam_san_xuat_khong_hop_le(kb, kich_ban):
    dv = dict(kich_ban["TC01"])
    for nam, tu_khoa in ((2030, "năm định giá 2026"), (1985, "từ 1990"), (2010, "chỉ có đời 2014–2026"),
                         (2019.5, "số nguyên"), (None, "Vui lòng nhập")):
        dv["nam_sx"] = nam
        loi, _ = kiem_tra_dau_vao(dv, kb)
        assert "nam_sx" in loi and tu_khoa in loi["nam_sx"], (nam, loi)


def test_so_km_khong_hop_le(kb, kich_ban):
    dv = dict(kich_ban["TC01"])
    dv["so_km"] = -1
    assert "không được âm" in kiem_tra_dau_vao(dv, kb)[0]["so_km"]
    dv["so_km"] = 2_000_000
    assert "vượt giới hạn" in kiem_tra_dau_vao(dv, kb)[0]["so_km"]
    dv["so_km"] = 700_000          # hợp lệ nhưng bất thường → cảnh báo, không chặn
    loi, cb = kiem_tra_dau_vao(dv, kb)
    assert "so_km" not in loi and "cao bất thường" in cb["so_km"]


def test_dich_vu_tu_choi_dau_vao_loi(svc, kich_ban):
    dv = dict(kich_ban["TC01"], nam_sx=2030)
    kq = svc.dinh_gia(dv)
    assert not kq.hop_le and kq.ket_hop is None and "nam_sx" in kq.loi


def test_chia_train_test_doc_lap():
    train, test = pd.read_csv(TRAIN_CSV), pd.read_csv(TEST_CSV)
    sach = pd.read_csv(CLEAN_CSV)
    assert not set(train["ma_tin"]) & set(test["ma_tin"])
    assert len(train) + len(test) == len(sach)
    log = json.loads((PROCESSED_DIR / "cleaning_log.json").read_text(encoding="utf-8"))
    assert log["chia_tap"]["so_train"] == len(train) and log["chia_tap"]["so_test"] == len(test)
    buoc = log["cac_buoc"]
    for a, b in zip(buoc, buoc[1:]):
        assert b["truoc"] == a["sau"]          # số liệu từng bước liên tục


def test_du_lieu_sach_tham_chieu_khung(kb):
    sach = pd.read_csv(CLEAN_CSV)
    assert sach["phien_ban_id"].isin(list(kb.phien_ban)).all()
    assert (sach["gia"] > 0).all() and (sach["so_km"] >= 0).all()
    assert sach["nam_sx"].between(1990, kb.nam_dinh_gia).all()
    assert (sach["nguon_du_lieu"].str.startswith("Mô phỏng")).all()


def test_bo_sinh_tai_lap_voi_seed(kb):
    cfg = doc_cau_hinh()
    cfg["so_ban_ghi_goc"] = 60
    a, b = sinh_du_lieu_sach(kb, cfg), sinh_du_lieu_sach(kb, cfg)
    pd.testing.assert_frame_equal(a, b)
