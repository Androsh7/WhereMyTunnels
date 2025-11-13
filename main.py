"""Main logic for WhereMyTunnels"""

# Standard libraries
import argparse
import re

# Third-party libraries
import psutil
import time
from rich.console import Console, Group
from rich.tree import Tree
from rich.live import Live

# Project libraries
from src.base_ssh import BaseSsh
from src.base_forward import Forward
from src.master_socket import MasterSocket
from src.socket_forward import SocketForward
from src.traditional_tunnel import TraditionalTunnel
from src.traditional_session import TraditionalSession
from src.ssh_process import SshProcess
from src.default import VERSION

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


def build_connection_branches(parent_branch: Tree, connection_list: list[psutil._common.pconn]):
    out_list = []
    for connection in connection_list:
        if connection is None:
            continue
        elif connection.status == "LISTEN":
            out_list.append("[blue]" f"LISTEN {connection.laddr.ip}:{connection.laddr.port}" "[/blue]")
        elif connection.status == "ESTABLISHED":
            out_list.append(
                "[green]"
                f"ESTABLISHED {connection.laddr.ip}:{connection.laddr.port} -> "
                f"{connection.raddr.ip}:{connection.raddr.port}"
                "[/green]"
            )
        else:
            out_list.append(str(connection))
    out_list.sort()
    for connection_str in out_list:
        parent_branch.add(connection_str)


def build_forward_branches(parent_branch: Tree, forward_list: list[Forward]):
    for forward in forward_list:
        sub_branch = parent_branch.add(str(forward))
        build_connection_branches(parent_branch=sub_branch, connection_list=forward.attached_connections)

def build_process_branch(parent_tree: Tree, ssh_process: BaseSsh) -> Tree:
    branch = parent_tree.add(str(ssh_process))
    branch.add(f"[yellow]ARGS: {ssh_process.ssh_process.raw_arguments}[/yellow]")
    build_connection_branches(parent_branch=branch, connection_list=ssh_process.ssh_process.connections)
    build_forward_branches(parent_branch=branch, forward_list=ssh_process.forwards)
    return branch

def master_socket_ssh_tree(debug: bool, ssh_process_list: list[BaseSsh]) -> Tree:
    tree = Tree("[bold cyan]Master Sockets[/bold cyan]")
    for ssh_process in ssh_process_list:
        if ssh_process.ssh_type != "master_socket":
            continue
        # Create a branch for the master socket
        branch = build_process_branch(tree, ssh_process=ssh_process)

        # Create a sub-branch for any attached stream socket
        for ssh_sub_process in ssh_process_list:
            if ssh_sub_process.ssh_type != "socket_forward" or ssh_process.socket_file != ssh_sub_process.socket_file:
                continue
            build_process_branch(parent_tree=branch, ssh_process=ssh_sub_process)
    return tree


def traditional_tunnel_ssh_tree(debug: bool, ssh_process_list: list[BaseSsh]) -> Tree:

    tree = Tree("[bold magenta]Traditional Tunnels[/bold magenta]")
    for ssh_process in ssh_process_list:
        if ssh_process.ssh_type != "traditional_tunnel":
            continue
        build_process_branch(parent_tree=tree, ssh_process=ssh_process)
    return tree


def traditional_session_ssh_tree(debug: bool, ssh_process_list: list[BaseSsh]) -> Tree:
    tree = Tree("[bold yellow]Traditional Sessions[/bold yellow]")
    for ssh_process in ssh_process_list:
        if ssh_process.ssh_type != "traditional_session":
            continue
        build_process_branch(parent_tree=tree, ssh_process=ssh_process)
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
    parser = argparse.ArgumentParser(
        prog="WhereMyTunnels",
        description="Tool for viewing current SSH connections"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"WhereMyTunnels v{VERSION}"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=2,
        help="Refresh interval in seconds (default: 2)"
    )
    args = parser.parse_args()
    try:
        console.rule(f"[bold #39ff14]WhereMyTunnels[/bold #39ff14] [#39ff14]v{VERSION}[/#39ff14]", style="#39ff14", characters="=")
        render_tree(debug=True, interval=args.interval)
    except KeyboardInterrupt:
        pass
