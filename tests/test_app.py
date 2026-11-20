"""Kiểm thử giao diện bằng Streamlit AppTest (chạy app thật, không cần trình duyệt)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "src" / "app.py")


@pytest.fixture()
def at():
    a = AppTest.from_file(APP, default_timeout=60)
    a.run()
    assert not a.exception, a.exception
    return a


def _texts(a):
    return " ".join(m.value for m in a.markdown) + " " + " ".join(getattr(e, "value", "") for e in a.error) \
        + " " + " ".join(getattr(e, "value", "") for e in a.warning) + " " + " ".join(getattr(e, "value", "") for e in a.info)


def test_trang_dinh_gia_mac_dinh(at):
    assert at.sidebar.radio(key="trang").value == "Định giá"
    assert at.selectbox(key="f_hang").value == "Toyota"
    assert at.selectbox(key="f_pb").value == "toyota-vios-15g-cvt"
    assert at.number_input(key="f_nam").value == 2019 and at.number_input(key="f_km").value == 95000
    assert "Dữ liệu mô phỏng" in _texts(at)


def test_chon_hang_cap_nhat_dong_xe(at):
    at.selectbox(key="f_hang").set_value("Honda").run()
    assert at.selectbox(key="f_dong").options == ["City", "Civic", "CR-V"]
    assert at.selectbox(key="f_dong").value == "City"
    assert at.selectbox(key="f_pb").value == "honda-city-15g"
    at.selectbox(key="f_dong").set_value("CR-V").run()
    assert at.selectbox(key="f_pb").value == "honda-crv-15e"


def test_luong_dinh_gia_den_ket_qua(at):
    at.button(key="btn_dinh_gia").click().run()
    assert not at.exception
    kq = at.session_state["ket_qua"]
    assert kq is not None and kq.hop_le
    at.button(key="btn_xem_kq").click().run()
    assert at.session_state["trang"] == "Kết quả và giải thích"
    assert not at.exception
    assert len(at.tabs) >= 3 and [t.label for t in at.tabs[:3]] == ["Giải thích", "Vết suy diễn", "Xe tương tự"]
    assert "Giá đề xuất" in _texts(at)


def test_loi_nhap_hien_gan_truong_va_khong_dinh_gia(at):
    at.number_input(key="f_nam").set_value(2030).run()
    assert "không được lớn hơn năm định giá" in _texts(at)
    at.button(key="btn_dinh_gia").click().run()
    assert at.session_state["ket_qua"] is None
    assert "Chưa thể định giá" in _texts(at)


def test_nhac_tinh_lai_khi_dau_vao_doi(at):
    at.button(key="btn_dinh_gia").click().run()
    at.number_input(key="f_km").set_value(120000).run()
    assert "lần tính trước" in _texts(at)


def test_kich_ban_ngap_nuoc_co_canh_bao(at):
    nhan = [o for o in at.selectbox(key="f_kich_ban").options if o.startswith("TC03")][0]
    at.selectbox(key="f_kich_ban").set_value(nhan).run()
    assert at.radio(key="f_ngap").value == "Có"
    at.button(key="btn_dinh_gia").click().run()
    at.sidebar.radio(key="trang").set_value("Kết quả và giải thích").run()
    assert not at.exception
    assert any("R20" in e.value for e in at.error)


def test_trang_ket_qua_khi_chua_co_ket_qua(at):
    at.sidebar.radio(key="trang").set_value("Kết quả và giải thích").run()
    assert "Chưa có kết quả định giá" in _texts(at)


def test_trang_phan_tich_va_quan_tri(at):
    at.sidebar.radio(key="trang").set_value("Phân tích dữ liệu").run()
    assert not at.exception and "Dữ liệu mô phỏng" in _texts(at)
    at.multiselect(key="pt_hang").set_value(["Kia"]).run()
    at.multiselect(key="pt_pk").set_value(["SUV-D"]).run()
    assert "Không tìm thấy mẫu" in _texts(at)
    at.sidebar.radio(key="trang").set_value("Quản trị tri thức").run()
    assert not at.exception
    assert "Đạt" in _texts(at)
