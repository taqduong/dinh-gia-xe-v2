"""Trang 1 – Định giá: chọn kịch bản mẫu, nhập thông tin xe, bấm Định giá."""
from __future__ import annotations

import streamlit as st

from ..formatting import fmt_so, fmt_trieu
from ..service import DichVuDinhGia
from ..validation import kiem_tra_dau_vao
from . import state
from .theme import ghi_chu_mo_phong, loi_truong, the_kpi, the_tin_cay, tieu_de_muc, tieu_de_trang


def _cb_doi_kich_ban(svc: DichVuDinhGia):
    nhan = st.session_state.f_kich_ban
    for s in svc.kb.kich_ban:
        if state.nhan_kich_ban(s) == nhan:
            state.ghi_dau_vao_vao_form(s["dau_vao"], svc.kb)
            return


def _cb_doi_hang(svc: DichVuDinhGia):
    dongs = svc.kb.danh_sach_dong(st.session_state.f_hang)
    st.session_state.f_dong = dongs[0]
    st.session_state.f_pb = svc.kb.danh_sach_phien_ban(st.session_state.f_hang, dongs[0])[0].id


def _cb_doi_dong(svc: DichVuDinhGia):
    st.session_state.f_pb = svc.kb.danh_sach_phien_ban(st.session_state.f_hang, st.session_state.f_dong)[0].id


def _cb_dinh_gia(svc: DichVuDinhGia):
    dv = state.dau_vao_hien_tai()
    kq = svc.dinh_gia(dv)
    if kq.hop_le:
        st.session_state.ket_qua = kq
        st.session_state.dau_vao_kq = dv
        st.session_state.loi_khi_bam = None
    else:
        st.session_state.loi_khi_bam = kq.loi


def _dam_bao_lua_chon_hop_le(svc: DichVuDinhGia):
    kb = svc.kb
    ss = st.session_state
    if ss.get("f_hang") not in kb.danh_sach_hang():
        ss.f_hang = kb.danh_sach_hang()[0]
    dongs = kb.danh_sach_dong(ss.f_hang)
    if ss.get("f_dong") not in dongs:
        ss.f_dong = dongs[0]
    pbs = [p.id for p in kb.danh_sach_phien_ban(ss.f_hang, ss.f_dong)]
    if ss.get("f_pb") not in pbs:
        ss.f_pb = pbs[0]


def render(svc: DichVuDinhGia):
    kb = svc.kb
    tieu_de_trang("Định giá xe ô tô cũ",
                  "Nhập thông tin xe → máy suy diễn áp dụng tập luật → CBR so sánh với các xe tương tự → giá đề xuất kèm giải thích.")
    ghi_chu_mo_phong(
        f"<b>Dữ liệu mô phỏng.</b> Kho {fmt_so(len(svc.kho))} xe so sánh được sinh bằng chương trình (seed cố định), "
        "không phải tin rao thu thập từ thị trường. Giá xe mới tham chiếu và hệ số trong luật là <b>giả định</b> của nhóm. "
        f"Năm định giá cố định: <b>{kb.nam_dinh_gia}</b>.")

    _dam_bao_lua_chon_hop_le(svc)
    nhan_kb = [state.KHONG_CHON] + [state.nhan_kich_ban(s) for s in kb.kich_ban]
    c_kb, c_mota = st.columns([0.42, 0.58], vertical_alignment="bottom")
    with c_kb:
        st.selectbox("Kịch bản mẫu (tự điền biểu mẫu, vẫn sửa được)", nhan_kb, key="f_kich_ban",
                     on_change=_cb_doi_kich_ban, args=(svc,))
    with c_mota:
        s_chon = next((s for s in kb.kich_ban if state.nhan_kich_ban(s) == st.session_state.f_kich_ban), None)
        if s_chon:
            da_sua = s_chon["dau_vao"] != state.dau_vao_hien_tai()
            st.markdown(f'<div class="info-chip">{s_chon["mo_ta"]}'
                        + (' <b>· Đã chỉnh sửa so với kịch bản.</b>' if da_sua else "") + "</div>",
                        unsafe_allow_html=True)

    dv = state.dau_vao_hien_tai()
    loi, canh_bao = kiem_tra_dau_vao(dv, kb)

    with st.container(border=True):
        c1, c2, c3 = st.columns(3, gap="large")
        with c1:
            tieu_de_muc("Thông tin xe", "1")
            st.selectbox("Hãng xe", kb.danh_sach_hang(), key="f_hang", on_change=_cb_doi_hang, args=(svc,))
            st.selectbox("Dòng xe", kb.danh_sach_dong(st.session_state.f_hang), key="f_dong",
                         on_change=_cb_doi_dong, args=(svc,))
            pbs = kb.danh_sach_phien_ban(st.session_state.f_hang, st.session_state.f_dong)
            st.selectbox("Phiên bản", [p.id for p in pbs], key="f_pb",
                         format_func=lambda i: kb.phien_ban[i].ten)
            loi_truong(loi.get("phien_ban"))
            pb = kb.phien_ban.get(st.session_state.f_pb)
            if pb:
                st.markdown(
                    f'<div class="info-chip">Phân khúc: <b>{pb.phan_khuc}</b> – {kb.ten_phan_khuc(pb.phan_khuc)}<br>'
                    f'Giá mới tham chiếu: <b>{fmt_trieu(pb.gia_moi, 0)}</b> <span class="small-muted">· giả định</span><br>'
                    f'{pb.dong_co} · {pb.hop_so} · {pb.so_cho} chỗ · đời {pb.nam_tu}–{pb.nam_den}</div>',
                    unsafe_allow_html=True)
        with c2:
            tieu_de_muc("Mức sử dụng", "2")
            st.number_input("Năm sản xuất", step=1, format="%d", key="f_nam",
                            help=f"Từ {kb.config['gia_tri_hop_le']['nam_sx_toi_thieu']} đến {kb.nam_dinh_gia}, trong đời của phiên bản.")
            loi_truong(loi.get("nam_sx"))
            st.number_input("Số km đã đi", step=1000, format="%d", key="f_km",
                            help="Số km trên đồng hồ, từ 0 đến 1.000.000 km.")
            loi_truong(loi.get("so_km"), canh_bao.get("so_km"))
            st.selectbox("Khu vực", kb.config["gia_tri_hop_le"]["khu_vuc"], key="f_kv")
            loi_truong(loi.get("khu_vuc"))
            if "nam_sx" not in loi and "so_km" not in loi and st.session_state.f_nam is not None:
                tuoi = kb.nam_dinh_gia - int(st.session_state.f_nam)
                st.markdown(f'<div class="info-chip">Tuổi xe: <b>{tuoi} năm</b> · trung bình '
                            f'<b>{fmt_so(st.session_state.f_km / max(1, tuoi))} km/năm</b></div>',
                            unsafe_allow_html=True)
        with c3:
            tieu_de_muc("Tình trạng và lịch sử", "3")
            st.selectbox("Tình trạng xe", kb.config["gia_tri_hop_le"]["tinh_trang"], key="f_tt")
            loi_truong(loi.get("tinh_trang"))
            cc1, cc2 = st.columns(2)
            with cc1:
                st.radio("Bảo dưỡng tại hãng", ["Có", "Không"], key="f_bd", horizontal=True)
                st.radio("Từng ngập nước", ["Có", "Không"], key="f_ngap", horizontal=True)
            with cc2:
                st.radio("Từng chạy dịch vụ", ["Có", "Không"], key="f_dv", horizontal=True)
                st.radio("Tai nạn nặng", ["Có", "Không"], key="f_tn", horizontal=True)

    st.button("Định giá", type="primary", use_container_width=True, key="btn_dinh_gia",
              on_click=_cb_dinh_gia, args=(svc,))

    loi_bam = st.session_state.get("loi_khi_bam")
    if loi_bam and loi:
        st.error("Chưa thể định giá: hãy sửa các trường được đánh dấu ⚠ ở trên ("
                 + ", ".join({"nam_sx": "Năm sản xuất", "so_km": "Số km", "phien_ban": "Phiên bản"}.get(k, k) for k in loi)
                 + ").")

    kq = st.session_state.get("ket_qua")
    if kq is None:
        st.info("Chọn một kịch bản mẫu hoặc tự nhập thông tin xe, sau đó bấm **Định giá**.")
        return
    if state.ket_qua_da_cu():
        st.warning(f"Thông tin xe đã thay đổi sau lần tính gần nhất. Giá dưới đây thuộc **lần tính trước** "
                   f"({kq.phien_ban.ten_day_du}, đời {kq.dau_vao['nam_sx']}, {fmt_so(kq.dau_vao['so_km'])} km, "
                   f"lúc {kq.thoi_diem}). Bấm **Định giá** để tính lại.")
    kh = kq.ket_hop
    st.markdown(f"**Kết quả lần tính gần nhất** · {kq.phien_ban.ten_day_du} · đời {kq.dau_vao['nam_sx']} · "
                f"{fmt_so(kq.dau_vao['so_km'])} km · {kq.dau_vao['khu_vuc']}")
    k1, k2, k3, k4 = st.columns([1.25, 1, 1, 1])
    k1.markdown(the_kpi("Giá đề xuất", fmt_so(kh.gia_de_xuat, 1), "triệu",
                        f"Khoảng {fmt_so(kh.khoang_thap, 1)} – {fmt_so(kh.khoang_cao, 1)} triệu", chinh=True),
                unsafe_allow_html=True)
    k2.markdown(the_kpi("Giá theo luật", fmt_so(kh.gia_luat, 1), "triệu",
                        f"{len(kq.suy_dien.buoc)} luật kích hoạt"), unsafe_allow_html=True)
    k3.markdown(the_kpi("Giá CBR", fmt_so(kh.gia_cbr, 1) if kh.gia_cbr is not None else "Không đủ dữ liệu",
                        "triệu" if kh.gia_cbr is not None else "", f"{kh.n} xe tương tự", nho=kh.gia_cbr is None),
                unsafe_allow_html=True)
    k4.markdown(the_tin_cay(kh.muc_tin_cay, "Phân loại theo quy tắc, không phải xác suất"), unsafe_allow_html=True)
    st.write("")
    st.button("Xem kết quả và giải thích →", key="btn_xem_kq", on_click=state.chuyen_trang,
              args=("Kết quả và giải thích",), use_container_width=False)
