"""Defines the BaseSsh class"""

# Standard libraries
from typing import Literal, Optional

# Third-party libraries
from attrs import define, field, validators
from src.ssh_types.ssh_process import SshProcess

# Project libraries
from src.ssh_types.default import SSH_TYPES
from src.ssh_types.base_forward import Forward

@define
class BaseSsh:
    ssh_type: Literal[SSH_TYPES] = field(
        validator=validators.and_(validators.instance_of(str), validators.in_(SSH_TYPES))
    )
    ssh_process: SshProcess = field(validator=validators.instance_of(SshProcess))
    socket_file: Optional[str] = field(validator=validators.optional(str))

    @classmethod
    def is_process_this(process: SshProcess):
        pass

    @classmethod
    def from_process(cls, process: SshProcess):
        pass

    @staticmethod
    def get_forward_list(process: SshProcess) -> list[Forward]:
        out_list = []
        for argument, value in process.arguments.value_arguments:
            if argument == "L":
                out_list.append(Forward.from_argument(forward_type="local", argument=value))
            elif argument == "R":
                out_list.append(Forward.from_argument(forward_type="reverse", argument=value))
        return out_list

    @staticmethod
    def get_socket_file(process: SshProcess) -> str:
        for argument, value in process.arguments.value_arguments:
            if argument != "S":
                continue
            return value
        raise KeyError("No socket file specific in argument list")
