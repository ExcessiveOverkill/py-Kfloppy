from kfloppy.storage import MF2Root, sanitize_filename


def test_sanitize_filename_drops_path_components():
    assert sanitize_filename("..\\TEST1.tp") == "TEST1.TP"


def test_write_and_read_roundtrip(tmp_path):
    root = MF2Root(tmp_path)
    session = root.begin_write("test1.tp")
    session.append(b"hello")
    assert session.finish() == 5
    assert root.read_bytes("test1.tp") == b"hello"
