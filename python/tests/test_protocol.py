from kfloppy.protocol import CommandEvent, DataEvent, StreamParser


def test_parse_framed_command():
    parser = StreamParser()
    events = parser.feed(b"\x01SLF#TEST1.TP\x04")
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, CommandEvent)
    assert event.command == "SLF"
    assert event.argument == b"TEST1.TP"


def test_parse_raw_data_between_frames():
    parser = StreamParser()
    events = parser.feed(b"abc\x01CLR\x04def")
    assert any(isinstance(event, DataEvent) and event.raw == b"abc" for event in events)
    assert any(isinstance(event, CommandEvent) and event.command == "CLR" for event in events)
    assert any(isinstance(event, DataEvent) and event.raw == b"def" for event in events)
