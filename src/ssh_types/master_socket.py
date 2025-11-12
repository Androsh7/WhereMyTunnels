"""Defines the MasterSocket class"""

# Third-party libraries
from attrs import define, field, validators

# Project libraries
from src.ssh_types.base_ssh import BaseSsh
from src.ssh_types.ssh_process import SshProcess
from src.ssh_types.base_forward import Forward

@define
class MasterSocket(BaseSsh):
    forwards: list[Forward] = field(validator=validators.instance_of(list))

    def __str__(self):
        return f'{self.socket_file} -> {self.ssh_process.username.split("\\")[-1]}@{self.ssh_process.arguments.destination_host}:{self.ssh_process.arguments.destination_port} ({self.ssh_process.pid})'

    @staticmethod
    def is_process_this(process: SshProcess) -> bool:
        """Determines if the given process is a master socket
        by checking for the "M" flag

        Args:
            process: The SSH process to look at

        Returns:
            True if the process is a master socket, otherwise False
        """
        return "M" in process.arguments.flags

    @classmethod
    def from_process(cls, process: SshProcess):
        return cls(
            ssh_process=process,
            socket_file=BaseSsh.from_process(process),
            forwards=BaseSsh.get_forward_list(process),
            ssh_type="master_socket",
        )
