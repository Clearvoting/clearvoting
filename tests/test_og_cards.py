"""og Phase B card builder (plan T10.1). Needs Pillow + fontTools + brotli, which are sync-job-only
dependencies (never requirements.txt), so the whole module skips in CI."""
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("PIL")
pytest.importorskip("fontTools")
pytest.importorskip("brotli")

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "synced"


def _script():
    spec = importlib.util.spec_from_file_location("build_og_cards", ROOT / "scripts" / "build_og_cards.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_one_card_per_member_and_per_state(tmp_path):
    from PIL import Image

    members = json.loads((FIXTURES / "members.json").read_text())["members"]
    counts = _script().build_entity_cards(FIXTURES, tmp_path)

    expected_members = {m["bioguideId"] for m in members}
    expected_states = {m["stateCode"] for m in members}
    assert {p.stem for p in (tmp_path / "member").glob("*.png")} == expected_members
    assert {p.stem for p in (tmp_path / "state").glob("*.png")} == expected_states
    assert counts == {"members": len(expected_members), "states": len(expected_states)}
    with Image.open(tmp_path / "member" / "S000148.png") as card:
        assert card.size == (1200, 630)


def test_stale_cards_are_pruned(tmp_path):
    (tmp_path / "member").mkdir(parents=True)
    (tmp_path / "state").mkdir(parents=True)
    (tmp_path / "member" / "X000000.png").write_bytes(b"old")
    (tmp_path / "state" / "OH.png").write_bytes(b"old")
    _script().build_entity_cards(FIXTURES, tmp_path)
    assert not (tmp_path / "member" / "X000000.png").exists()
    assert not (tmp_path / "state" / "OH.png").exists()


def test_cards_are_byte_stable_between_runs(tmp_path):
    script = _script()
    script.build_entity_cards(FIXTURES, tmp_path / "a")
    script.build_entity_cards(FIXTURES, tmp_path / "b")
    for card in (tmp_path / "a" / "member").glob("*.png"):
        assert card.read_bytes() == (tmp_path / "b" / "member" / card.name).read_bytes()
