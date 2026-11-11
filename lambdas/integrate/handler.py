# shortcut: stub until #20 — passes the batch through unchanged; replace with the real step.
def handler(event, context):
    if event.get("fail_at") == "integrate":
        raise RuntimeError("forced failure for testing")
    return event
