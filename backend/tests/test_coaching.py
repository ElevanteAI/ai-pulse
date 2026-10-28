from tests.conftest import login


def test_report_turns_known_risk_into_safe_use_coaching(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    report = client.get("/reports/me", headers=headers).json()
    assert report["coaching"] == [{
        "risk": "customer_data_shared",
        "title": "Keep customer information out of public AI tools",
        "action": "Replace names, contact details, account numbers, and complaint text with placeholders before prompting.",
    }]
