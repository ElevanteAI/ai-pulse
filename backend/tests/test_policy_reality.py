"""My feature: policy reality check. Expected counts worked out by hand from the seed profiles.

"Say they follow" = policy option 4 or 5. "Risky" = data option 1-2, or a customer/confidential flag.
  Sales   says: Vikram, Neha, Ananya (3)        gap: Neha (1)            unaware: Karan (1)
  Support says: Arjun, Kavitha, Sunil, Tara (4)  gap: Kavitha, Tara (2)   unaware: Priya (1)
  Other   says: Dev, Sara, Imran (3)             gap: none                unaware: Omar (1)
  Org     says: 10 of 16, gap 3 (30%), unaware 3
"""
from types import SimpleNamespace as NS

from app.services import policy_check as pc
from tests.conftest import login


def rows(policy=None, data=None, flags=()):
    out = []
    if policy is not None:
        out.append(NS(question_id="common-policy", score=policy, answer="x", flags=[]))
    if data is not None:
        out.append(NS(question_id="common-data", score=data, answer="Rarely", flags=[]))
    out.append(NS(question_id="common-open", score=3, answer="x", flags=list(flags)))
    return out


def dashboard(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    return client.get("/dashboard", headers=headers).json()


def report(client, email):
    headers, _ = login(client, email, "Northwind Logistics")
    return client.get("/reports/me", headers=headers).json()["policy_check"]


def test_classification_rules():
    assert pc.classify(rows(policy=4, data=4))[0] == pc.CONSISTENT
    assert pc.classify(rows(policy=4, data=2))[0] == pc.GAP
    assert pc.classify(rows(policy=5, data=5, flags=["customer_data_shared"]))[0] == pc.GAP
    assert pc.classify(rows(policy=3, data=1))[0] == pc.RISKY  # read it, didn't claim to follow it
    assert pc.classify(rows(policy=2, data=5))[0] == pc.UNAWARE
    assert pc.classify(rows(data=5))[0] == pc.UNKNOWN
    # unreviewed_output is a real risk, but not a data-handling one
    assert pc.classify(rows(policy=4, data=4, flags=["unreviewed_output"]))[0] == pc.CONSISTENT


def test_org_headline_matches_hand_count(client):
    org = dashboard(client)["policy_reality"]
    assert (org["respondents"], org["say_they_follow_policy"], org["of_whom_risky_practice"], org["unaware_of_policy"]) == (16, 10, 3, 3)
    assert org["gap_rate"] == 0.3
    assert org["headline"] == ("10 of 16 people say they follow the AI policy, but 3 of them (30%) still show "
                               "risky data handling. 3 are not sure what the policy says.")


def test_per_team_breakdown(client):
    groups = {g["department"]: g["policy_reality"] for g in dashboard(client)["groups"]}
    assert (groups["Sales"]["say_they_follow_policy"], groups["Sales"]["of_whom_risky_practice"]) == (3, 1)
    assert (groups["Support"]["say_they_follow_policy"], groups["Support"]["of_whom_risky_practice"]) == (4, 2)
    assert groups["Other teams"]["of_whom_risky_practice"] == 0
    assert groups["Other teams"]["headline"].endswith("1 is not sure what the policy says.")


def test_leadership_never_sees_who(client):
    data = dashboard(client)
    text = str(data)
    for name in ["Neha", "Kavitha", "Tara", "evidence", "You said"]:
        assert name not in text


def test_tiny_org_has_no_policy_reality(client):
    headers, _ = login(client, "meera@bluepeak.test", "Bluepeak Retail")
    assert client.get("/dashboard", headers=headers).json()["policy_reality"] is None


def test_employee_with_gap_gets_specific_private_evidence(client):
    neha = report(client, "neha@northwind.test")
    assert neha["status"] == "gap"
    assert any('"Rarely"' in e for e in neha["evidence"])
    assert any("customer data" in e for e in neha["evidence"])
    assert "remove names, emails" in neha["message"]


def test_employee_states(client):
    assert report(client, "vikram@northwind.test")["status"] == "consistent"
    assert report(client, "karan@northwind.test")["status"] == "unaware"
    assert report(client, "farah@northwind.test")["status"] == "not_enough_data"  # hasn't taken it
    tara = report(client, "tara@northwind.test")
    assert tara["status"] == "gap" and "confidential data" in tara["evidence"][0]
