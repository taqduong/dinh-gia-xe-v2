"""Kiểm tra cơ sở tri thức: nạp từ file, kế thừa khung, phát hiện lỗi cấu hình."""
import copy

from carval.kb import KnowledgeBase, doc_json
from carval.kb_validation import kiem_tra_co_so_tri_thuc
from carval.paths import KB_DIR


def test_nap_tri_thuc_tu_file(kb):
    tk = kb.thong_ke()
    assert tk["so_luat"] == 25
    assert tk["so_phien_ban"] == 35
    assert len({l.id for l in kb.luat}) == 25


def test_ke_thua_thuoc_tinh_khung(kb):
    pb = kb.phien_ban["toyota-vios-15g-cvt"]
    assert pb.phan_khuc == "B"            # kế thừa từ dòng Vios
    assert pb.nhom_giu_gia == "cao"       # kế thừa từ hãng Toyota
    assert pb.gia_moi == 545


def test_co_so_tri_thuc_hien_tai_nhat_quan(kb, svc):
    kq = kiem_tra_co_so_tri_thuc(kb, kho_tinh_huong=svc.kho.df)
    assert kq["hop_le"], kq["van_de"]


def test_phat_hien_loi_trong_tep_minh_hoa(kb):
    kq = kiem_tra_co_so_tri_thuc(kb, rules_raw=doc_json(KB_DIR / "examples" / "rules_invalid_demo.json"))
    assert not kq["hop_le"]
    loai = {(v["loai"], v["doi_tuong"]) for v in kq["van_de"]}
    assert ("Mã trùng", "Luật R06") in loai
    assert ("Kiểu dữ liệu", "Luật R14") in loai
    thong_diep = " ".join(v["thong_diep"] for v in kq["van_de"])
    assert "tinh_ty_le_km_v2" in thong_diep          # hàm suy diễn không tồn tại
    assert "so_chu_xe" in thong_diep                 # dữ kiện chưa khai báo
    assert "Lexus" in thong_diep and "SUV-E" in thong_diep  # tham chiếu khung thiếu
    assert any(v["loai"] == "Chồng lấn/bao phủ" and "R05" in v["doi_tuong"] for v in kq["van_de"])


def test_phat_hien_khung_va_kich_ban_loi(kb):
    frames = copy.deepcopy(kb.frames)
    frames["hang_xe"][0]["dong_xe"][0]["phien_ban"][0]["gia_moi"] = -5
    frames["hang_xe"][0]["dong_xe"][0]["phan_khuc"] = "XYZ"
    scen = copy.deepcopy(kb.scenarios_raw)
    scen["kich_ban"][0]["dau_vao"]["phien_ban"] = "khong-ton-tai"
    kb2 = KnowledgeBase.tu_du_lieu(frames, kb.rules_raw, kb.config, scen)
    kq = kiem_tra_co_so_tri_thuc(kb2)
    doi_tuong = {v["doi_tuong"] for v in kq["van_de"]}
    assert "Khung toyota-vios-15e-mt" in doi_tuong
    assert "Khung dòng toyota-vios" in doi_tuong
    assert "Kịch bản TC01" in doi_tuong


def test_nhom_tuoi_bao_phu_va_loai_tru(kb):
    from carval.inference import ForwardChainingEngine
    luat_tuoi = [l for l in kb.luat if l.nhom == "TUOI_XE"]
    for tuoi in range(0, 41):
        n = sum(all(ForwardChainingEngine.thoa(dk, {"tuoi_xe": tuoi}) for dk in l.dieu_kien) for l in luat_tuoi)
        assert n == 1, f"tuổi {tuoi} khớp {n} luật khấu hao"
