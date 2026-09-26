from app.database.models import Interview
from app.interview.probe import MAX_PROBE_DEPTH, apply_probe, normalise_topic


def _interview(**kw):
    iv = Interview(current_topic="redis", probe_depth=0, consecutive_wrongs=0, covered_topics=[])
    for k, v in kw.items():
        setattr(iv, k, v)
    return iv


def _result(action, *, topic="redis", correct=True):
    return {"probe_action": action, "topic": topic, "evaluation": {"correct": correct}}


def test_deepen_bumps_depth_same_topic():
    iv = _interview(probe_depth=1)
    apply_probe(iv, _result("deepen"))
    assert iv.probe_depth == 2
    assert iv.current_topic == "redis"
    assert iv.covered_topics == []


def test_switch_retires_topic_and_resets_depth():
    iv = _interview(probe_depth=3)
    apply_probe(iv, _result("switch", topic="mysql"))
    assert iv.covered_topics == ["redis"]
    assert iv.current_topic == "mysql"
    assert iv.probe_depth == 0


def test_first_wrong_stays_then_second_switches():
    iv = _interview(probe_depth=2)
    apply_probe(iv, _result("correct_and_stay", correct=False))
    assert iv.current_topic == "redis"        # first miss: stays on topic
    assert iv.consecutive_wrongs == 1
    apply_probe(iv, _result("correct_and_stay", topic="mysql", correct=False))
    assert iv.covered_topics == ["redis"]     # second miss: forced switch
    assert iv.probe_depth == 0


def test_depth_is_capped():
    iv = _interview(probe_depth=MAX_PROBE_DEPTH)
    apply_probe(iv, _result("deepen"))
    assert iv.probe_depth == MAX_PROBE_DEPTH


def test_normalise_topic_strips_and_lowercases():
    assert normalise_topic("  Redis  ") == "redis"
    assert normalise_topic("") == "general"