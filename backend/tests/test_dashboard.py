"""Dashboard numbers, checked against values worked out by hand.

Northwind Sales in the seed (option index + 1 = points):
  Vikram  4,4,4,4,4,4 + open 4       -> 4.0
  Neha    3,4,2,2,3     + open 3       -> 17/6 = 2.833
  Rohan   4,3,3,3,4,4 + open 2       -> 23/7 = 3.286
  Ananya  5,5,5,5,5,5 + open 5       -> 5.0
  Karan   1,1,2,2,1     + open 1       -> 8/6  = 1.333
  Sales = mean of people = 16.452 / 5 = 3.29 (Practitioner). Farah hasn't responded.
"""
from types import SimpleNamespace as NS

from app.services import aggregation as agg
from app.utils import maturity_level
from tests.conftest import login


def dashboard(client, email="asha@northwind.test", org="Northwind Logistics"):
    headers, _ = login(client, email, org)
    return client.get("/dashboard", headers=headers).json()


def group(data, name):
    return next(g for g in data["groups"] if g["department"] == name)


def person(*scores, flags=(), status=None):
    rows = [NS(score=s, flags=list(flags), ai_status=status) for s in scores]
    return (NS(), rows)


def test_sales_average_matches_hand_calculation(client):
    sales = group(dashboard(client), "Sales")
    assert sales["employees"] == 6
    assert sales["respondents"] == 5
    assert sales["average_score"] == 3.29
    assert sales["level"] == "Practitioner"


def test_average_is_per_person_not_per_answer():
    # One person with 8 answers of 5, one with a single 1. Per person: (5 + 1) / 2 = 3.0.
    # The original "all answers / headcount" logic would give 41 / 2 = 20.5.
    assert agg.summarise([person(*[5] * 8), person(1)])["average_score"] == 3.0


def test_people_with_no_scores_do_not_drag_the_average_down():
    # A respondent whose only answer couldn't be scored is counted, but has no average
    s = agg.summarise([person(4), person(None, status="needs_review")])
    assert s["respondents"] == 2 and s["average_score"] == 4.0


def test_no_answers_is_not_assessed_not_beginner():
    assert agg.summarise([]) == {"respondents": 0, "average_score": None, "level": "Not assessed"}


def test_report_and_dashboard_use_the_same_scale(client):
    """Original: 3.6 was 'Practitioner' on the report and 'Leader' on the dashboard."""
    for avg, expected in [(1.9, "Beginner"), (2.0, "Exploring"), (3.6, "Practitioner"), (4.0, "Leader")]:
        assert maturity_level(avg) == expected
    headers, _ = login(client, "ananya@northwind.test", "Northwind Logistics")
    assert client.get("/reports/me", headers=headers).json()["level"] == maturity_level(5.0)


def test_risks_count_people_not_answers():
    people = [person(3, 3, 3, flags=["customer_data_shared"]), person(4, flags=["customer_data_shared"])]
    assert agg.risk_counts(people) == [{"risk": "customer_data_shared", "people": 2}]


def test_ai_scoring_health_counts_needs_review():
    people = [person(4, status="scored"), person(None, status="needs_review"), person(3)]
    assert agg.ai_scoring_health(people) == {"open_answers": 2, "needs_review": 1}
