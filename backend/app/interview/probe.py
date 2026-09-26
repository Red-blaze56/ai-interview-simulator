'''
PROBE ACTIONS -> "deepen", "switch", "correct_and_stay", "wrap" 

Stay on the topic  ┬─ go HARDER          → deepen
                   └─ teach + retry same → correct_and_stay
Leave the topic    ─── go WIDER (new)     → switch
Leave the interview ── stop + report      → wrap
'''

MAX_PROBE_DEPTH = 5

_TOPIC_ALIASES : dict[str,str] = {}


def normalise_topic(raw: str, * , fallback: str = "general") -> str:
    t = (raw or "").strip().lower()
    if not t: return fallback
    return _TOPIC_ALIASES.get(t,t)

def apply_probe(interview, result: dict) -> None: 
    """Pure state machine: advance the probe chain from the interviewer's
    decision. Mutates `interview` in place — no DB, no LLM."""
    action = result.get("probe_action", "deepen")
    new_topic = normalise_topic(
        result.get("topic", ""), fallback=interview.current_topic or "general"
    )
    answered_correctly = (result.get("evaluation") or {}).get("correct", True)

    if answered_correctly:
        interview.consecutive_wrongs = 0
    else:
        interview.consecutive_wrongs += 1

    # --- Gaurdrail (switching to next topic)---
    if action == "correct_and_stay":
        if answered_correctly:
            action = "deepen"
        elif interview.consecutive_wrongs >= 2:
            action = "switch"

    changed_topic = new_topic != interview.current_topic

    if action == "correct_and_stay":
        interview.current_topic = new_topic 
    elif action == "switch" or changed_topic:
        if interview.current_topic and interview.current_topic != "general":
            interview.covered_topics = [
                *(interview.covered_topics or []), interview.current_topic
            ] 
        interview.current_topic = new_topic
        interview.probe_depth = 0
    else:
        interview.probe_depth = min(interview.probe_depth + 1, MAX_PROBE_DEPTH)


