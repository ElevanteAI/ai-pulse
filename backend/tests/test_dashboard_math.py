from app.routes.dashboard import average_score, level_for


def test_average_divides_by_number_of_scores():
    assert average_score([4, 4]) == 4.0
    assert average_score([2, 3]) == 2.5


def test_no_scores_is_none_not_zero():
    assert average_score([]) is None


def test_level_for_missing_average():
    assert level_for(None) == "Not assessed"


def test_dashboard_and_report_use_the_same_levels():
    from app.utils import maturity_level
    for avg in (1.7, 2.7, 3.7, 4.2):
        assert level_for(avg) == maturity_level(avg)
