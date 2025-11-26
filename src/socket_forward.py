"""Defines the SocketForward class"""

# Third-party libraries
from attrs import define

# Project libraries
from src.base_ssh import BaseSsh
from src.ssh_process import SshProcess


@define
class SocketForward(BaseSsh):

    def __str__(self):
        return (
            "[magenta]"
            f"{self.socket_file} -> "
            f'{self.ssh_process.username.split("\\")[-1].lower()}@'
            f"{self.ssh_process.arguments.destination_host}:"
            f"{self.ssh_process.arguments.destination_port} "
            f"({self.ssh_process.pid})"
            "[/magenta]"
        )

    @staticmethod
    def is_process_this(process: SshProcess) -> bool:
        """Determines if the given process is a socket forward
        by checking for the absence of the "M" flag and looking
        for the "S" and ("L" or "R") arguments

        Args:
            process: The SSH process to look at

        Returns:
            True if the process is a socket forward, otherwise False
        """
        # Check for Master Socket flag
        if "M" in process.arguments.flags:
            return False

        # Check for the socket argument and a forward (Local or Reverse)
        socket_argument = False
        forward_argument = False
        for argument, _ in process.arguments.value_arguments:
            if argument == "S":
                socket_argument = True
            elif argument in ("L", "R"):
                forward_argument = True

        return socket_argument and forward_argument

    @classmethod
    def from_process(cls, process: SshProcess):
        return cls(
            ssh_process=process,
            socket_file=BaseSsh.get_socket_file(process),
            forwards=BaseSsh.build_forward_list(process),
            ssh_type="socket_forward",
        )
