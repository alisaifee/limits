from __future__ import annotations

import pytest

from limits._storage_scheme import parse_storage_uri
from limits.errors import ConfigurationError


@pytest.mark.parametrize(
    "uri, expected",
    [
        ("schema://", []),
        ("schema://localhost:1234", [("localhost", 1234)]),
        (
            "schema://localhost:1234,localhost:4321",
            [("localhost", 1234), ("localhost", 4321)],
        ),
        ("schema://[::1]:1,[::1]:2", [("::1", 1), ("::1", 2)]),
        ("schema://[::1]:1,localhost:2", [("::1", 1), ("localhost", 2)]),
        ("schema://a:b@[::1]:1,[::1]:2", [("::1", 1), ("::1", 2)]),
        ("schema://a:b@localhost:1234", [("localhost", 1234)]),
        ("schema://localhost:1, localhost:2", [("localhost", 1), ("localhost", 2)]),
    ],
)
def test_valid_hosts(uri, expected):
    assert parse_storage_uri(uri).locations == expected


@pytest.mark.parametrize(
    "uri, message",
    [
        ("schema://localhost", "Missing host or port"),
        ("schema://localhost:notaport", "Unable to parse storage uri"),
        ("schema://localhost:1,", "Missing host or port"),
        ("schema://,localhost:1", "Missing host or port"),
    ],
)
def test_invalid_hosts(uri, message):
    with pytest.raises(ConfigurationError, match=message):
        parse_storage_uri(uri)


@pytest.mark.parametrize(
    "uri, expected_path",
    [
        ("schema+unix:///tmp/test.sock", "/tmp/test.sock"),
        ("schema+unix:///var/run/redis.sock", "/var/run/redis.sock"),
        ("schema+unix:///tmp/a.sock", "/tmp/a.sock"),
    ],
)
def test_uds_paths(uri, expected_path):
    parsed = parse_storage_uri(uri)
    assert parsed.locations == []
    assert parsed.path == expected_path


@pytest.mark.parametrize(
    "uri, username, password",
    [
        ("schema://", None, None),
        ("schema://localhost:1234", None, None),
        (
            "schema://localhost:1234,localhost:4321",
            None,
            None,
        ),
        ("schema://[::1]:1,[::1]:2", None, None),
        ("schema://a:b@[::1]:1,[::1]:2", "a", "b"),
        ("schema://a:b@localhost:1234", "a", "b"),
        ("schema://a@:b@@localhost:1234", "a@", "b@"),
    ],
)
def test_username_password(uri, username, password):
    parsed = parse_storage_uri(uri)
    assert parsed.username == username
    assert parsed.password == password
