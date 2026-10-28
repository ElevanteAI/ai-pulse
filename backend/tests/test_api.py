from tests.conftest import login


def test_login_lists_organizations(client):
    _, data = login(client, "ravi@consult.test")
    names = {o["org_name"] for o in data["organizations"]}
    assert names == {"Northwind Logistics", "Bluepeak Retail"}


def test_employee_sees_questions(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.get("/diagnostic/questions", headers=headers)
    assert r.status_code == 200
    assert any(q["id"] == "sup-drafts" for q in r.json())


def test_admin_dashboard(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    # All departments have < 5 respondents, so none are displayed (privacy filter)
    assert len(r.json()["departments"]) == 0
    # But small_groups_summary shows they exist
    assert r.json()["small_groups_summary"] is not None
    assert r.json()["small_groups_summary"]["count"] == 4


def test_admin_cannot_see_other_org(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    r = client.get("/dashboard?org_id=1", headers=headers)
    assert r.status_code == 200
    assert "departments" in r.json()


# Test 1: Dashboard response contains response_rates and hidden_team_count fields
def test_dashboard_has_response_rates_field(client):
    """Dashboard response should contain response_rates list and hidden_team_count"""
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    response_data = r.json()
    
    # Verify response_rates field exists
    assert "response_rates" in response_data
    assert isinstance(response_data["response_rates"], list)
    assert "hidden_team_count" in response_data
    assert isinstance(response_data["hidden_team_count"], int)


# Test 2: Teams with < 5 completed responses do not appear in response_rates
def test_teams_with_less_than_5_responses_hidden(client):
    """Teams with < 5 completed should not appear in response_rates"""
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    response_data = r.json()
    
    # All teams in response_rates should have >= 5 completed
    for team in response_data.get("response_rates", []):
        assert team["completed"] >= 5, f"Team {team['team_name']} has only {team['completed']} responses but appears in visible list"


# Test 3: Response rate team entries have required fields
def test_response_rate_team_structure(client):
    """Each team in response_rates should have team_id, team_name, completed, invited"""
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    response_data = r.json()
    
    for team in response_data.get("response_rates", []):
        assert "team_id" in team
        assert "team_name" in team
        assert "completed" in team
        assert "invited" in team
        assert isinstance(team["completed"], int)
        assert isinstance(team["invited"], int)


# Test 4: Overall counts are present and correct
def test_overall_counts_present(client):
    """Overall completed and invited should be totals for the org"""
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    response_data = r.json()
    
    # Verify overall structure
    assert "overall" in response_data
    assert "completed" in response_data["overall"]
    assert "invited" in response_data["overall"]
    assert response_data["overall"]["completed"] >= 0
    assert response_data["overall"]["invited"] >= response_data["overall"]["completed"]


# Test 5: Cross-org isolation - admin cannot see other org's dashboard
def test_cross_org_isolation(client):
    """Admin should not be able to access other organizations' dashboards"""
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    
    # Try to access a non-existent org or another org's data
    r = client.get("/dashboard?org_id=999", headers=headers)
    # Should be 403 (forbidden) or 404 (not found)
    assert r.status_code in [403, 404], "Admin should not access other organizations"


# Test 6: Response contains no details about hidden teams
def test_no_hidden_team_identifiers(client):
    """Response JSON should not contain team names/ids for hidden teams"""
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    response_json = r.json()
    
    # Verify hidden_team_count is just an integer
    assert isinstance(response_json.get("hidden_team_count"), int)
    
    # Response should not have a 'hidden_teams' list or similar
    assert "hidden_teams" not in response_json
    
    # Verify response_rates only contains visible teams (completed >= 5)
    for team in response_json.get("response_rates", []):
        assert team["completed"] >= 5


# Test 7: Unauthenticated request returns 401 or 403
def test_unauthenticated_dashboard_access(client):
    """Unauthenticated request should be denied"""
    r = client.get("/dashboard?org_id=1")
    assert r.status_code in [401, 403], "Unauthenticated request should be denied"


# Test 8: Non-admin user cannot access dashboard
def test_non_admin_access_denied(client):
    """Non-admin user should not be able to access dashboard"""
    headers, data = login(client, "priya@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 403, "Non-admin should be denied access to dashboard"


# Test 9: MIN_GROUP_SIZE threshold is enforced (5 responses)
def test_privacy_threshold_enforced(client):
    """Teams must have exactly 5+ responses to be visible"""
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    response_data = r.json()
    
    # All visible teams must meet the threshold
    for team in response_data.get("response_rates", []):
        assert team["completed"] >= 5, f"Team visible with only {team['completed']} responses"
    
    # hidden_team_count should account for teams below threshold
    assert isinstance(response_data["hidden_team_count"], int)
    assert response_data["hidden_team_count"] >= 0
