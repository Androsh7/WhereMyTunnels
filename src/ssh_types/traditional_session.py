"""Defines the TraditionalSession class"""

# Third-party libraries
from attrs import define, field, validators

# Project libraries
from src.ssh_types.base_ssh import BaseSsh
from src.ssh_types.ssh_process import SshProcess


@define
class TraditionalSession(BaseSsh):

    def __str__(self):
        return f'{self.ssh_process.username.split("\\")[-1]}@{self.ssh_process.arguments.destination_host}:{self.ssh_process.arguments.destination_port} ({self.ssh_process.pid})'

    @staticmethod
    def is_process_this(process: SshProcess) -> bool:
        return True

    @classmethod
    def from_process(cls, process: SshProcess):
        return cls(
            ssh_process=process,
            ssh_type="traditional_session",
            socket_file=None,
        )
