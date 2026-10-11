"""Hidden acceptance tests for EventEmitter."""

from event_emitter import EventEmitter  # ty: ignore[unresolved-import]


def test_exact_and_wildcard_matching():
    ee = EventEmitter()
    calls = []

    ee.on("user.created", lambda e, uid: calls.append(("exact", uid)))
    ee.on("user.*", lambda e, uid: calls.append(("single", uid)))
    ee.on("user.**", lambda e, uid: calls.append(("multi", uid)))

    count = ee.emit("user.created", "u1")
    assert count == 3
    assert len(calls) == 3

    calls.clear()
    count = ee.emit("user.profile.updated", "u2")
    # user.* should NOT match user.profile.updated
    # user.** SHOULD match user.profile.updated
    assert count == 1
    assert calls == [("multi", "u2")]


def test_once_listener_auto_removes():
    ee = EventEmitter()
    hits = []
    ee.once("ping", lambda: hits.append(1))

    assert ee.emit("ping") == 1
    assert ee.emit("ping") == 0
    assert hits == [1]


def test_off_deregistration():
    ee = EventEmitter()
    fn = lambda: None
    ee.on("test", fn)
    assert ee.off("test", fn) is True
    assert ee.off("test", fn) is False
