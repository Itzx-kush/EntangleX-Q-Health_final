from io import BytesIO

import pytest

from app.redis_bridge import RedisBridgeError, _encode_command, _read_resp, validate_command


def test_encode_command_uses_resp_bulk_strings():
    assert _encode_command(["SET", "greeting", "hello world"]) == (
        b"*3\r\n$3\r\nSET\r\n$8\r\ngreeting\r\n$11\r\nhello world\r\n"
    )


@pytest.mark.parametrize(
    ("wire", "expected"),
    [
        (b"+PONG\r\n", "PONG"),
        (b"$5\r\nhello\r\n", "hello"),
        (b"$-1\r\n", None),
        (b":17\r\n", 17),
        (b"*2\r\n+OK\r\n$3\r\nhey\r\n", ["OK", "hey"]),
    ],
)
def test_read_resp_supported_types(wire, expected):
    assert _read_resp(BytesIO(wire)) == expected


def test_read_resp_server_error_is_safe_exception():
    with pytest.raises(RedisBridgeError, match="unknown command"):
        _read_resp(BytesIO(b"-ERR unknown command\r\n"))


@pytest.mark.parametrize(
    "command",
    [["PING"], ["ECHO", "hello"], ["SET", "key", "value"], ["GET", "key"]],
)
def test_validate_supported_commands(command):
    assert validate_command(command)[0] == command[0]


@pytest.mark.parametrize(
    "command",
    [[], ["FLUSHALL"], ["GET"], ["SET", "key"], ["ECHO", "a", "b"]],
)
def test_validate_rejects_unsupported_or_invalid_commands(command):
    with pytest.raises(RedisBridgeError):
        validate_command(command)


def test_validate_command_is_case_insensitive():
    assert validate_command(["ping"]) == ["PING"]
