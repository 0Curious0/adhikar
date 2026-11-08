from adhikar.dialogue.profile import SQLiteProfileStore, UserProfile, merge_facts, pin_scheme


def _store(tmp_path):
    return SQLiteProfileStore(tmp_path / "profiles.db")


def test_get_returns_empty_profile_for_unknown_user(tmp_path):
    store = _store(tmp_path)

    profile = store.get("user-1")

    assert profile == UserProfile(user_id="user-1")


def test_save_then_get_roundtrips_facts_and_pin(tmp_path):
    store = _store(tmp_path)
    profile = UserProfile(user_id="user-1", facts={"age_years": 45}, pinned_scheme_id="pm_kisan")

    store.save(profile)

    assert store.get("user-1") == profile


def test_save_overwrites_existing_profile_for_same_user(tmp_path):
    store = _store(tmp_path)
    store.save(UserProfile(user_id="user-1", facts={"age_years": 45}))
    store.save(UserProfile(user_id="user-1", facts={"age_years": 46}, pinned_scheme_id="pds"))

    profile = store.get("user-1")

    assert profile.facts == {"age_years": 46}
    assert profile.pinned_scheme_id == "pds"


def test_profiles_persist_across_store_instances(tmp_path):
    db_path = tmp_path / "profiles.db"
    SQLiteProfileStore(db_path).save(UserProfile(user_id="user-1", facts={"state": "Rajasthan"}))

    reopened = SQLiteProfileStore(db_path)

    assert reopened.get("user-1").facts == {"state": "Rajasthan"}


def test_merge_facts_combines_without_mutating_original():
    profile = UserProfile(user_id="user-1", facts={"age_years": 45})

    updated = merge_facts(profile, {"state": "Rajasthan"})

    assert updated.facts == {"age_years": 45, "state": "Rajasthan"}
    assert profile.facts == {"age_years": 45}


def test_merge_facts_overwrites_existing_keys():
    profile = UserProfile(user_id="user-1", facts={"age_years": 45})

    updated = merge_facts(profile, {"age_years": 46})

    assert updated.facts == {"age_years": 46}


def test_pin_scheme_sets_pinned_scheme_id_without_mutating_original():
    profile = UserProfile(user_id="user-1")

    updated = pin_scheme(profile, "pm_kisan")

    assert updated.pinned_scheme_id == "pm_kisan"
    assert profile.pinned_scheme_id is None
