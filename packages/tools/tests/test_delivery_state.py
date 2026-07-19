import pytest

from codex3d_tools import AcceptedStateGuard, DeliveryState, DeliveryStateError


def test_rejected_state_blocks_delivery_until_exact_restore() -> None:
    guard = AcceptedStateGuard()
    guard.accept("a" * 64, reason="confirmed")
    guard.reject(reason="user_rejected")
    with pytest.raises(DeliveryStateError):
        guard.require_delivery_allowed()
    guard.begin_restore()
    with pytest.raises(DeliveryStateError):
        guard.finish_restore("b" * 64)
    assert guard.state is DeliveryState.RESTORING


def test_verified_restore_allows_delivery() -> None:
    guard = AcceptedStateGuard()
    guard.accept("a" * 64, reason="confirmed")
    guard.reject(reason="user_rejected")
    guard.begin_restore()
    guard.finish_restore("a" * 64)
    guard.require_delivery_allowed()
    guard.deliver()
    assert guard.state is DeliveryState.DELIVERED
