# shortcut: stub until #22 — passes the batch through unchanged; replace with the real step.
def handler(event, context):
    if event.get("fail_at") == "verify":
        raise RuntimeError("forced failure for testing")
    return event
