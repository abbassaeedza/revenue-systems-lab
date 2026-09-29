"""Shared error handler: catch -> structured payload -> alert dispatch.

Mirrors a 3-node production pattern (errorTrigger -> build-payload -> alert-channel).
Clean-room demo — alert_channel here just appends to a list instead of sending real email.
"""
from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable


@dataclass
class ErrorPayload:
    workflow: str
    error_type: str
    message: str
    occurred_at: str
    traceback: str


AlertChannel = Callable[[ErrorPayload], None]


def default_alert_channel(sink: list) -> AlertChannel:
    """Returns an alert channel that appends to `sink` — stand-in for an email/Slack send."""
    def _channel(payload: ErrorPayload) -> None:
        sink.append(payload)
    return _channel


class ErrorHandler:
    """Wraps a step of a pipeline; on exception, builds a structured payload and alerts,
    then re-raises so the caller decides whether to halt or continue the batch.
    """

    def __init__(self, workflow: str, alert_channel: AlertChannel) -> None:
        self.workflow = workflow
        self.alert_channel = alert_channel

    def __enter__(self) -> "ErrorHandler":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            return False
        payload = ErrorPayload(
            workflow=self.workflow,
            error_type=exc_type.__name__,
            message=str(exc),
            occurred_at=datetime.now(timezone.utc).isoformat(),
            traceback="".join(traceback.format_exception(exc_type, exc, tb)),
        )
        self.alert_channel(payload)
        return False  # don't suppress — caller's own try/except decides batch-continue vs halt


if __name__ == "__main__":
    alerts: list[ErrorPayload] = []
    channel = default_alert_channel(alerts)

    # one bad record in a 3-record batch must alert on the bad one and not stop the other two
    processed = []
    for record in ["ok-1", "BAD_RECORD", "ok-2"]:
        try:
            with ErrorHandler(workflow="demo-batch", alert_channel=channel):
                if record == "BAD_RECORD":
                    raise ValueError(f"could not process {record}")
                processed.append(record)
        except ValueError:
            continue  # batch-continue: this record failed, the rest of the batch still runs

    assert processed == ["ok-1", "ok-2"], "one bad record must not abort the rest of the batch"
    assert len(alerts) == 1
    assert alerts[0].error_type == "ValueError"
    assert alerts[0].workflow == "demo-batch"

    print(f"OK — processed {processed}, alerted on {len(alerts)} error: {alerts[0].message}")
