"""Defines the BaseSsh class"""

# Standard libraries
import psutil
from typing import Literal, Optional

# Third-party libraries
from attrs import define, field, validators
from src.ssh_process import SshProcess

# Project libraries
from src.default import FORWARD_ARGUMENT_TO_STRING, SSH_TYPES
from src.base_forward import Forward


@define
class BaseSsh:
    ssh_type: Literal[SSH_TYPES] = field(
        validator=validators.and_(validators.instance_of(str), validators.in_(SSH_TYPES))
    )
    ssh_process: SshProcess = field(validator=validators.instance_of(SshProcess))
    socket_file: Optional[str] = field(validator=validators.optional(str))
    forwards: list[Forward] = field(
        factory=list,
        validator=validators.optional(
            validators.deep_iterable(
                member_validator=validators.instance_of(Forward), iterable_validator=validators.instance_of(list)
            )
        ),
    )
    attached_connections: list[psutil._common.pconn] = field(
        factory=list,
        validator=validators.deep_iterable(
            member_validator=validators.instance_of(psutil._common.pconn),
            iterable_validator=validators.instance_of(list),
        ),
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
            if argument not in ("L", "R", "D"):
                continue
            forward = Forward.from_argument(
                forward_type=FORWARD_ARGUMENT_TO_STRING[argument],
                argument=value,
                ssh_connection_destination=process.arguments.destination_host,
            )

            # Attach connections
            for index, connection in enumerate(process.connections):
                if connection is None:
                    continue
                if (
                    (
                        forward.forward_type in ("local", "dynamic")
                        and connection.status == "LISTEN"
                        and type(connection.laddr) != tuple
                        and connection.laddr.port == forward.source_port
                    )
                    or (connection.status == "ESTABLISHED" and connection.laddr.port == forward.source_port)
                    or (
                        forward.forward_type == "reverse"
                        and connection.status == "LISTEN"
                        and type(connection.raddr) != tuple
                        and connection.raddr.port == forward.source_port
                    )
                ):
                    forward.attached_connections.append(connection)
                    process.connections[index] = None

            # Mark forwards with missing connections as malformed
            if len(forward.attached_connections) == 0:
                if forward.forward_type in ("local", "dynamic"):
                    forward.malformed_message = "NO ATTACHED CONNECTION"
                elif forward.forward_type == "reverse":
                    forward.malformed_message = "REVERSE FORWARD NOT CURRENTLY IN USE"
                    forward.malformed_message_color = "dark_orange"
                else:
                    raise ValueError("Invalid forward type")

            out_list.append(forward)

        return out_list

    @staticmethod
    def get_socket_file(process: SshProcess) -> str:
        for argument, value in process.arguments.value_arguments:
            if argument != "S":
                continue
            return value
        raise KeyError("No socket file specific in argument list")
