"""Defines the TraditionalTunnel class"""

# Third-party libraries
from attrs import define

# Project libraries
from src.base_ssh import BaseSsh
from src.ssh_process import SshProcess


@define
class TraditionalTunnel(BaseSsh):

    def __str__(self):
        return (
            "[magenta]"
            "TUNNEL: "
            f'{self.ssh_process.username.split("\\")[-1].lower()}@'
            f"{self.ssh_process.arguments.destination_host}:"
            f"{self.ssh_process.arguments.destination_port} "
            f"({self.ssh_process.pid})"
            "[/magenta]"
        )

    @staticmethod
    def is_process_this(process: SshProcess) -> bool:
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

        return forward_argument and not socket_argument

    @classmethod
    def from_process(cls, process: SshProcess):
        return cls(
            ssh_process=process,
            forwards=BaseSsh.build_forward_list(process),
            ssh_type="traditional_tunnel",
            socket_file=None,
        )
