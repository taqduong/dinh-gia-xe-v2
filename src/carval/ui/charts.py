"""Biểu đồ Plotly cho giao diện (nhãn tiếng Việt, đơn vị triệu đồng, dấu phẩy thập phân)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ..formatting import fmt_so
from ..service import KetQuaDinhGia
from .theme import AQUA, CAM, DO, NAVY, NAVY_DAM, XANH

FONT = "Source Sans Pro, Segoe UI, Arial, sans-serif"
CAU_HINH = {"displayModeBar": False, "responsive": True}


def _bo_cuc(fig: go.Figure, cao: int, tieu_de: str | None = None, le_trai: int = 60, le_duoi: int = 50) -> go.Figure:
    fig.update_layout(
        height=cao, template="plotly_white", separators=",.",
        font=dict(family=FONT, size=14, color="#1B2433"),
        margin=dict(l=le_trai, r=24, t=48 if tieu_de else 16, b=le_duoi),
        title=dict(text=tieu_de, font=dict(size=16, color=NAVY_DAM), x=0, xanchor="left") if tieu_de else None,
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        hoverlabel=dict(font=dict(family=FONT, size=13), bgcolor="#FFFFFF", bordercolor="#C9D3E3"),
    )
    fig.update_xaxes(gridcolor="#EEF1F6", zerolinecolor="#D5DCE8", linecolor="#C9D3E3")
    fig.update_yaxes(gridcolor="#EEF1F6", zerolinecolor="#D5DCE8", linecolor="#C9D3E3")
    return fig


def ngat_dong(chu: str, rong: int = 16) -> str:
    """Ngắt nhãn dài thành nhiều dòng (<br>) để không phải xoay nhãn trục."""
    dong, hien_tai = [], ""
    for tu in chu.split():
        if hien_tai and len(hien_tai) + 1 + len(tu) > rong:
            dong.append(hien_tai)
            hien_tai = tu
        else:
            hien_tai = (hien_tai + " " + tu).strip()
    if hien_tai:
        dong.append(hien_tai)
    return "<br>".join(dong)


def khoang_gia(kq: KetQuaDinhGia) -> go.Figure:
    kh = kq.ket_hop
    lo, hi, p = kh.khoang_thap, kh.khoang_cao, kh.gia_de_xuat
    diem = [p, kh.gia_luat] + ([kh.gia_cbr] if kh.gia_cbr is not None else [])
    xmin, xmax = min([lo] + diem), max([hi] + diem)
    pad = (xmax - xmin) * 0.12 or p * 0.05
    fig = go.Figure()
    fig.add_shape(type="rect", x0=lo, x1=hi, y0=-0.32, y1=0.32, fillcolor="#DCE6F5", line=dict(color="#9DB4D9", width=1), layer="below")
    fig.add_trace(go.Scatter(x=[p], y=[0], mode="markers", name="Giá đề xuất",
                             marker=dict(symbol="diamond", size=22, color=CAM, line=dict(color="#fff", width=2)),
                             hovertemplate="Giá đề xuất: %{x:,.1f} triệu<extra></extra>"))
    fig.add_trace(go.Scatter(x=[kh.gia_luat], y=[0], mode="markers", name="Giá theo luật",
                             marker=dict(symbol="circle", size=13, color=XANH, line=dict(color="#fff", width=2)),
                             hovertemplate="Giá theo luật: %{x:,.1f} triệu<extra></extra>"))
    if kh.gia_cbr is not None:
        fig.add_trace(go.Scatter(x=[kh.gia_cbr], y=[0], mode="markers", name="Giá CBR",
                                 marker=dict(symbol="square", size=12, color=AQUA, line=dict(color="#fff", width=2)),
                                 hovertemplate="Giá CBR: %{x:,.1f} triệu<extra></extra>"))
    for x, nhan, anchor in ((lo, f"Thấp: {fmt_so(lo, 1)}", "left"), (hi, f"Cao: {fmt_so(hi, 1)}", "right")):
        fig.add_annotation(x=x, y=0.36, text=nhan, showarrow=False, yanchor="bottom", xanchor=anchor,
                           font=dict(size=14, color=NAVY_DAM))
    fig.add_annotation(x=p, y=-0.40, text=f"<b>Đề xuất: {fmt_so(p, 1)}</b>", showarrow=False, yanchor="top",
                       font=dict(size=15, color="#B4461C"))
    fig.update_yaxes(visible=False, range=[-0.95, 0.85])
    fig.update_xaxes(range=[xmin - pad, xmax + pad], title=dict(text="Giá (triệu đồng)", font=dict(size=13)),
                     tickformat=",.0f")
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right"), showlegend=True)
    return _bo_cuc(fig, 215, le_trai=24, le_duoi=48)


def waterfall(kq: KetQuaDinhGia) -> go.Figure:
    sd = kq.suy_dien
    nhan = ["Giá xe mới"]
    y = [sd.gia_moi]
    do = ["absolute"]
    van_ban = [fmt_so(sd.gia_moi, 1)]
    hover = [f"Giá xe mới tham chiếu: {fmt_so(sd.gia_moi, 1)} triệu"]
    for b in sd.buoc_tac_dong_gia:
        if b.nhom == "KHOI_TAO":
            continue
        nhan.append(f"<b>{b.ma_luat}</b><br>{ngat_dong(b.ten, 15 if len(sd.buoc_tac_dong_gia) > 6 else 20)}")
        y.append(b.thay_doi)
        do.append("relative")
        van_ban.append(("+" if b.thay_doi > 0 else "−") + fmt_so(abs(b.thay_doi), 1))
        hover.append(f"{b.ma_luat} – {b.ten}<br>×{fmt_so(b.he_so, 3)}: {fmt_so(b.gia_truoc, 1)} → {fmt_so(b.gia_sau, 1)} triệu")
    nhan.append("Giá theo luật")
    y.append(sd.gia_luat)
    do.append("total")
    van_ban.append(fmt_so(sd.gia_luat, 1))
    hover.append(f"Giá theo luật: {fmt_so(sd.gia_luat, 1)} triệu")
    fig = go.Figure(go.Waterfall(
        x=nhan, y=y, measure=do, text=van_ban, textposition="outside", cliponaxis=False,
        hovertext=hover, hoverinfo="text",
        connector=dict(line=dict(color="#B8C4D6", width=1, dash="dot")),
        increasing=dict(marker=dict(color=AQUA)), decreasing=dict(marker=dict(color=DO)),
        totals=dict(marker=dict(color=NAVY)), width=[0.55] * len(nhan),
    ))
    fig.update_yaxes(title=dict(text="Giá (triệu đồng)", font=dict(size=13)), tickformat=",.0f",
                     range=[0, sd.gia_moi * 1.15])
    fig.update_xaxes(tickfont=dict(size=12.5), tickangle=0, automargin=True)
    fig.update_layout(showlegend=False, bargap=0.35)
    return _bo_cuc(fig, 460, "Từ giá xe mới đến giá theo luật", le_duoi=90)


def tac_dong(kq: KetQuaDinhGia) -> go.Figure:
    buoc = [b for b in kq.suy_dien.buoc_tac_dong_gia if b.nhom != "KHOI_TAO"]
    buoc = sorted(buoc, key=lambda b: abs(b.thay_doi))
    fig = go.Figure(go.Bar(
        y=[f"{b.ma_luat} · {b.ten}" for b in buoc], x=[b.thay_doi for b in buoc], orientation="h",
        marker=dict(color=[AQUA if b.thay_doi > 0 else DO for b in buoc]),
        text=[("+" if b.thay_doi > 0 else "−") + fmt_so(abs(b.thay_doi), 1) for b in buoc],
        textposition="auto", insidetextanchor="middle", cliponaxis=False,
        textfont=dict(size=13), outsidetextfont=dict(color="#1B2433"), insidetextfont=dict(color="#FFFFFF"),
        hovertemplate="%{y}<br>Thay đổi: %{x:,.1f} triệu<extra></extra>",
    ))
    m = max([abs(b.thay_doi) for b in buoc] + [1])
    fig.update_xaxes(title=dict(text="Mức thay đổi giá (triệu đồng)", font=dict(size=13)), tickformat=",.0f",
                     range=[-m * 1.35 if any(b.thay_doi < 0 for b in buoc) else -m * 0.1,
                            m * 1.35 if any(b.thay_doi > 0 for b in buoc) else m * 0.1],
                     zeroline=True, zerolinecolor="#8C9AB2", zerolinewidth=1.5)
    fig.update_layout(showlegend=False, bargap=0.4)
    return _bo_cuc(fig, max(220, 70 + 46 * len(buoc)), "Tác động của từng luật lên giá", le_trai=10)


# ------------------------------------------------------------------ phân tích dữ liệu
def phan_bo_gia(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Histogram(x=df["gia"], nbinsx=40, marker=dict(color=NAVY, line=dict(color="#FFFFFF", width=1)),
                                 hovertemplate="Giá %{x} triệu<br>Số mẫu: %{y}<extra></extra>"))
    trung_vi = float(df["gia"].median())
    fig.add_vline(x=trung_vi, line=dict(color=CAM, width=2, dash="dash"))
    fig.add_annotation(x=trung_vi, y=1, yref="paper", text=f"Trung vị {fmt_so(trung_vi, 0)}", showarrow=False,
                       xanchor="left", yanchor="top", xshift=6, font=dict(color="#B4461C", size=13))
    fig.update_xaxes(title=dict(text="Giá (triệu đồng)", font=dict(size=13)), tickformat=",.0f")
    fig.update_yaxes(title=dict(text="Số mẫu", font=dict(size=13)))
    fig.update_layout(bargap=0.02, showlegend=False)
    return _bo_cuc(fig, 380, "Phân bố giá")


def trung_vi_phan_khuc(df: pd.DataFrame, ten_pk: dict) -> go.Figure:
    g = df.groupby("phan_khuc")["gia"].agg(["median", "count"]).sort_values("median")
    fig = go.Figure(go.Bar(
        y=g.index.tolist(), x=g["median"], orientation="h", marker=dict(color=NAVY),
        text=[fmt_so(v, 0) for v in g["median"]], textposition="outside", cliponaxis=False,
        customdata=np.stack([g["count"], [ten_pk.get(i, i) for i in g.index]], axis=1),
        hovertemplate="%{customdata[1]}<br>Giá trung vị: %{x:,.0f} triệu<br>Số mẫu: %{customdata[0]}<extra></extra>",
    ))
    fig.update_xaxes(title=dict(text="Giá trung vị (triệu đồng)", font=dict(size=13)), tickformat=",.0f",
                     range=[0, float(g["median"].max()) * 1.18])
    fig.update_yaxes(title=dict(text="Phân khúc", font=dict(size=13)))
    fig.update_layout(showlegend=False, bargap=0.35)
    return _bo_cuc(fig, 380, "Giá trung vị theo phân khúc")


def tuoi_va_gia(df: pd.DataFrame) -> go.Figure:
    rng = np.random.default_rng(0)
    jitter = rng.uniform(-0.25, 0.25, len(df))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["tuoi_xe"] + jitter, y=df["gia"], mode="markers", name="Mẫu",
        marker=dict(color=NAVY, size=6, opacity=0.35),
        customdata=np.stack([df["hang"] + " " + df["dong_xe"] + " " + df["phien_ban"], df["so_km"]], axis=1),
        hovertemplate="%{customdata[0]}<br>Tuổi %{x:.0f} năm · %{customdata[1]:,} km<br>Giá %{y:,.0f} triệu<extra></extra>",
    ))
    tv = df.groupby("tuoi_xe")["gia"].median()
    fig.add_trace(go.Scatter(x=tv.index, y=tv.values, mode="lines+markers", name="Giá trung vị theo tuổi",
                             line=dict(color=CAM, width=2.5), marker=dict(size=8, color=CAM),
                             hovertemplate="Tuổi %{x} năm<br>Trung vị %{y:,.0f} triệu<extra></extra>"))
    fig.update_xaxes(title=dict(text="Tuổi xe (năm)", font=dict(size=13)), dtick=1,
                     range=[float(df["tuoi_xe"].min()) - 0.6, float(df["tuoi_xe"].max()) + 0.6])
    fig.update_yaxes(title=dict(text="Giá (triệu đồng)", font=dict(size=13)), tickformat=",.0f")
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right"))
    return _bo_cuc(fig, 430, "Quan hệ giữa tuổi xe và giá")
