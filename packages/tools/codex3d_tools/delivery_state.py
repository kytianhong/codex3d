from __future__ import annotations

from enum import Enum


class DeliveryState(str, Enum):
    WORKING = "working"
    USER_ACCEPTED = "user_accepted"
    USER_REJECTED = "user_rejected"
    RESTORING = "restoring"
    DELIVERED = "delivered"


class DeliveryStateError(RuntimeError):
    pass


class AcceptedStateGuard:
    def __init__(self) -> None:
        self.state = DeliveryState.WORKING
        self.accepted_fingerprint: str | None = None
        self.transitions: list[dict[str, str | None]] = []

    def accept(self, fingerprint: str, *, reason: str) -> None:
        self._record(DeliveryState.USER_ACCEPTED, reason)
        self.accepted_fingerprint = fingerprint

    def reject(self, *, reason: str) -> None:
        if self.state is not DeliveryState.USER_ACCEPTED:
            raise DeliveryStateError("Only an accepted scene can enter the rejected state.")
        self._record(DeliveryState.USER_REJECTED, reason)

    def begin_restore(self) -> None:
        if self.state is not DeliveryState.USER_REJECTED:
            raise DeliveryStateError("Restore is only valid after the user rejects a revision.")
        self._record(DeliveryState.RESTORING, "restore_requested")

    def finish_restore(self, fingerprint: str) -> None:
        if self.state is not DeliveryState.RESTORING:
            raise DeliveryStateError("No restore is in progress.")
        if not self.accepted_fingerprint or fingerprint != self.accepted_fingerprint:
            raise DeliveryStateError("Restored fingerprint does not match the accepted scene.")
        self._record(DeliveryState.USER_ACCEPTED, "restore_verified")

    def deliver(self) -> None:
        if self.state is not DeliveryState.USER_ACCEPTED:
            raise DeliveryStateError("Final delivery requires a verified accepted scene.")
        self._record(DeliveryState.DELIVERED, "final_artifacts_verified")

    def require_delivery_allowed(self) -> None:
        if self.state is not DeliveryState.USER_ACCEPTED:
            raise DeliveryStateError("Final delivery is blocked until an accepted scene is restored.")

    def _record(self, state: DeliveryState, reason: str) -> None:
        self.transitions.append({"from": self.state.value, "to": state.value, "reason": reason})
        self.state = state
