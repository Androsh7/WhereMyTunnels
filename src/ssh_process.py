"""Defines the SshProcess class"""

# Standard libraries
import psutil
from typing import Literal, Optional

# Third-party libraries
from attrs import define, field, validators

# Project libraries
from src.forward import Forward, build_forward_list
from src.default import SSH_TYPES
from src.ssh_arguments import SshArguments


def get_socket_file(arguments: SshArguments) -> Optional[str]:
    """Parses ssh arguments for a socket file

    Args:
        arguments: The ssh arguments

    Returns:
        Returns the socket file or None if no socket file exists in the arguments
    """
    for argument, value in arguments.value_arguments:
        if argument != "S":
            continue
        return value
    return None


@define
class SshProcess:
    """Stores the SSH process information"""

    ssh_type: Literal[SSH_TYPES] = field(
        validator=validators.and_(validators.instance_of(str), validators.in_(SSH_TYPES))
    )
    username: str = field(validator=validators.instance_of(str))
    arguments: SshArguments = field(validator=validators.instance_of(SshArguments))
    pid: int = field(validator=validators.and_(validators.instance_of(int), validators.ge(1)))
    connections: list[psutil._common.pconn] = field(
        validator=validators.deep_iterable(
            member_validator=validators.instance_of(psutil._common.pconn),
            iterable_validator=validators.instance_of(list),
        )
    )
    socket_file: Optional[str] = field(validator=validators.optional(validator=validators.instance_of(str)))
    forwards: list[Forward] = field(
        factory=list,
        validator=validators.optional(
            validators.deep_iterable(
                member_validator=validators.instance_of(Forward), iterable_validator=validators.instance_of(list)
            )
        ),
    )
    children: list = field(factory=list, validator=validators.instance_of(list))
    malformed_message: Optional[str] = field(default=None, validator=validators.optional(validators.instance_of(str)))
    malformed_message_color: Optional[str] = field(
        default="bold red", validator=validators.optional(validators.instance_of(str))
    )

    @classmethod
    def from_process(cls, process: psutil.Process):
        """Creates an SshProcess object from a psutil process

        Args:
            process: The psutil process
        """
        # Parse raw process arguments
        pid = process.info["pid"]
        connections = process.net_connections()
        arguments = SshArguments.from_command_list(process.info["cmdline"])
        if arguments.username is None:
            username = process.info["username"]
        else:
            username = arguments.username

        # Build forward list
        forwards = build_forward_list(arguments=arguments, connections=connections)

        # Get socket file
        socket_file = get_socket_file(arguments)

        # Determine process type
        if "M" in arguments.flags:
            ssh_type = "master_socket"
        elif socket_file:
            if len(forwards) > 0:
                ssh_type = "socket_forward"
            else:
                ssh_type = "socket_session"
        elif len(forwards) > 0:
            ssh_type = "traditional_tunnel"
        else:
            ssh_type = "traditional_session"

        # Remove Nonetype connections
        trimmed_connection_list = []
        for connection in connections:
            if connection:
                trimmed_connection_list.append(connection)

        return cls(
            ssh_type=ssh_type,
            username=username,
            arguments=arguments,
            pid=pid,
            connections=trimmed_connection_list,
            socket_file=socket_file,
            forwards=forwards,
        )
