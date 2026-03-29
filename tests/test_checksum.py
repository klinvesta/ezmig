from ezmig.checksum import compute_checksum


def test_checksum_is_deterministic():
    data = b"hello world"
    assert compute_checksum(data) == compute_checksum(data)


def test_checksum_changes_on_content_change():
    assert compute_checksum(b"a") != compute_checksum(b"b")
