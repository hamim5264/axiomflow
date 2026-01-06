from storage import get_connection
from models import Event

def log_event(event: Event):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO execution_logs(actor_id, action) VALUES (?, ?)",
        (event.actor_id, f"event:{event.event_type}")
    )

    conn.commit()
    conn.close()

    print(
        f"[EVENT] {event.event_type} | "
        f"user={event.actor_id} | msg={event.message}"
    )
