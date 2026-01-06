from models import Event
from rules import evaluate_rules
from logs import log_event


def run_lead_demo():
    """
    Simulates a full lead journey
    """
    actor_id = "demo_user_001"

    events = [
        Event(
            event_type="message_received",
            actor_id=actor_id,
            message="Hi"
        ),
        Event(
            event_type="message_received",
            actor_id=actor_id,
            message="Can you tell me the price?"
        ),
        Event(
            event_type="message_received",
            actor_id=actor_id,
            message="I want a demo"
        )
    ]

    executed_steps = []

    for event in events:
        log_event(event)
        actions = evaluate_rules(event)
        executed_steps.append({
            "event": event.message,
            "actions": actions
        })

    return executed_steps
