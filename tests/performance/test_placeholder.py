import pytest

pytestmark = pytest.mark.skip(reason="performance QA layer is a v1 deliverable")


def test_performance_placeholder():
    assert True
