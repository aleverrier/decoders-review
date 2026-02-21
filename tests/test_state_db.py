from pathlib import Path

from qldpcwatch.state import StateDB


def test_state_db_run_and_version_tracking(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    db = StateDB(db_path)

    run_id = db.start_run("2026-01-01T00:00:00+00:00")
    assert run_id > 0

    db.record_version(
        arxiv_id="2401.01234",
        version="v1",
        updated_date="2026-01-01",
        source_hash="abc",
        extraction_hash="def",
    )
    db.upsert_paper(
        arxiv_id="2401.01234",
        latest_version="v1",
        latest_source_hash="abc",
        title="Example",
        primary_category="quant-ph",
    )

    assert not db.needs_processing(arxiv_id="2401.01234", version="v1", source_hash="abc")
    assert db.needs_processing(arxiv_id="2401.01234", version="v1", source_hash="xyz")

    hit = db.find_version_by_source_hash(arxiv_id="2401.01234", source_hash="abc")
    assert hit is not None
    assert hit.version == "v1"

    db.finish_run(run_id, new_papers=1, updated_papers=0, notes={"ok": True})
    db.set_last_run("2026-01-01T01:00:00+00:00")
    assert db.get_last_run() == "2026-01-01T01:00:00+00:00"

    db.close()
