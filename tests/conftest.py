import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from carval.kb import KnowledgeBase  # noqa: E402
from carval.paths import TEST_CSV, TRAIN_CSV  # noqa: E402
from carval.service import DichVuDinhGia  # noqa: E402


@pytest.fixture(scope="session")
def kb():
    return KnowledgeBase.tu_thu_muc()


@pytest.fixture(scope="session")
def svc(kb):
    return DichVuDinhGia(kb=kb, kho_df=pd.read_csv(TRAIN_CSV))


@pytest.fixture(scope="session")
def test_df():
    return pd.read_csv(TEST_CSV)


@pytest.fixture(scope="session")
def kich_ban(kb):
    return {s["id"]: s["dau_vao"] for s in kb.kich_ban}
