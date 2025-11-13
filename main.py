"""Main logic for WhereMyTunnels"""

# Standard libraries
import re
from typing import Union

# Third-party libraries
import psutil
import time
from rich.console import Console, Group
from rich.text import Text
from rich.tree import Tree
from rich.live import Live

# Project libraries
from src.ssh_types.base_ssh import BaseSsh
from src.ssh_types.master_socket import MasterSocket
from src.ssh_types.socket_forward import SocketForward
from src.ssh_types.traditional_tunnel import TraditionalTunnel
from src.ssh_types.traditional_session import TraditionalSession
from src.ssh_types.ssh_process import SshProcess

console = Console()

SSH_NAME_RE = re.compile(r"(?:^|/)(ssh)(?:\.exe)?$", re.IGNORECASE)


def get_ssh_raw_processes() -> list[psutil.Process]:
    for process in psutil.process_iter(["pid", "username", "name", "cmdline"]):
        try:
            name = (process.info.get("name") or "").strip()
            if SSH_NAME_RE.search(name):
                yield SshProcess.from_process(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def get_ssh_processes() -> list[BaseSsh]:
    out_list = []
    for process in get_ssh_raw_processes():
        if MasterSocket.is_process_this(process):
            out_list.append(MasterSocket.from_process(process))
        elif SocketForward.is_process_this(process):
            out_list.append(SocketForward.from_process(process))
        elif TraditionalTunnel.is_process_this(process):
            out_list.append(TraditionalTunnel.from_process(process))
        else:
            out_list.append(TraditionalSession.from_process(process))
    return out_list


def master_socket_ssh_tree(debug: bool, ssh_process_list: list[BaseSsh]) -> Tree:
    tree = Tree("[bold]Master Sockets[/bold]")
    for ssh_process in ssh_process_list:
        if ssh_process.ssh_type != "master_socket":
            continue
        # Create a branch for the master socket
        branch = tree.add(str(ssh_process))
        if debug:
            branch.add(f"[yellow]{ssh_process.ssh_process.raw_arguments}[/yellow]")

        # Create sub-branches for forwards
        for forward in ssh_process.forwards:
            branch.add(str(forward))

        # Create a sub-branch for any attached stream socket
        for ssh_sub_process in ssh_process_list:
            if ssh_sub_process.ssh_type != "socket_forward" or ssh_process.socket_file != ssh_sub_process.socket_file:
                continue
            sub_branch = branch.add(str(ssh_sub_process))

            # Print the raw arguments
            if debug:
                sub_branch.add(f"[yellow]{ssh_sub_process.ssh_process.raw_arguments}[/yellow]")
    return tree


def traditional_tunnel_ssh_tree(debug: bool, ssh_process_list: list[BaseSsh]) -> Tree:

    tree = Tree("[bold]Traditional Tunnels[/bold]")
    for ssh_process in ssh_process_list:
        if ssh_process.ssh_type != "traditional_tunnel":
            continue
        branch = tree.add(str(ssh_process))

        # Print the raw arguments
        if debug:
            branch.add(f"[yellow]{ssh_process.ssh_process.raw_arguments}[/yellow]")

        # Print all forwards
        for forward in ssh_process.forwards:
            branch.add(str(forward))
    return tree


def traditional_session_ssh_tree(debug: bool, ssh_process_list: list[BaseSsh]) -> Tree:
    tree = Tree("[bold]Traditional Sessions[/bold]")
    for ssh_process in ssh_process_list:
        if ssh_process.ssh_type != "traditional_session":
            continue
        branch = tree.add(str(ssh_process))

        # Print the raw arguments
        if debug:
            branch.add(f"[yellow]{ssh_process.ssh_process.raw_arguments}[/yellow]")
    return tree


def create_trees(debug: bool) -> Group:
    ssh_process_list = get_ssh_processes()
    return Group(
        master_socket_ssh_tree(debug, ssh_process_list),
        traditional_tunnel_ssh_tree(debug, ssh_process_list),
        traditional_session_ssh_tree(debug, ssh_process_list),
    )


def render_tree(debug: bool = False, interval: float = 2.0):
    """Continuously refresh the tree output every `interval` seconds."""
    with Live(create_trees(debug), refresh_per_second=4, console=console) as live:
        while True:
            new_group = create_trees(debug)
            live.update(new_group)
            time.sleep(interval)


if __name__ == "__main__":
    try:
        console.rule(Text("WhereMyTunnels v1.0.0", style="bold green"), style="bold green", characters="=")
        render_tree(debug=True)
    except KeyboardInterrupt:
        pass
