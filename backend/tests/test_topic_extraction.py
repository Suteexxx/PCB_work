"""
Unit tests for app.services.web_agent.topic_extraction -- the gazetteer-based
component/topology detector. Pure regex logic, no model/network deps, so
these run fast and deterministically in CI.
"""

from app.services.web_agent.topic_extraction import extract_known_topics

EXAMPLE_USER_QUERY = """
design a ultra low noise and highly stable current source for 100mA current range
using libbrecht hall design. use ultra precision resistors. include the power supply
for all components and generate all required voltage and polarities. and use zero
drift opamps. the circuit should work from single dc input. include the required
ldos. it should have capability to adjust the current using a potentiometer.
provide me list of components. estimate the current noise.
"""


def test_example_query_detects_all_expected_topics():
    """Regression test: the exact example prompt from the product spec should
    decompose into every relevant electronics topic, with no silent misses."""
    topics = extract_known_topics(EXAMPLE_USER_QUERY)

    expected_topics = [
        "Howland / Libbrecht-Hall current source",
        "Zero-drift / chopper op-amp",
        "Ultra-precision resistor",
        "Low-dropout regulator (LDO)",
        "Current source / current sink design",
        "Negative voltage generation / charge pump",  # triggered by "polarities"
        "Current noise / 1/f noise analysis",
        "Potentiometer-based current/voltage adjustment",
        "Single supply / single rail power design",  # triggered by "single dc input"
    ]
    for expected in expected_topics:
        assert expected in topics, f"Expected '{expected}' in detected topics: {topics}"


def test_ldo_matches_plural_form():
    assert "Low-dropout regulator (LDO)" in extract_known_topics("include the required ldos")


def test_ldo_matches_singular_form():
    assert "Low-dropout regulator (LDO)" in extract_known_topics("add an LDO for the reference")


def test_no_false_positive_on_unrelated_query():
    topics = extract_known_topics("how do I bake a chocolate cake")
    assert topics == []


def test_howland_matches_libbrecht_hall_variant():
    topics = extract_known_topics("use the libbrecht-hall topology for this design")
    assert "Howland / Libbrecht-Hall current source" in topics


def test_zero_drift_matches_chopper_stabilized_variant():
    topics = extract_known_topics("use a chopper-stabilized amplifier")
    assert "Zero-drift / chopper op-amp" in topics
