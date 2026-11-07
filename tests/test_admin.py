from carecircle.admin import POLICIES, policy_for


def test_policy_admits_people_and_only_named_agents():
    assert policy_for(["id-scribe"]) == {
        "rules": [{"users": "*", "agents": []}, {"users": [], "agents": ["id-scribe"]}]
    }


def test_people_only_when_no_agents_named():
    assert policy_for([]) == {"rules": [{"users": "*", "agents": []}]}


def test_meds_cannot_reach_ledger():
    assert "meds" not in POLICIES["ledger"]
    assert set(POLICIES["pillbox"]) == {"meds", "coordinator"}
