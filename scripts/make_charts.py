"""Vẽ biểu đồ thực nghiệm TỪ CÁC FILE KẾT QUẢ (outputs/results/*.csv, *.json) → outputs/charts/*.png.

Chạy:  python scripts/make_charts.py
"""
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from carval.formatting import fmt_so  # noqa: E402
from carval.paths import CHARTS_DIR, PROCESSED_DIR, RESULTS_DIR  # noqa: E402

PP = ["Chỉ luật", "Chỉ CBR", "Random Forest", "Hệ lai luật + CBR"]
MAU = {"Chỉ luật": "#2A78D6", "Chỉ CBR": "#1BAF7A", "Random Forest": "#6250D6", "Hệ lai luật + CBR": "#EB6834"}
NAVY = "#1F3B73"
CHU = "#1B2433"
PHU = "#52607A"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#C9D3E3", "axes.labelcolor": CHU,
    "xtick.color": PHU, "ytick.color": PHU, "axes.titleweight": "bold", "axes.titlesize": 11,
    "axes.titlecolor": "#15284F", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#EEF1F6", "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.dpi": 100, "savefig.dpi": 220, "savefig.bbox": "tight", "legend.frameon": False,
})
VN = FuncFormatter(lambda x, _: fmt_so(x, 0) if abs(x) >= 1 or x == 0 else fmt_so(x, 2))


def vn(so_le):
    return FuncFormatter(lambda x, _: fmt_so(x, so_le))


def luu(fig, ten):
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHARTS_DIR / ten, facecolor="white")
    plt.close(fig)
    print("Đã lưu", ten)


def nhan_cot(ax, bars, so_le=1, hau_to=""):
    for b in bars:
        h = b.get_height()
        ax.annotate(fmt_so(h, so_le) + hau_to, (b.get_x() + b.get_width() / 2, h), xytext=(0, 3),
                    textcoords="offset points", ha="center", va="bottom", fontsize=9, color=CHU)


def ten_ngan(t):
    return {"Hệ lai luật + CBR": "Hệ lai\nluật + CBR", "Random Forest": "Random\nForest"}.get(t, t)


def bd_sai_so(m):
    bang = pd.DataFrame(m["bang_chinh"]).set_index("phuong_phap").loc[PP]
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.6))
    for ax, cot, ten, sl, ht in ((axs[0], "MAE", "MAE (triệu đồng)", 1, ""), (axs[1], "MAPE", "MAPE (%)", 2, "%"),
                                 (axs[2], "R2", "R²", 3, "")):
        v = bang[cot].to_numpy()
        bars = ax.bar(range(4), v, color=[MAU[p] for p in PP], width=0.62, edgecolor="white", linewidth=1.5)
        nhan_cot(ax, bars, sl, ht)
        ax.set_xticks(range(4), [ten_ngan(p) for p in PP], fontsize=8.5)
        ax.set_title(ten)
        ax.yaxis.set_major_formatter(vn(2 if cot == "R2" else 0))
        if cot == "R2":
            ax.set_ylim(0.9, 1.0)
        else:
            ax.set_ylim(0, v.max() * 1.2)
    n_cbr = int(bang.loc["Chỉ CBR", "n"])
    fig.text(0.5, -0.04, f"Tập test {m['so_test']} ca (dữ liệu mô phỏng). Chỉ CBR tính trên {n_cbr} ca có kết quả; "
             "các phương pháp khác trên toàn bộ test.", ha="center", fontsize=8.5, color=PHU)
    fig.tight_layout()
    luu(fig, "ch01_so_sanh_sai_so.png")


def bd_thuc_te_du_doan(pr):
    fig, axs = plt.subplots(2, 2, figsize=(8.6, 7.6), sharex=True, sharey=True)
    cot = {"Chỉ luật": "p_luat", "Chỉ CBR": "p_cbr", "Random Forest": "p_rf", "Hệ lai luật + CBR": "p_he_lai"}
    lim = [0, max(pr["gia_thuc"].max(), pr[list(cot.values())].max().max()) * 1.05]
    for ax, p in zip(axs.flat, PP):
        d = pr[pr[cot[p]].notna()]
        ax.scatter(d["gia_thuc"], d[cot[p]], s=9, alpha=0.45, color=MAU[p], edgecolors="none")
        ax.plot(lim, lim, color="#8C9AB2", lw=1, ls="--")
        ax.set_title(f"{p} (n = {len(d)})")
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.xaxis.set_major_formatter(VN)
        ax.yaxis.set_major_formatter(VN)
    for ax in axs[1]:
        ax.set_xlabel("Giá thực tế (triệu đồng)")
    for ax in axs[:, 0]:
        ax.set_ylabel("Giá dự đoán (triệu đồng)")
    fig.tight_layout()
    luu(fig, "ch02_thuc_te_du_doan.png")


def bd_phan_bo_sai_so(pr):
    cot = {"Chỉ luật": "p_luat", "Chỉ CBR": "p_cbr", "Random Forest": "p_rf", "Hệ lai luật + CBR": "p_he_lai"}
    du_lieu = []
    for p in PP:
        d = pr[pr[cot[p]].notna()]
        du_lieu.append((np.abs(d[cot[p]] - d["gia_thuc"]) / d["gia_thuc"] * 100).to_numpy())
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    bp = ax.boxplot(du_lieu, tick_labels=[ten_ngan(p) for p in PP], showfliers=False, patch_artist=True, widths=0.5,
                    medianprops=dict(color=CHU, lw=1.5))
    for patch, p in zip(bp["boxes"], PP):
        patch.set_facecolor(MAU[p])
        patch.set_alpha(0.75)
        patch.set_edgecolor("white")
    for i, v in enumerate(du_lieu, 1):
        ax.annotate(f"P90 = {fmt_so(np.percentile(v, 90), 1)}%", (i, np.percentile(v, 75)), xytext=(28, 2),
                    textcoords="offset points", fontsize=8.5, color=PHU)
    ax.set_ylabel("Sai số tuyệt đối tương đối (%)")
    ax.yaxis.set_major_formatter(vn(0))
    ax.set_title("Phân bố sai số phần trăm trên tập test (không vẽ điểm ngoại lai)")
    fig.tight_layout()
    luu(fig, "ch03_phan_bo_sai_so.png")


def bd_theo_nhom():
    g = pd.read_csv(RESULTS_DIR / "metrics_by_group.csv")
    nhom = ["Thông thường", "Chạy dịch vụ", "Ngập nước/tai nạn nặng"]
    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    w = 0.2
    for i, p in enumerate(PP):
        v = [float(g[(g["nhom"] == n) & (g["phuong_phap"] == p)]["MAPE"].iloc[0]) for n in nhom]
        bars = ax.bar(np.arange(3) + (i - 1.5) * w, v, width=w, color=MAU[p], label=p, edgecolor="white", linewidth=1.2)
        nhan_cot(ax, bars, 1)
    so = [int(g[(g["nhom"] == n) & (g["phuong_phap"] == "Hệ lai luật + CBR")]["n"].iloc[0]) for n in nhom]
    ax.set_xticks(range(3), [f"{n}\n(n = {s})" for n, s in zip(nhom, so)])
    ax.set_ylabel("MAPE (%)")
    ax.yaxis.set_major_formatter(vn(0))
    ax.legend(ncol=4, loc="upper left", fontsize=8.5)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.15)
    ax.set_title("MAPE theo nhóm ca trên tập test")
    fig.tight_layout()
    luu(fig, "ch04_sai_so_theo_nhom.png")


def bd_thoi_gian():
    t = pd.read_csv(RESULTS_DIR / "timing.csv").set_index("phuong_phap").loc[PP]
    fig, ax = plt.subplots(figsize=(8.2, 3.2))
    y = np.arange(4)
    ax.barh(y + 0.18, t["tb_ms"], height=0.34, color=[MAU[p] for p in PP], label="Trung bình")
    ax.barh(y - 0.18, t["p95_ms"], height=0.34, color=[MAU[p] for p in PP], alpha=0.45, label="P95")
    for i, p in enumerate(PP):
        ax.annotate(f"TB {fmt_so(t.loc[p, 'tb_ms'], 2)} ms", (t.loc[p, "tb_ms"], i + 0.18), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8.5)
        ax.annotate(f"P95 {fmt_so(t.loc[p, 'p95_ms'], 2)} ms", (t.loc[p, "p95_ms"], i - 0.18), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8.5, color=PHU)
    ax.set_yticks(y, PP)
    ax.set_xscale("log")
    ax.set_xlabel("Thời gian xử lý một ca (ms, thang logarit)")
    ax.set_xlim(0.1, t["p95_ms"].max() * 6)
    ax.xaxis.set_major_formatter(vn(1))
    ax.invert_yaxis()
    ax.set_title("Thời gian xử lý mỗi ca trên tập test (thanh đậm: trung bình, thanh nhạt: P95)")
    fig.tight_layout()
    luu(fig, "ch05_thoi_gian.png")


def bd_chon_tham_so():
    tk = pd.read_csv(RESULTS_DIR / "tuning_cbr_theta_k.csv")
    w = pd.read_csv(RESULTS_DIR / "tuning_w_max.csv")
    d = pd.read_csv(RESULTS_DIR / "tuning_delta_min.csv")
    tt = json.loads((RESULTS_DIR / "tuning_summary.json").read_text(encoding="utf-8"))["da_chon"]
    fig, axs = plt.subplots(2, 2, figsize=(9.6, 6.6))
    a = tk[tk["k"] == 5]
    ax = axs[0, 0]
    ax.plot(a["theta"], a["MAE_CBR"], marker="o", color=NAVY)
    for x, yv, c in zip(a["theta"], a["MAE_CBR"], a["ty_le_co_ket_qua"]):
        ax.annotate(f"{fmt_so(c * 100, 0)}%", (x, yv), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=7.5, color=PHU)
    ax.axvline(tt["theta"], color="#EB6834", ls="--", lw=1.2)
    ax.set_ylim(a["MAE_CBR"].min() - 0.3, a["MAE_CBR"].max() + 0.5)
    ax.set_title("(a) MAE của CBR theo ngưỡng θ (k = 5)")
    ax.set_xlabel("Ngưỡng θ (nhãn: % ca có kết quả)")
    ax.set_ylabel("MAE (triệu đồng)")
    ax.xaxis.set_major_formatter(vn(2))
    ax.yaxis.set_major_formatter(vn(1))
    b = tk[tk["theta"] == tt["theta"]]
    ax = axs[0, 1]
    ax.plot(b["k"], b["MAE_CBR"], marker="o", color=NAVY)
    ax.axvline(tt["k"], color="#EB6834", ls="--", lw=1.2)
    ax.set_title(f"(b) MAE của CBR theo k (θ = {fmt_so(tt['theta'], 2)})")
    ax.set_xlabel("Số xe tương tự tối đa k")
    ax.set_ylabel("MAE (triệu đồng)")
    ax.set_xticks(b["k"])
    ax.yaxis.set_major_formatter(vn(1))
    ax = axs[1, 0]
    ax.plot(w["w_max"], w["MAE_he_lai"], marker="o", color=NAVY)
    ax.axvline(tt["w_max"], color="#EB6834", ls="--", lw=1.2)
    ax.set_title("(c) MAE của hệ lai theo w_max")
    ax.set_xlabel("w_max (trọng số CBR tối đa)")
    ax.set_ylabel("MAE (triệu đồng)")
    ax.xaxis.set_major_formatter(vn(1))
    ax.yaxis.set_major_formatter(vn(1))
    ax = axs[1, 1]
    ax.plot(d["delta_min"], d["ty_le_trong_khoang"] * 100, marker="o", color=NAVY)
    for x, yv, wd in zip(d["delta_min"], d["ty_le_trong_khoang"] * 100, d["do_rong_tb_phan_tram"]):
        ax.annotate(f"rộng {fmt_so(wd, 0)}%", (x, yv), xytext=(6, -4), textcoords="offset points", ha="left", va="top", fontsize=7.5, color=PHU)
    ax.axhline(80, color="#8C9AB2", ls=":", lw=1)
    ax.axvline(tt["delta_min"], color="#EB6834", ls="--", lw=1.2)
    ax.set_xlim(d["delta_min"].min() - 0.01, d["delta_min"].max() + 0.02)
    ax.set_title("(d) Tỷ lệ giá thật nằm trong khoảng theo δ_min")
    ax.set_xlabel("δ_min")
    ax.set_ylabel("Tỷ lệ trong khoảng (%)")
    ax.xaxis.set_major_formatter(vn(2))
    ax.yaxis.set_major_formatter(vn(0))
    fig.suptitle("Chọn tham số trên tập validation (đường cam: giá trị được chọn)", fontsize=11, fontweight="bold", color="#15284F")
    fig.tight_layout()
    luu(fig, "ch06_chon_tham_so.png")


def bd_tin_cay():
    tc = pd.read_csv(RESULTS_DIR / "metrics_by_confidence.csv")
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.3))
    nhan = [f"{m}\n(n = {n})" for m, n in zip(tc["muc_tin_cay"], tc["n"])]
    for ax, cot, ten, sl in ((axs[0], "MAPE", "MAPE của hệ lai (%)", 2), (axs[1], "ty_le_trong_khoang", "Tỷ lệ giá thật trong khoảng (%)", 1),
                             (axs[2], "do_rong_tb_phan_tram", "Độ rộng khoảng TB (% giá đề xuất)", 1)):
        bars = ax.bar(range(len(tc)), tc[cot], color=NAVY, width=0.55)
        nhan_cot(ax, bars, sl)
        ax.set_xticks(range(len(tc)), nhan)
        ax.set_title(ten, fontsize=10)
        ax.set_ylim(0, tc[cot].max() * 1.22)
        ax.yaxis.set_major_formatter(vn(0))
    fig.tight_layout()
    luu(fig, "ch07_theo_muc_tin_cay.png")


def bd_lam_sach():
    log = json.loads((PROCESSED_DIR / "cleaning_log.json").read_text(encoding="utf-8"))
    buoc = [b for b in log["cac_buoc"] if b["buoc"][0] in "0123456"]
    fig, axs = plt.subplots(1, 2, figsize=(10.4, 3.7), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axs[0]
    ten = [b["buoc"] for b in buoc]
    sau = [b["sau"] for b in buoc]
    bars = ax.barh(range(len(buoc)), sau, color=NAVY, height=0.6)
    for i, b in enumerate(buoc):
        ax.annotate(fmt_so(b["sau"]) + (f"  (−{b['bi_loai']})" if b["bi_loai"] else ""), (b["sau"], i), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8.5)
    ax.set_yticks(range(len(buoc)), ten, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(2800, max(sau) * 1.03)
    ax.xaxis.set_major_formatter(VN)
    ax.set_xlabel("Số bản ghi còn lại")
    ax.set_title("Số bản ghi sau từng bước làm sạch")
    ax = axs[1]
    ct = log["chia_tap"]
    pk = sorted(set(ct["train_theo_phan_khuc"]) | set(ct["test_theo_phan_khuc"]))
    tr = [ct["train_theo_phan_khuc"].get(p, 0) for p in pk]
    te = [ct["test_theo_phan_khuc"].get(p, 0) for p in pk]
    ax.bar(range(len(pk)), tr, color="#2A78D6", label=f"Train ({fmt_so(ct['so_train'])})", width=0.7)
    ax.bar(range(len(pk)), te, bottom=tr, color="#EB6834", label=f"Test ({fmt_so(ct['so_test'])})", width=0.7)
    ax.set_xticks(range(len(pk)), pk, fontsize=8.5)
    ax.set_ylabel("Số bản ghi")
    ax.legend(fontsize=8.5)
    ax.set_title("Chia train/test phân tầng theo phân khúc")
    fig.tight_layout()
    luu(fig, "ch08_lam_sach_chia_tap.png")


def main():
    m = json.loads((RESULTS_DIR / "metrics.json").read_text(encoding="utf-8"))
    pr = pd.read_csv(RESULTS_DIR / "predictions_test.csv")
    bd_sai_so(m)
    bd_thuc_te_du_doan(pr)
    bd_phan_bo_sai_so(pr)
    bd_theo_nhom()
    bd_thoi_gian()
    bd_chon_tham_so()
    bd_tin_cay()
    bd_lam_sach()


if __name__ == "__main__":
    main()
