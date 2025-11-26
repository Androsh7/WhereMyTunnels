"""Defines the MasterSocket class"""

# Third-party libraries
from attrs import define

# Project libraries
from src.base_ssh import BaseSsh
from src.ssh_process import SshProcess


@define
class MasterSocket(BaseSsh):

    def __str__(self):
        return (
            "[cyan]"
            "CONTROL "
            f"{self.socket_file} -> "
            f'{self.ssh_process.username.split("\\")[-1].lower()}@'
            f"{self.ssh_process.arguments.destination_host}:"
            f"{self.ssh_process.arguments.destination_port} "
            f"({self.ssh_process.pid})"
            "[/cyan]"
        )

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
            forwards=BaseSsh.build_forward_list(process),
            ssh_type="master_socket",
        )
