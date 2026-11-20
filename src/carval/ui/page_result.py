"""Trang 2 – Kết quả và giải thích."""
from __future__ import annotations

import html

import streamlit as st

from .. import explain
from ..formatting import fmt_km, fmt_phan_tram, fmt_so
from ..service import DichVuDinhGia
from . import charts, state
from .theme import bang_html, the_kpi, the_tin_cay, tieu_de_muc, tieu_de_trang

MUC_CB = {"nghiem_trong": "error", "chu_y": "warning", "thong_tin": "info"}


def _ltx(x: float, so_le: int = 1) -> str:
    """Số kiểu Việt cho LaTeX: 1.234,5 -> 1.234{,}5"""
    return fmt_so(x, so_le).replace(",", "{,}")


def _cong_thuc_ket_hop(kq, config):
    kh = kq.ket_hop
    w_max = config["ket_hop"]["w_cbr_toi_da"]
    if kh.n == 0:
        st.latex(r"w_{CBR} = 0 \;\Rightarrow\; \alpha = 1,\quad P = P_{luật} = " + _ltx(kh.gia_de_xuat) + r"\ \text{triệu}")
        return
    st.latex(r"w_{CBR} = w_{max}\cdot\frac{n}{k}\cdot \overline{Sim} = " + _ltx(w_max, 2) + r"\cdot\frac{" + str(kh.n)
             + "}{" + str(kh.k) + r"}\cdot " + _ltx(kh.sim_tb, 3) + " = " + _ltx(kh.w_cbr, 3)
             + r",\qquad \alpha = 1 - w_{CBR} = " + _ltx(kh.alpha, 3))
    st.latex(r"P = \alpha\, P_{luật} + w_{CBR}\, P_{CBR} = " + _ltx(kh.alpha, 3) + r"\times " + _ltx(kh.gia_luat)
             + r" + " + _ltx(kh.w_cbr, 3) + r"\times " + _ltx(kh.gia_cbr) + " = "
             + _ltx(kh.gia_de_xuat) + r"\ \text{triệu}")


def _khong_co_ket_qua():
    tieu_de_trang("Kết quả và giải thích")
    st.info("Chưa có kết quả định giá. Hãy sang trang **Định giá**, chọn kịch bản mẫu hoặc nhập thông tin xe rồi bấm "
            "**Định giá**. Kết quả sẽ được giữ lại khi chuyển giữa các trang.")
    st.button("← Về trang Định giá", type="primary", on_click=state.chuyen_trang, args=("Định giá",))


def render(svc: DichVuDinhGia):
    kq = st.session_state.get("ket_qua")
    if kq is None:
        _khong_co_ket_qua()
        return
    kb = svc.kb
    kh, sd, cbr, dv = kq.ket_hop, kq.suy_dien, kq.cbr, kq.dau_vao
    tieu_de_trang("Kết quả và giải thích")

    # 1) Thông tin xe của lần định giá
    st.markdown(
        f'<div class="car-head"><div class="car-name">{html.escape(kq.phien_ban.ten_day_du)}</div>'
        f'<div class="car-meta"><span>Phiên bản <b>{html.escape(kq.phien_ban.ten)}</b></span>'
        f'<span>Đời <b>{dv["nam_sx"]}</b></span><span><b>{fmt_km(dv["so_km"])}</b></span>'
        f'<span>Khu vực <b>{dv["khu_vuc"]}</b></span><span>Tình trạng <b>{dv["tinh_trang"]}</b></span>'
        f'<span class="small-muted">Tính lúc {kq.thoi_diem} · {fmt_so(kq.thoi_gian_ms, 1)} ms</span></div></div>',
        unsafe_allow_html=True)
    if state.ket_qua_da_cu():
        c1, c2 = st.columns([0.78, 0.22], vertical_alignment="center")
        c1.warning("Thông tin trên trang Định giá đã thay đổi sau lần tính này. Giá dưới đây thuộc **lần tính trước**; "
                   "hãy quay lại bấm **Định giá** để cập nhật.")
        c2.button("Về trang Định giá", on_click=state.chuyen_trang, args=("Định giá",), use_container_width=True)

    # 2) Bốn ô số chính
    k1, k2, k3, k4 = st.columns([1.25, 1, 1, 1])
    k1.markdown(the_kpi("Giá đề xuất", fmt_so(kh.gia_de_xuat, 1), "triệu",
                        f"α = {fmt_so(kh.alpha, 3)} luật · w<sub>CBR</sub> = {fmt_so(kh.w_cbr, 3)}", chinh=True),
                unsafe_allow_html=True)
    k2.markdown(the_kpi("Giá theo luật", fmt_so(kh.gia_luat, 1), "triệu",
                        f"Từ giá mới {fmt_so(sd.gia_moi, 0)} tr · giữ {fmt_phan_tram(sd.gia_luat / sd.gia_moi)}"),
                unsafe_allow_html=True)
    if kh.gia_cbr is not None:
        k3.markdown(the_kpi("Giá CBR", fmt_so(kh.gia_cbr, 1), "triệu",
                            f"{kh.n} xe tương tự · Sim TB {fmt_so(kh.sim_tb, 3)}"), unsafe_allow_html=True)
    else:
        k3.markdown(the_kpi("Giá CBR", "Không đủ dữ liệu", "", "0 xe đạt ngưỡng → dùng giá theo luật", nho=True),
                    unsafe_allow_html=True)
    k4.markdown(the_tin_cay(kh.muc_tin_cay, "Chỉ số kinh nghiệm theo quy tắc, không phải xác suất đúng"),
                unsafe_allow_html=True)

    # 3) Thanh khoảng giá
    with st.container(border=True):
        st.markdown(f"**Khoảng giá tham khảo:** {fmt_so(kh.khoang_thap, 1)} – {fmt_so(kh.khoang_cao, 1)} triệu đồng "
                    f"(P × (1 ± δ), δ = {fmt_phan_tram(kh.delta)}) · <span class='small-muted'>khoảng kinh nghiệm, "
                    "không phải khoảng tin cậy thống kê</span>", unsafe_allow_html=True)
        st.plotly_chart(charts.khoang_gia(kq), use_container_width=True, config=charts.CAU_HINH, key="ch_khoang")

    # 4) Cảnh báo
    for c in kq.canh_bao:
        getattr(st, MUC_CB.get(c["muc"], "info"))(f"**{c['ma_luat']}** – {c['noi_dung']}")

    # 5) Ba tab
    tab_gt, tab_vet, tab_xe = st.tabs(["Giải thích", "Vết suy diễn", "Xe tương tự"])
    with tab_gt:
        c1, c2 = st.columns([0.52, 0.48], gap="large")
        with c1:
            tieu_de_muc("Vì sao có giá này?")
            for cau in explain.loi_giai_thich(kq, kb.config):
                st.markdown("- " + cau)
        with c2:
            st.plotly_chart(charts.tac_dong(kq), use_container_width=True, config=charts.CAU_HINH, key="ch_tacdong")
        tieu_de_muc("Phép tính giá đề xuất")
        with st.container(border=True):
            _cong_thuc_ket_hop(kq, kb.config)
            st.markdown(f"Khoảng tham khảo: {explain.chi_tiet_delta(kq, kb.config)} → "
                        f"[{fmt_so(kh.khoang_thap, 1)}; {fmt_so(kh.khoang_cao, 1)}] triệu đồng.")

    with tab_vet:
        st.plotly_chart(charts.waterfall(kq), use_container_width=True, config=charts.CAU_HINH, key="ch_wf")
        st.markdown(f"**Bảng vết suy diễn** – {len(sd.buoc)} luật kích hoạt theo thứ tự chu kỳ; giá tính bằng triệu đồng.")
        vet = explain.bang_vet(kq)
        lop = ["giam" if (b.thay_doi or 0) < -1e-9 else ("tang" if (b.thay_doi or 0) > 1e-9 else "") for b in sd.buoc]
        st.markdown(bang_html(vet, cot_so={"Bước", "Giá trước", "Thay đổi", "Giá sau"}, cot_ma={"Mã luật"}, lop_dong=lop),
                    unsafe_allow_html=True)
        with st.expander("Tập xung đột và luật được chọn ở từng chu kỳ (giải quyết xung đột)"):
            import pandas as pd
            st.markdown(bang_html(pd.DataFrame([{"Chu kỳ": b.chu_ky, "Tập xung đột (theo thứ tự ưu tiên)": ", ".join(b.tap_xung_dot),
                                                 "Luật được chọn": b.ma_luat, "Ưu tiên": b.uu_tien,
                                                 "Điều kiện thỏa": "; ".join(b.dieu_kien_thoa)} for b in sd.buoc]),
                                  cot_so={"Chu kỳ", "Ưu tiên"}, cot_ma={"Luật được chọn"}), unsafe_allow_html=True)
            st.caption("Chọn luật có độ ưu tiên cao nhất → nhiều điều kiện hơn → mã nhỏ hơn; mỗi luật chạy một lần.")
        tieu_de_muc("Bước kết hợp với CBR")
        with st.container(border=True):
            st.markdown("Sau khi suy diễn xong, giá theo luật được kết hợp với giá CBR theo trọng số phụ thuộc số xe "
                        "tìm được (n) và độ tương tự trung bình:")
            _cong_thuc_ket_hop(kq, kb.config)

    with tab_xe:
        cfg = kb.config["cbr"]
        pk = kq.phien_ban.phan_khuc
        st.markdown(
            f"Lọc cứng cùng phân khúc **{pk}**, đời **{dv['nam_sx'] - cfg['chenh_nam_toi_da']}–{dv['nam_sx'] + cfg['chenh_nam_toi_da']}**: "
            f"**{cbr.so_ung_vien}** ứng viên → **{cbr.so_dat_nguong}** xe có Sim ≥ θ = {fmt_so(cbr.nguong, 2)} → "
            f"chọn tối đa k = {cbr.k} xe có Sim cao nhất. Kho tình huống chỉ gồm tập train.")
        if cbr.n == 0:
            st.warning(f"Không có xe tương tự đạt ngưỡng. {cbr.ly_do} Hệ thống trả về trạng thái **thiếu dữ liệu** "
                       "và dùng giá theo luật.")
        else:
            st.markdown(bang_html(explain.bang_xe_tuong_tu(kq),
                                  cot_so={"#", "Năm", "Số km", "Giá gốc (tr)", "Giá hiệu chỉnh (tr)", "Độ tương tự"}),
                        unsafe_allow_html=True)
            st.markdown(f"Giá CBR = Σ Sim·P′ / Σ Sim = **{fmt_so(cbr.gia_cbr, 1)} triệu**; "
                        f"hệ số biến thiên của giá hiệu chỉnh CV = {fmt_so(cbr.cv, 3)}.")
            tieu_de_muc("Căn cứ so sánh và hiệu chỉnh từng xe")
            lua_chon = {f"#{i} · {x.ten_xe} · {x.nam_sx} · {fmt_km(x.so_km)} · Sim {fmt_so(x.do_tuong_tu, 3)}": x
                        for i, x in enumerate(cbr.xe, 1)}
            chon = st.selectbox("Chọn xe so sánh", list(lua_chon), key="chon_xe_tt")
            x = lua_chon[chon]
            st.markdown("**Độ tương tự theo từng tiêu chí** – Sim = Σ wᵢ·simᵢ / Σ wᵢ")
            st.markdown(bang_html(explain.bang_tuong_tu_cuc_bo(kq, x, kb),
                                  cot_so={"sim cục bộ", "Trọng số", "Đóng góp"}, dong_tong_cuoi=True),
                        unsafe_allow_html=True)
            c2, c3 = st.columns([0.6, 0.4], gap="large", vertical_alignment="center")
            with c2:
                st.markdown("**Hiệu chỉnh giá về đặc điểm xe cần định giá** (tỷ số hệ số theo nhóm luật)")
                st.markdown(bang_html(explain.bang_hieu_chinh(kq, x, svc.kho),
                                      cot_so={"Xe cần định giá", "Xe so sánh", "Tỷ số"}, dong_tong_cuoi=True),
                            unsafe_allow_html=True)
            with c3:
                st.latex(r"P'_j = P_j \times \frac{P_{luật}(Q)}{P_{luật}(C_j)}")
                st.latex(_ltx(x.gia_goc) + r"\times " + _ltx(x.ty_le_hieu_chinh, 3) + " = "
                         + _ltx(x.gia_hieu_chinh) + r"\ \text{triệu}")
