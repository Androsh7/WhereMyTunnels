"""Defines the BaseSsh class"""

# Standard libraries
import psutil
from typing import Literal, Optional

# Third-party libraries
from attrs import define, field, validators
from src.ssh_process import SshProcess

# Project libraries
from src.default import SSH_TYPES
from src.base_forward import Forward


@define
class BaseSsh:
    ssh_type: Literal[SSH_TYPES] = field(
        validator=validators.and_(validators.instance_of(str), validators.in_(SSH_TYPES))
    )
    ssh_process: SshProcess = field(validator=validators.instance_of(SshProcess))
    socket_file: Optional[str] = field(validator=validators.optional(str))
    forwards: list[Forward] = field(
        validator=validators.optional(
            validators.deep_iterable(
                member_validator=validators.instance_of(Forward), iterable_validator=validators.instance_of(list)
            )
        )
    )
    attached_connection: Optional[psutil._common.sconn] = field(
        default=None, validator=validators.optional(psutil._common.sconn)
    )

    @classmethod
    def is_process_this(process: SshProcess):
        pass

    @classmethod
    def from_process(cls, process: SshProcess):
        pass

    @staticmethod
    def build_forward_list(process: SshProcess) -> list[Forward]:
        out_list = []
        for argument, value in process.arguments.value_arguments:

            # Create forward object
            if argument not in ("L", "R"):
                continue
            forward = Forward.from_argument(forward_type=f'{"local" if argument == "L" else "reverse"}', argument=value)

            # Attach connections
            for index, connection in enumerate(process.connections):
                if (
                    forward.forward_type == "local"
                    and connection.status == "LISTEN"
                    and connection.laddr.port == forward.source_port
                ):
                    forward.attached_connections.append(connection)
                    del process.connections[index]
                elif (
                    forward.forward_type == "reverse"
                    and connection.status == "LISTEN"
                    and connection.raddr.port == forward.source_port
                ):
                    forward.attached_connections.append(connection)
                    del process.connections[index]

            # Mark forwards with missing connections as malformed
            if len(forward.attached_connections) == 0:
                forward.malformed_message = "NO ATTACHED CONNECTION"
            out_list.append(forward)

        return out_list

    @staticmethod
    def get_socket_file(process: SshProcess) -> str:
        for argument, value in process.arguments.value_arguments:
            if argument != "S":
                continue
            return value
        raise KeyError("No socket file specific in argument list")
