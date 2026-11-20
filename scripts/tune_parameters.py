"""Chọn tham số trên tập VALIDATION tách từ train (không dùng tập test).

Quy tắc chọn (đặt trước khi chạy):
  - k: cố định k_toi_da = 5 theo yêu cầu thiết kế (bảng xe tương tự ≤ 5 dòng để giải thích được);
       vẫn ghi kết quả k = 1, 3, 5, 7, 10 để tham khảo.
  - θ (ngưỡng tương tự): trong các θ để CBR trả kết quả cho ≥ 95% ca validation, chọn θ LỚN NHẤT có MAE của CBR
       không vượt quá MAE nhỏ nhất quá 1% (quy tắc dung sai: khi sai số tương đương, ưu tiên ngưỡng chặt hơn để
       các xe so sánh thực sự giống xe cần định giá). Quy tắc dung sai được thêm sau lần chạy đầu cho thấy MAE gần
       như không đổi trong khoảng θ = 0,60–0,75; toàn bộ việc chọn chỉ dùng validation.
  - w_max (trọng số CBR tối đa): w_max cho MAE của hệ lai nhỏ nhất trên validation.
  - δ_min: giá trị nhỏ nhất làm tỷ lệ giá thật nằm trong khoảng ≥ 80% trên validation (mục tiêu kinh nghiệm).
  - Random Forest: lưới nhỏ min_samples_leaf × max_features, chọn MAE validation nhỏ nhất.

Chạy:  python scripts/tune_parameters.py [--apply]
  --apply ghi θ, w_max, δ_min vào kb/config.json và tham số RF vào outputs/results/rf_params.json.
"""
import argparse
import copy
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from carval.cbr import KhoTinhHuong, dau_vao_tu_dong  # noqa: E402
from carval.combine import ket_hop  # noqa: E402
from carval.evaluation import RandomForestDoiChung, chi_so  # noqa: E402
from carval.inference import ForwardChainingEngine  # noqa: E402
from carval.kb import KnowledgeBase  # noqa: E402
from carval.paths import KB_DIR, RESULTS_DIR, TRAIN_CSV  # noqa: E402

THETA = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
K_LIST = [1, 3, 5, 7, 10]
W_MAX = [0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
DELTA_MIN = [0.04, 0.06, 0.08, 0.10, 0.12, 0.14]
RF_GRID = [(leaf, mf) for leaf in (1, 3, 5) for mf in (1.0, 0.5, "sqrt")]
K_CO_DINH = 5
PHU_TOI_THIEU = 0.95
DUNG_SAI_THETA = 0.01
MUC_TIEU_PHU_KHOANG = 0.80


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    kb = KnowledgeBase.tu_thu_muc()
    train = pd.read_csv(TRAIN_CSV)
    sub, val = train_test_split(train, test_size=0.2, random_state=7, stratify=train["phan_khuc"])
    sub, val = sub.reset_index(drop=True), val.reset_index(drop=True)
    print(f"Train {len(train)} → sub-train {len(sub)} (kho CBR) + validation {len(val)}")
    eng = ForwardChainingEngine(kb)
    kho = KhoTinhHuong(sub, kb, eng)
    y = val["gia"].to_numpy(float)

    # Truy hồi một lần với θ thấp nhất, k lớn nhất; các cấu hình khác là tập con theo thứ tự hạng.
    ds = []
    for _, r in val.iterrows():
        dv = dau_vao_tu_dong(r)
        sd = eng.suy_dien(dv)
        kq = kho.truy_hoi(dv, sd.gia_luat, k=max(K_LIST), nguong=min(THETA))
        ds.append((dv, sd, kq))
    p_luat = np.array([sd.gia_luat for _, sd, _ in ds])

    def cbr_cfg(theta, k):
        out = []
        for _, _, kq in ds:
            xe = [x for x in kq.xe if x.do_tuong_tu >= theta - 1e-12][:k]
            if not xe:
                out.append((np.nan, 0, np.nan, 0.0))
                continue
            s = np.array([x.do_tuong_tu for x in xe])
            p = np.array([x.gia_hieu_chinh for x in xe])
            g = float((s * p).sum() / s.sum())
            cv = float(np.sqrt((s * (p - g) ** 2).sum() / s.sum()) / g) if len(xe) > 1 else 0.0
            out.append((g, len(xe), float(s.mean()), cv))
        return out

    # 1) θ × k
    dong = []
    for theta in THETA:
        for k in K_LIST:
            res = cbr_cfg(theta, k)
            g = np.array([r[0] for r in res])
            m = ~np.isnan(g)
            ct = chi_so(y[m], g[m]) if m.any() else {"MAE": np.nan, "MAPE": np.nan}
            dong.append({"theta": theta, "k": k, "ty_le_co_ket_qua": float(m.mean()), "MAE_CBR": ct["MAE"], "MAPE_CBR": ct["MAPE"],
                         "so_xe_tb": float(np.mean([r[1] for r in res]))})
    bang_tk = pd.DataFrame(dong)
    hop_le = bang_tk[(bang_tk["k"] == K_CO_DINH) & (bang_tk["ty_le_co_ket_qua"] >= PHU_TOI_THIEU)]
    mae_tot = float(hop_le["MAE_CBR"].min())
    theta_chon = float(hop_le[hop_le["MAE_CBR"] <= mae_tot * (1 + DUNG_SAI_THETA)]["theta"].max())
    res_chon = cbr_cfg(theta_chon, K_CO_DINH)

    # 2) w_max (hệ lai) với θ, k đã chọn
    def hybrid(w_max, delta_min):
        cfg = copy.deepcopy(kb.config)
        cfg["ket_hop"]["w_cbr_toi_da"] = w_max
        cfg["khoang_gia"]["delta_min"] = delta_min
        P, LO, HI = [], [], []
        for (dv, sd, _), (g, n, sim, cv) in zip(ds, res_chon):
            class _C:  # đối tượng tối thiểu có cùng thuộc tính KetQuaCBR dùng trong ket_hop
                pass
            c = _C()
            c.k, c.gia_cbr, c.sim_tb, c.cv = K_CO_DINH, (None if n == 0 else g), (None if n == 0 else sim), cv
            c.n = n
            co_cy = any(cb["muc"] == "chu_y" for cb in sd.canh_bao)
            kh = ket_hop(sd.gia_luat, c, sd.co_canh_bao_nghiem_trong, co_cy, cfg)
            P.append(kh.gia_de_xuat)
            LO.append(kh.khoang_thap)
            HI.append(kh.khoang_cao)
        return np.array(P), np.array(LO), np.array(HI)

    dong_w = []
    d0 = kb.config["khoang_gia"]["delta_min"]
    for w in W_MAX:
        P, _, _ = hybrid(w, d0)
        ct = chi_so(y, P)
        dong_w.append({"w_max": w, "MAE_he_lai": ct["MAE"], "MAPE_he_lai": ct["MAPE"], "R2": ct["R2"]})
    bang_w = pd.DataFrame(dong_w)
    w_chon = float(bang_w.sort_values(["MAE_he_lai", "w_max"]).iloc[0]["w_max"])

    # 3) δ_min
    dong_d = []
    for dmin in DELTA_MIN:
        P, LO, HI = hybrid(w_chon, dmin)
        dong_d.append({"delta_min": dmin, "ty_le_trong_khoang": float(((y >= LO) & (y <= HI)).mean()),
                       "do_rong_tb_trieu": float((HI - LO).mean()), "do_rong_tb_phan_tram": float(((HI - LO) / P).mean() * 100)})
    bang_d = pd.DataFrame(dong_d)
    dat = bang_d[bang_d["ty_le_trong_khoang"] >= MUC_TIEU_PHU_KHOANG]
    d_chon = float(dat["delta_min"].min()) if len(dat) else float(max(DELTA_MIN))

    # 4) Random Forest
    dong_rf = []
    for leaf, mf in RF_GRID:
        rf = RandomForestDoiChung(kb, min_samples_leaf=leaf, max_features=mf).fit(sub)
        ct = chi_so(y, rf.du_doan(val))
        dong_rf.append({"min_samples_leaf": leaf, "max_features": str(mf), "MAE_RF": ct["MAE"], "MAPE_RF": ct["MAPE"]})
    bang_rf = pd.DataFrame(dong_rf)
    best = bang_rf.sort_values("MAE_RF").iloc[0]
    mf_best = best["max_features"]
    mf_best = float(mf_best) if mf_best not in ("sqrt", "log2") else mf_best
    rf_params = {"n_estimators": 300, "min_samples_leaf": int(best["min_samples_leaf"]), "max_features": mf_best, "random_state": 42}

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    bang_tk.to_csv(RESULTS_DIR / "tuning_cbr_theta_k.csv", index=False)
    bang_w.to_csv(RESULTS_DIR / "tuning_w_max.csv", index=False)
    bang_d.to_csv(RESULTS_DIR / "tuning_delta_min.csv", index=False)
    bang_rf.to_csv(RESULTS_DIR / "tuning_rf.csv", index=False)
    tom_tat = {
        "tap_validation": {"so_sub_train": len(sub), "so_validation": len(val),
                           "phuong_phap": "train_test_split(train, test_size=0,2, random_state=7, stratify=phan_khuc)"},
        "quy_tac_chon": {"k": f"cố định {K_CO_DINH}", "theta": f"θ lớn nhất có MAE CBR ≤ MAE tốt nhất × (1 + {DUNG_SAI_THETA:.0%}), tỷ lệ có kết quả ≥ {PHU_TOI_THIEU:.0%}",
                         "w_max": "MAE hệ lai nhỏ nhất", "delta_min": f"nhỏ nhất đạt tỷ lệ trong khoảng ≥ {MUC_TIEU_PHU_KHOANG:.0%}",
                         "rf": "MAE validation nhỏ nhất"},
        "da_chon": {"k": K_CO_DINH, "theta": theta_chon, "w_max": w_chon, "delta_min": d_chon, "rf": rf_params},
        "mae_luat_validation": chi_so(y, p_luat)["MAE"],
    }
    with open(RESULTS_DIR / "tuning_summary.json", "w", encoding="utf-8") as f:
        json.dump(tom_tat, f, ensure_ascii=False, indent=2)
    with open(RESULTS_DIR / "rf_params.json", "w", encoding="utf-8") as f:
        json.dump(rf_params, f, ensure_ascii=False, indent=2)
    print(bang_tk[bang_tk["k"] == K_CO_DINH].to_string(index=False))
    print(bang_tk[bang_tk["theta"] == theta_chon].to_string(index=False))
    print(bang_w.to_string(index=False))
    print(bang_d.to_string(index=False))
    print(bang_rf.to_string(index=False))
    print("ĐÃ CHỌN:", json.dumps(tom_tat["da_chon"], ensure_ascii=False))

    if args.apply:
        p = KB_DIR / "config.json"
        cfg = json.loads(p.read_text(encoding="utf-8"))
        cfg["cbr"]["k_toi_da"] = K_CO_DINH
        cfg["cbr"]["nguong_tuong_tu"] = theta_chon
        cfg["ket_hop"]["w_cbr_toi_da"] = w_chon
        cfg["khoang_gia"]["delta_min"] = d_chon
        p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Đã ghi tham số vào kb/config.json")


if __name__ == "__main__":
    main()
