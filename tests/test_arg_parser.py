"""Tests the parse_args function"""

# Third-party libraries
import pytest

# Project libraries
from src.ssh_process import SshArguments


CASES = [
    # 1) No flags/args
    (
        ["ssh", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[],
            flags=[],
        ),
        "no_flags_no_args",
    ),
    # 2) Duplicate flags (separate)
    (
        ["ssh", "-v", "-v", "-v", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[],
            flags=["v", "v", "v"],
        ),
        "multiple_duplicate_flags",
    ),
    # 3) Bundled flags
    (
        ["ssh", "-vvv", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[],
            flags=["v", "v", "v"],
        ),
        "bundled_flags",
    ),
    # 4) -L spaced
    (
        ["ssh", "-L", "8080:127.0.0.1:80", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[("L", "8080:127.0.0.1:80")],
            flags=[],
        ),
        "local_forward_spaced",
    ),
    # 5) -L smashed
    (
        ["ssh", "-L8080:localhost:80", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[("L", "8080:localhost:80")],
            flags=[],
        ),
        "local_forward_smashed",
    ),
    # 6) -vvvL...
    (
        ["ssh", "-vvvL123:localhost:22", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[("L", "123:localhost:22")],
            flags=["v", "v", "v"],
        ),
        "mixed_bundled_and_forward",
    ),
    # 7) Multiple -L / -R spaced
    (
        ["ssh", "-L", "8080:127.0.0.1:80", "-R", "0.0.0.0:2222:localhost:22", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[
                ("L", "8080:127.0.0.1:80"),
                ("R", "0.0.0.0:2222:localhost:22"),
            ],
            flags=[],
        ),
        "multiple_forwards_spaced",
    ),
    # 8) -D spaced
    (
        ["ssh", "-D", "1080", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[("D", "1080")],
            flags=[],
        ),
        "dynamic_forward_spaced",
    ),
    # 9) -D smashed
    (
        ["ssh", "-D9050", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[("D", "9050")],
            flags=[],
        ),
        "dynamic_forward_smashed",
    ),
    # 10) -p spaced
    (
        ["ssh", "-p", "2200", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=2200,
            value_arguments=[("p", "2200")],
            flags=[],
        ),
        "port_spaced",
    ),
    # 11) -p smashed
    (
        ["ssh", "-p2200", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=2200,
            value_arguments=[("p", "2200")],
            flags=[],
        ),
        "port_smashed",
    ),
    # 12) Separate flags -N -f -C
    (
        ["ssh", "-N", "-f", "-C", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[],
            flags=["N", "f", "C"],
        ),
        "common_flags_separate",
    ),
    # 13) Bundled -NfC
    (
        ["ssh", "-NfC", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[],
            flags=["N", "f", "C"],
        ),
        "common_flags_bundled",
    ),
    # 14) -o attached
    (
        ["ssh", "-oStrictHostKeyChecking=no", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[("o", "StrictHostKeyChecking=no")],
            flags=[],
        ),
        "opt_o_attached_equals",
    ),
    # 15) -o spaced
    (
        ["ssh", "-o", "UserKnownHostsFile=/dev/null", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[("o", "UserKnownHostsFile=/dev/null")],
            flags=[],
        ),
        "opt_o_spaced",
    ),
    # 16) two -o mixed
    (
        ["ssh", "-o", "LogLevel=DEBUG", "-oStrictHostKeyChecking=no", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[
                ("o", "LogLevel=DEBUG"),
                ("o", "StrictHostKeyChecking=no"),
            ],
            flags=[],
        ),
        "opt_o_multiple_mixed",
    ),
    # 17) IPv6 forward
    (
        ["ssh", "-L", "[::1]:2222:[2001:db8::1]:22", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[("L", "[::1]:2222:[2001:db8::1]:22")],
            flags=[],
        ),
        "ipv6_forward",
    ),
    # 18) -D IPv6 smashed
    (
        ["ssh", "-D[::]:9050", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[("D", "[::]:9050")],
            flags=[],
        ),
        "dynamic_forward_ipv6_smashed",
    ),
    # 19) Identity spaced
    (
        ["ssh", "-i", "~/.ssh/id_rsa", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[("i", "~/.ssh/id_rsa")],
            flags=[],
        ),
        "identity_spaced",
    ),
    # 20) Identity smashed
    (
        ["ssh", "-i~/.ssh/key.pem", "host"],
        SshArguments(
            username=None,
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[("i", "~/.ssh/key.pem")],
            flags=[],
        ),
        "identity_smashed",
    ),
    # 21) Username parsing
    (
        ["ssh", "user@host"],
        SshArguments(
            username="user",
            executable_name="ssh",
            destination_host="host",
            destination_port=22,
            value_arguments=[],
            flags=[],
        ),
        "username_parsing",
    ),
]


@pytest.mark.parametrize("cmd,expected,_id", CASES, ids=[c[2] for c in CASES])
def test_parse_args_cases(cmd, expected, _id):
    assert SshArguments.from_command_list(cmd) == expected
