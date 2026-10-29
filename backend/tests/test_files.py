from app.core.files import sanitize_filename


def test_strips_directory_traversal() -> None:
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\Windows\\system32\\evil.exe") == "evil.exe"


def test_removes_unsafe_characters() -> None:
    assert sanitize_filename('a<b>c:d"e/f\\g|h?i*j.mp4') == "g_h_i_j.mp4"
    assert sanitize_filename('a<b>c:d"e|h?i*j.mp4') == "a_b_c_d_e_h_i_j.mp4"


def test_keeps_unicode_letters() -> None:
    assert sanitize_filename("Café — 日本語 [abc].mp3") == "Café _ 日本語 [abc].mp3"


def test_handles_empty_and_reserved_names() -> None:
    assert sanitize_filename("...") == "download"
    assert sanitize_filename("CON.txt") == "_CON.txt"


def test_truncates_long_names() -> None:
    result = sanitize_filename("a" * 400 + ".mp4")
    assert len(result.encode("utf-8")) < 200
    assert result.endswith(".mp4")
