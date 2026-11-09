from adhikar.dialogue.activity import SQLiteActivityLogStore


def _store(tmp_path):
    return SQLiteActivityLogStore(tmp_path / "activity.db")


def test_recent_returns_empty_list_for_unknown_user(tmp_path):
    store = _store(tmp_path)

    assert store.recent("user-1") == []


def test_log_then_recent_roundtrips_entry(tmp_path):
    store = _store(tmp_path)

    store.log("user-1", scheme_id="pm_kisan", eligibility_status="eligible")

    entries = store.recent("user-1")
    assert len(entries) == 1
    assert entries[0].scheme_id == "pm_kisan"
    assert entries[0].eligibility_status == "eligible"
    assert entries[0].created_at  # non-empty ISO timestamp


def test_recent_orders_newest_first(tmp_path):
    store = _store(tmp_path)

    store.log("user-1", scheme_id="pm_kisan", eligibility_status="missing_fields")
    store.log("user-1", scheme_id="ignwps", eligibility_status="eligible")

    entries = store.recent("user-1")

    assert [entry.scheme_id for entry in entries] == ["ignwps", "pm_kisan"]


def test_recent_respects_limit(tmp_path):
    store = _store(tmp_path)
    for i in range(5):
        store.log("user-1", scheme_id=f"scheme_{i}", eligibility_status="eligible")

    entries = store.recent("user-1", limit=2)

    assert len(entries) == 2
    assert [entry.scheme_id for entry in entries] == ["scheme_4", "scheme_3"]


def test_recent_only_returns_entries_for_requested_user(tmp_path):
    store = _store(tmp_path)
    store.log("user-1", scheme_id="pm_kisan", eligibility_status="eligible")
    store.log("user-2", scheme_id="ignwps", eligibility_status="eligible")

    entries = store.recent("user-1")

    assert len(entries) == 1
    assert entries[0].scheme_id == "pm_kisan"


def test_entries_persist_across_store_instances(tmp_path):
    db_path = tmp_path / "activity.db"
    SQLiteActivityLogStore(db_path).log("user-1", scheme_id="pm_kisan", eligibility_status="eligible")

    reopened = SQLiteActivityLogStore(db_path)

    assert len(reopened.recent("user-1")) == 1
