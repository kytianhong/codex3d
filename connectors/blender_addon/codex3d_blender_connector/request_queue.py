from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from .protocol_compat import BridgeRequest, BridgeResponse


@dataclass
class PendingBridgeRequest:
    request: BridgeRequest
    timeout: float
    enqueued_at: float = field(default_factory=time.monotonic)
    event: threading.Event = field(default_factory=threading.Event)
    response: BridgeResponse | None = None

    @property
    def deadline(self) -> float:
        return self.enqueued_at + self.timeout

    def complete(self, response: BridgeResponse) -> None:
        self.response = response
        self.event.set()
