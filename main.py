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

# Default Flags
SHOW_CONNECTIONS = False
SHOW_ARGUMENTS = True

# Color Constants
TITLE_COLOR = "#39ff14"
TITLE_COLOR_BOLD = f"bold {TITLE_COLOR}"
LINK_COLOR = "underline blue"


def return_with_color(text: str, color: str) -> str:
    """Returns text wrapped in color tags

    Args:
        text: The text to wrap
        color: The color to use

    Returns:
        The text wrapped in color tags
    """
    return f"[{color}]{text}[/{color}]"


def get_ssh_raw_processes() -> list[psutil.Process]:
    """Gets a list of all raw SSH processes"""
    for process in psutil.process_iter(["pid", "username", "name", "cmdline"]):
        try:
            name = (process.info.get("name") or "").strip()
            if SSH_NAME_RE.search(name):
                yield SshProcess.from_process(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def get_ssh_processes() -> list[BaseSsh]:
    """Gets a list of all SSH processes"""
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
    """Creates branches for connections

    Args:
        parent_branch: The parent branch to add the connections to
        connection_list: The list of connections to create branches for
    """
    out_list = []
    for connection in connection_list:
        if connection is None:
            continue
        elif connection.status == "LISTEN":
            out_list.append(
                return_with_color(text=f"LISTEN {connection.laddr.ip}:{connection.laddr.port}", color="blue")
            )
        elif connection.status == "ESTABLISHED":
            out_list.append(
                return_with_color(
                    text=(
                        f"ESTABLISHED {connection.laddr.ip}:{connection.laddr.port} -> "
                        f"{connection.raddr.ip}:{connection.raddr.port}"
                    ),
                    color="blue",
                )
            )
        else:
            out_list.append(str(connection))
    out_list.sort()
    for connection_str in out_list:
        parent_branch.add(connection_str)


def build_forward_branches(parent_branch: Tree, forward_list: list[Forward]):
    """Creates branches for forwards

    Args:
        parent_branch: The parent branch to add the forwards to
        forward_list: The list of forwards to create branches for
    """
    for forward in forward_list:
        sub_branch = parent_branch.add(str(forward))
        if SHOW_CONNECTIONS:
            build_connection_branches(parent_branch=sub_branch, connection_list=forward.attached_connections)


def build_process_branch(parent_tree: Tree, ssh_process: BaseSsh) -> Tree:
    """Creates a branch for a specific ssh process

    Args:
        parent_tree: The parent tree to add the branch to
        ssh_process: The ssh process to create the branch for

    Returns:
        returns the created branch
    """
    branch_title = str(ssh_process)
    if SHOW_ARGUMENTS:
        branch_title += return_with_color(text=f" {ssh_process.ssh_process.raw_arguments}", color="white")
    branch = parent_tree.add(branch_title)
    if SHOW_CONNECTIONS:
        build_connection_branches(parent_branch=branch, connection_list=ssh_process.ssh_process.connections)
    build_forward_branches(parent_branch=branch, forward_list=ssh_process.forwards)
    return branch


def master_socket_ssh_tree(ssh_process_list: list[BaseSsh]) -> Tree:
    """Creates a tree of master sockets and socket forwards

    Args:
        ssh_process_list: List of SSH processes

    Returns:
        Tree of master sockets and socket forwards
    """
    tree = Tree("")

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

    tree.label = return_with_color(text=f"Master Sockets ({len(tree.children)})", color="bold cyan")
    return tree


def traditional_tunnel_ssh_tree(ssh_process_list: list[BaseSsh]) -> Tree:
    """Creates a tree of traditional tunnels

    Args:
        ssh_process_list: List of SSH processes

    Returns:
        Tree of traditional tunnels
    """

    tree = Tree("")
    for ssh_process in ssh_process_list:
        if ssh_process.ssh_type != "traditional_tunnel":
            continue
        build_process_branch(parent_tree=tree, ssh_process=ssh_process)
    tree.label = return_with_color(text=f"Traditional Tunnels ({len(tree.children)})", color="magenta")
    return tree


def traditional_session_ssh_tree(ssh_process_list: list[BaseSsh]) -> Tree:
    """Creates a tree of traditional sessions

    Args:
        ssh_process_list: List of SSH processes

    Returns:
        Tree of traditional sessions
    """
    tree = Tree("")
    for ssh_process in ssh_process_list:
        if ssh_process.ssh_type != "traditional_session":
            continue
        build_process_branch(parent_tree=tree, ssh_process=ssh_process)
    tree.label = return_with_color(text=f"Traditional Sessions ({len(tree.children)})", color="bold yellow")
    return tree


def create_trees() -> Group:
    """Returns a group of all trees"""
    ssh_process_list = get_ssh_processes()
    return Group(
        master_socket_ssh_tree(ssh_process_list),
        traditional_tunnel_ssh_tree(ssh_process_list),
        traditional_session_ssh_tree(ssh_process_list),
    )


def render_tree(interval: float = 2.0):
    """Continuously refresh the tree output every `interval` seconds."""
    with Live(create_trees(), refresh_per_second=interval, console=console) as live:
        while True:
            new_group = create_trees()
            live.update(new_group)
            time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="WhereMyTunnels", description="Tool for viewing current SSH connections", usage="wheremytunnels [options]"
    )
    parser.add_argument("--version", "-v", action="version", version=f"WhereMyTunnels v{VERSION}")
    parser.add_argument("--about", "-a", action="store_true", help="Show information about WhereMyTunnels")
    parser.add_argument("--interval", "-i", type=int, default=2, help="Refresh interval in seconds (default: 2)")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument(
        "--show-connections",
        action="store_true",
        help='Displays attached connections I.E: "LISTEN 127.0.0.1:8081", "ESTABLISHED 15.1.2.5:12385 -> 8.5.1.4:80"',
    )
    parser.add_argument(
        "--hide-arguments", action="store_true", help='Hide SSH arguments I.E: "ssh test.com -L 8080:localhost:80"'
    )
    args = parser.parse_args()

    # Set console color mode
    if args.no_color:
        console.no_color = True

    # Show about information
    if args.about:
        console.print(
            return_with_color(text="WhereMyTunnels ", color=TITLE_COLOR_BOLD)
            + return_with_color(text=f"v{VERSION}\n", color=TITLE_COLOR)
            + "A tool for viewing current SSH tunnels and connections.\n"
            "Created by Androsh7\n"
            f"GitHub:  {return_with_color(text="https://github.com/androsh7/WhereMyTunnels", color=LINK_COLOR)}\n"
            f"Website: {return_with_color(text="https://androsh7.com", color=LINK_COLOR)}"
        )
        exit(0)

    # Set global flags
    if args.show_connections:
        SHOW_CONNECTIONS = True
    if args.hide_arguments:
        SHOW_ARGUMENTS = False

    try:
        console.rule(
            f"{return_with_color(text="WhereMyTunnels", color=TITLE_COLOR_BOLD)} {return_with_color(text=f"v{VERSION}", color=TITLE_COLOR)}",
            style=TITLE_COLOR,
            characters="=",
        )
        render_tree(interval=args.interval)
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        raise type(ex)(f"WhereMyTunnels crashed (╯°□°)╯︵ ┻━┻") from ex
