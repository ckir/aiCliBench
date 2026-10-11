from event_emitter import EventEmitter


def test_instantiation():
    ee = EventEmitter()
    assert ee is not None
