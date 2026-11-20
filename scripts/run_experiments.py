"""Thực nghiệm trên TẬP TEST: so sánh Chỉ luật, Chỉ CBR, Random Forest và Hệ lai luật + CBR.

- Kho tình huống CBR và RF chỉ dùng tập train; tham số đã chọn trên validation (tune_parameters.py).
- Đo thời gian từng ca bằng time.perf_counter, chạy tuần tự trong một tiến trình, bỏ qua 20 ca khởi động.
- Lưu: outputs/results/predictions_test.csv, metrics.json, metrics_summary.csv, metrics_same_subset.csv,
       metrics_by_group.csv, metrics_by_confidence.csv, timing.csv, demo_cases.json, environment.json

Chạy:  python scripts/run_experiments.py
"""
import json
import os
import platform
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import sklearn  # noqa: E402
import streamlit  # noqa: E402

from carval.cbr import dau_vao_tu_dong  # noqa: E402
from carval.evaluation import RandomForestDoiChung, chi_so  # noqa: E402
from carval.kb import KnowledgeBase  # noqa: E402
from carval.paths import RESULTS_DIR, TEST_CSV, TRAIN_CSV  # noqa: E402
from carval.service import DichVuDinhGia  # noqa: E402

PHUONG_PHAP = ["Chỉ luật", "Chỉ CBR", "Random Forest", "Hệ lai luật + CBR"]
SO_CA_KHOI_DONG = 20
SO_BOOTSTRAP = 2000


def cpu_info() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "không xác định"


def nhom_ca(r) -> str:
    if r["ngap_nuoc"] or r["tai_nan_nang"]:
        return "Ngập nước/tai nạn nặng"
    if r["chay_dich_vu"]:
        return "Chạy dịch vụ"
    return "Thông thường"


def main():
    kb = KnowledgeBase.tu_thu_muc()
    train, test = pd.read_csv(TRAIN_CSV), pd.read_csv(TEST_CSV)
    assert not set(train["ma_tin"]) & set(test["ma_tin"])
    svc = DichVuDinhGia(kb=kb, kho_df=train)
    rf_params = json.loads((RESULTS_DIR / "rf_params.json").read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    rf = RandomForestDoiChung(kb, **rf_params).fit(train)
    t_huan_luyen_rf = time.perf_counter() - t0
    t0 = time.perf_counter()
    rf_batch = rf.du_doan(test)
    t_rf_lo = (time.perf_counter() - t0) * 1000 / len(test)
    rf.chi_mot_luong()

    # khởi động (không ghi nhận thời gian)
    for _, r in test.head(SO_CA_KHOI_DONG).iterrows():
        dv = dau_vao_tu_dong(r)
        svc.dinh_gia(dv)
        rf.du_doan(test.loc[[_]])

    dong = []
    for i, r in test.iterrows():
        dv = dau_vao_tu_dong(r)
        t = time.perf_counter()
        sd = svc.engine.suy_dien(dv)
        t_luat = (time.perf_counter() - t) * 1000

        t = time.perf_counter()
        sd2 = svc.engine.suy_dien(dv)  # CBR cần giá luật của truy vấn để hiệu chỉnh – tính cả thời gian này
        cbr = svc.kho.truy_hoi(dv, sd2.gia_luat)
        t_cbr = (time.perf_counter() - t) * 1000
        cbr_khong_hc = svc.kho.truy_hoi(dv, sd2.gia_luat, hieu_chinh=False)

        t = time.perf_counter()
        kq = svc.dinh_gia(dv)
        t_lai = (time.perf_counter() - t) * 1000

        t = time.perf_counter()
        p_rf = float(rf.du_doan(test.loc[[i]])[0])
        t_rf = (time.perf_counter() - t) * 1000

        kh = kq.ket_hop
        dong.append({
            "ma_tin": r["ma_tin"], "phien_ban_id": r["phien_ban_id"], "phan_khuc": r["phan_khuc"],
            "nam_sx": r["nam_sx"], "so_km": r["so_km"], "tinh_trang": r["tinh_trang"],
            "ngap_nuoc": r["ngap_nuoc"], "tai_nan_nang": r["tai_nan_nang"], "chay_dich_vu": r["chay_dich_vu"],
            "nhom": nhom_ca(r), "gia_thuc": r["gia"],
            "p_luat": sd.gia_luat,
            "p_cbr": cbr.gia_cbr if cbr.gia_cbr is not None else np.nan,
            "p_cbr_khong_hieu_chinh": cbr_khong_hc.gia_cbr if cbr_khong_hc.gia_cbr is not None else np.nan,
            "p_rf": p_rf, "p_rf_lo": float(rf_batch[test.index.get_loc(i)]),
            "p_he_lai": kh.gia_de_xuat, "khoang_thap": kh.khoang_thap, "khoang_cao": kh.khoang_cao, "delta": kh.delta,
            "n_cbr": cbr.n, "sim_tb": cbr.sim_tb if cbr.sim_tb is not None else np.nan, "w_cbr": kh.w_cbr,
            "muc_tin_cay": kh.muc_tin_cay, "trang_thai_cbr": cbr.trang_thai,
            "t_luat_ms": t_luat, "t_cbr_ms": t_cbr, "t_rf_ms": t_rf, "t_he_lai_ms": t_lai,
        })
    pr = pd.DataFrame(dong)
    pr["trong_khoang"] = (pr["gia_thuc"] >= pr["khoang_thap"]) & (pr["gia_thuc"] <= pr["khoang_cao"])
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    pr.to_csv(RESULTS_DIR / "predictions_test.csv", index=False, encoding="utf-8")

    y = pr["gia_thuc"].to_numpy()
    co_cbr = pr["p_cbr"].notna().to_numpy()
    cot = {"Chỉ luật": "p_luat", "Chỉ CBR": "p_cbr", "Random Forest": "p_rf", "Hệ lai luật + CBR": "p_he_lai"}

    # Bảng chính: toàn bộ test (CBR chỉ tính trên ca có kết quả, ghi rõ n)
    tong_hop = []
    for ten, c in cot.items():
        m = co_cbr if ten == "Chỉ CBR" else np.ones(len(pr), bool)
        ct = chi_so(y[m], pr[c].to_numpy()[m])
        ct.update({"phuong_phap": ten, "pham_vi": "ca có kết quả CBR" if ten == "Chỉ CBR" else "toàn bộ test"})
        tong_hop.append(ct)
    # CBR + dùng giá luật khi thiếu ca (để có n đầy đủ)
    p_cbr_fb = np.where(co_cbr, pr["p_cbr"], pr["p_luat"])
    ct = chi_so(y, p_cbr_fb)
    ct.update({"phuong_phap": "Chỉ CBR (thiếu ca → giá luật)", "pham_vi": "toàn bộ test"})
    tong_hop.append(ct)
    ct = chi_so(y[co_cbr], pr["p_cbr_khong_hieu_chinh"].to_numpy()[co_cbr])
    ct.update({"phuong_phap": "CBR không hiệu chỉnh (ablation)", "pham_vi": "ca có kết quả CBR"})
    tong_hop.append(ct)
    bang = pd.DataFrame(tong_hop)
    # thời gian
    tg = {"Chỉ luật": "t_luat_ms", "Chỉ CBR": "t_cbr_ms", "Random Forest": "t_rf_ms", "Hệ lai luật + CBR": "t_he_lai_ms"}
    dong_tg = []
    for ten, c in tg.items():
        v = pr[c].to_numpy()
        dong_tg.append({"phuong_phap": ten, "tb_ms": float(v.mean()), "trung_vi_ms": float(np.median(v)),
                        "p95_ms": float(np.percentile(v, 95)), "max_ms": float(v.max())})
    bang_tg = pd.DataFrame(dong_tg)
    bang = bang.merge(bang_tg[["phuong_phap", "tb_ms", "p95_ms"]], on="phuong_phap", how="left")
    bang.to_csv(RESULTS_DIR / "metrics_summary.csv", index=False, encoding="utf-8")
    bang_tg.to_csv(RESULTS_DIR / "timing.csv", index=False, encoding="utf-8")

    # Cùng tập con (ca có CBR) cho cả bốn phương pháp
    cung = []
    for ten, c in cot.items():
        ct = chi_so(y[co_cbr], pr[c].to_numpy()[co_cbr])
        ct["phuong_phap"] = ten
        cung.append(ct)
    pd.DataFrame(cung).to_csv(RESULTS_DIR / "metrics_same_subset.csv", index=False, encoding="utf-8")

    # Theo nhóm ca
    nhom = []
    for g, d in pr.groupby("nhom"):
        for ten, c in cot.items():
            m = d[c].notna()
            if m.sum() == 0:
                continue
            ct = chi_so(d.loc[m, "gia_thuc"], d.loc[m, c])
            ct.update({"nhom": g, "phuong_phap": ten})
            nhom.append(ct)
    pd.DataFrame(nhom).to_csv(RESULTS_DIR / "metrics_by_group.csv", index=False, encoding="utf-8")

    # Theo mức tin cậy (hệ lai)
    tc = []
    for muc in ["Cao", "Trung bình", "Thấp"]:
        d = pr[pr["muc_tin_cay"] == muc]
        if len(d) == 0:
            continue
        ct = chi_so(d["gia_thuc"], d["p_he_lai"])
        ct.update({"muc_tin_cay": muc, "ty_le_trong_khoang": float(d["trong_khoang"].mean() * 100),
                   "do_rong_tb_phan_tram": float(((d["khoang_cao"] - d["khoang_thap"]) / d["p_he_lai"]).mean() * 100)})
        tc.append(ct)
    pd.DataFrame(tc).to_csv(RESULTS_DIR / "metrics_by_confidence.csv", index=False, encoding="utf-8")

    # Bootstrap ghép cặp cho chênh lệch MAE (hệ lai − phương pháp khác) trên toàn bộ test
    rng = np.random.default_rng(2026)
    ae_lai = np.abs(pr["p_he_lai"] - y).to_numpy()
    bs = {}
    for ten, arr in (("Chỉ luật", pr["p_luat"].to_numpy()), ("Random Forest", pr["p_rf"].to_numpy()),
                     ("Chỉ CBR (thiếu ca → giá luật)", p_cbr_fb)):
        ae = np.abs(arr - y)
        diff = []
        for _ in range(SO_BOOTSTRAP):
            idx = rng.integers(0, len(y), len(y))
            diff.append(ae_lai[idx].mean() - ae[idx].mean())
        diff = np.array(diff)
        bs[ten] = {"chenh_MAE": float(ae_lai.mean() - ae.mean()), "ci95_thap": float(np.percentile(diff, 2.5)),
                   "ci95_cao": float(np.percentile(diff, 97.5))}

    # Kịch bản demo (đúng số liệu giao diện hiển thị)
    demo = []
    for s in kb.kich_ban:
        kq = svc.dinh_gia(s["dau_vao"])
        d = kq.tom_tat()
        d.update({"id": s["id"], "ten": s["ten"], "mo_ta": s["mo_ta"]})
        if kq.cbr.xe:
            d["can_cu_hieu_chinh"] = [svc.kho.can_cu_hieu_chinh(kq.suy_dien, x) for x in kq.cbr.xe]
        demo.append(d)
    with open(RESULTS_DIR / "demo_cases.json", "w", encoding="utf-8") as f:
        json.dump(demo, f, ensure_ascii=False, indent=2, default=float)

    moi_truong = {
        "thoi_diem_chay": time.strftime("%Y-%m-%d %H:%M:%S"),
        "he_dieu_hanh": platform.platform(), "cpu": cpu_info(), "so_luong_cpu": os.cpu_count(),
        "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
        "scikit_learn": sklearn.__version__, "streamlit": streamlit.__version__,
        "cach_do": ("time.perf_counter quanh từng lệnh dự đoán một ca; tuần tự, một tiến trình; bỏ qua "
                    f"{SO_CA_KHOI_DONG} ca khởi động; RF dự đoán từng ca với n_jobs=1. "
                    "Chỉ luật: suy diễn tiến. Chỉ CBR: suy diễn giá luật truy vấn + truy hồi + hiệu chỉnh. "
                    "Hệ lai: toàn bộ dinh_gia() gồm kiểm tra nhập, suy diễn, CBR, kết hợp. Không gồm thời gian vẽ giao diện."),
    }
    with open(RESULTS_DIR / "environment.json", "w", encoding="utf-8") as f:
        json.dump(moi_truong, f, ensure_ascii=False, indent=2)

    ket_qua = {
        "nguon_du_lieu": "Dữ liệu mô phỏng (không phải dữ liệu thị trường)",
        "so_train": len(train), "so_test": len(test),
        "so_ca_test_co_cbr": int(co_cbr.sum()), "so_ca_test_thieu_cbr": int((~co_cbr).sum()),
        "tham_so": {"cbr": kb.config["cbr"], "ket_hop": kb.config["ket_hop"], "khoang_gia": kb.config["khoang_gia"],
                    "rf": rf_params},
        "bang_chinh": tong_hop,
        "cung_tap_con_co_cbr": cung,
        "thoi_gian_ms": dong_tg,
        "rf_huan_luyen_giay": t_huan_luyen_rf,
        "rf_du_doan_theo_lo_ms_moi_ca": t_rf_lo,
        "khoang_gia_he_lai": {
            "ty_le_trong_khoang": float(pr["trong_khoang"].mean() * 100),
            "do_rong_tb_trieu": float((pr["khoang_cao"] - pr["khoang_thap"]).mean()),
            "do_rong_tb_phan_tram": float(((pr["khoang_cao"] - pr["khoang_thap"]) / pr["p_he_lai"]).mean() * 100),
            "delta_tb": float(pr["delta"].mean()),
        },
        "phan_bo_muc_tin_cay": pr["muc_tin_cay"].value_counts().to_dict(),
        "w_cbr_tb": float(pr["w_cbr"].mean()),
        "bootstrap_chenh_MAE_he_lai_tru": bs,
        "moi_truong": moi_truong,
    }
    with open(RESULTS_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(ket_qua, f, ensure_ascii=False, indent=2)

    pd.set_option("display.width", 200)
    print(bang[["phuong_phap", "pham_vi", "n", "MAE", "MAPE", "R2", "ty_le_sai_so_duoi_10", "tb_ms", "p95_ms"]].to_string(index=False))
    print("Cùng tập con:\n", pd.DataFrame(cung)[["phuong_phap", "n", "MAE", "MAPE", "R2"]].to_string(index=False))
    print("Khoảng giá:", ket_qua["khoang_gia_he_lai"])
    print("Mức tin cậy:", ket_qua["phan_bo_muc_tin_cay"])
    print("Bootstrap:", json.dumps(bs, ensure_ascii=False, indent=1))
    print(pd.DataFrame(tc).to_string(index=False))
    print(pd.DataFrame(nhom)[["nhom", "phuong_phap", "n", "MAE", "MAPE"]].to_string(index=False))


if __name__ == "__main__":
    main()
