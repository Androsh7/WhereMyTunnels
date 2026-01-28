"""Main logic for WhereMyTunnels"""

# Standard libraries
import argparse
import re
import sys
import time
from ipaddress import ip_address

# Third-party libraries
import psutil
from rich.console import Console, Group
from rich.live import Live
from rich.text import Text
from rich.tree import Tree

# Project libraries
from where_my_tunnels.default import VERSION
from where_my_tunnels.forward import Forward
from where_my_tunnels.render import render_connection, render_ssh_process, return_with_color
from where_my_tunnels.ssh_process import SshProcess

console = Console()

SSH_NAME_RE = re.compile(r"(?:^|/)(ssh)(?:\.exe)?$", re.IGNORECASE)

# Default Flags
SHOW_CONNECTIONS = False
SHOW_ARGUMENTS = False

# Colors
TITLE_COLOR = "#39ff14"
LINK_COLOR = "underline blue"

# Other constants
DEFAULT_INTERVAL = 2


def get_ssh_processes() -> list[SshProcess]:
    """Gets a list of all raw SSH processes"""
    out_list = []
    for process in psutil.process_iter(["pid", "username", "name", "cmdline"]):
        try:
            name = (process.info.get("name") or "").strip()
            if SSH_NAME_RE.search(name):
                out_list.append(SshProcess.from_process(process))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out_list


def build_connection_branches(parent_branch: Tree, connection_list: list[object]):
    """Creates branches for connections

    Args:
        parent_branch: The parent branch to add the connections to
        connection_list: The list of connections to create branches for
    """
    out_list = []
    for connection in connection_list:
        if connection is None:
            continue
        out_list.append(render_connection(connection))
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
        for child_process in forward.children:
            build_process_branch(child_process, parent_tree=sub_branch)


def build_process_branch(ssh_process: SshProcess, parent_tree: Tree) -> Tree:
    """Creates a branch for a specific ssh process

    Args:
        parent_tree: The parent tree to add the branch to (or None if a tree needs to be created)
        ssh_process: The ssh process to create the branch for

    Returns:
        returns the created branch
    """
    branch_title = render_ssh_process(ssh_process)
    if SHOW_ARGUMENTS:
        branch_title += return_with_color(text=f" {' '.join(ssh_process.arguments.raw_arguments)}", color="white")
    if parent_tree is not None:
        branch = parent_tree.add(branch_title)
    else:
        branch = Tree(branch_title)
    if SHOW_CONNECTIONS:
        build_connection_branches(parent_branch=branch, connection_list=ssh_process.connections)
    for child_process in ssh_process.children:
        build_process_branch(ssh_process=child_process, parent_tree=branch)
    build_forward_branches(parent_branch=branch, forward_list=ssh_process.forwards)
    return branch


def find_duplicate_forwards(forward_list: list[Forward]):
    """Detects duplicate forwards and marks them as malformed

    Args:
        forward_list: List of all forwards
    """
    for forward in forward_list:
        error_message = ""
        for forward_check in forward_list:
            if forward == forward_check:
                continue
            if (
                forward.forward_type == forward_check.forward_type
                and forward.forward_type in ("local", "dynamic")
                and forward.source_port == forward_check.source_port
            ):
                error_message += "DUPLICATE FORWARD DETECTED"
            elif (
                forward.forward_type == forward_check.forward_type
                and forward.forward_type == "reverse"
                and forward.source_port == forward_check.source_port
                and forward.ssh_connection_destination == forward_check.ssh_connection_destination
            ):
                error_message += "DUPLICATE FORWARD DETECTED"
            else:
                continue
            break

        # Add the error message to the malformed message
        if len(error_message) > 1:
            if forward.malformed_message is None:
                forward.malformed_message = error_message
            elif forward.malformed_message.find(error_message) == -1:
                forward.malformed_message += f" - {error_message}"
                forward.malformed_message_color = "bold red"


def assign_socket_children(ssh_process_list: list[SshProcess]):
    """Assigns socket forwards and socket sessions as children to the owning master socket
        or marks them as malformed if no master socket process exists

    Args:
        ssh_process_list: List of SshProcess object
    """
    for socket_ssh_process_index, socket_ssh_process in enumerate(ssh_process_list):
        if socket_ssh_process is None or socket_ssh_process.ssh_type not in ("socket_session", "socket_forward"):
            continue
        for master_socket_ssh_process in ssh_process_list:
            if master_socket_ssh_process is None or master_socket_ssh_process.ssh_type != "master_socket":
                continue

            # Add the socket process as a child to the master socket
            if socket_ssh_process.socket_file == master_socket_ssh_process.socket_file:
                master_socket_ssh_process.children.append(socket_ssh_process)
                ssh_process_list[socket_ssh_process_index] = None
                break

        # Add an error if no parent was found
        if ssh_process_list[socket_ssh_process_index] is not None:
            socket_ssh_process.malformed_message = f"Orphan {socket_ssh_process.ssh_type.replace('_', ' ')}"


def assign_forward_children(ssh_process_list: list[SshProcess], forward_list: list[Forward], max_depth: int = 3):
    """Assigns processes as children of ssh forwards

    Args:
        ssh_process_list: List of SshProcess object
        forward_list: List of Forward objects from the ssh_process_list
        max_depth: The max number of times the parsing will re-run to find more dependencies
    """
    for _ in range(max_depth):
        children_found = 0
        for ssh_process_index, ssh_process in enumerate(ssh_process_list):
            # Ignore socket sessions and socket forwards
            # and any process whose destination port is not "127.0.0.1"
            if (
                ssh_process is None
                or ssh_process.ssh_type in ("socket_session", "socket_forward")
                or ssh_process.arguments.destination_host != ip_address("127.0.0.1")
            ):
                continue

            for forward in forward_list:
                # Ignore any forward that isn't a local forward
                if forward.forward_type != "local":
                    continue

                if forward.source_port == ssh_process.arguments.destination_port:
                    forward.children.append(ssh_process)
                    ssh_process_list[ssh_process_index] = None
                    children_found += 1
                    break

        # Exit early if no children are found
        if children_found == 0:
            break


def create_ssh_tree_group() -> Group:
    """Returns a group of all ssh process trees"""

    # Get all ssh processes
    ssh_process_list = get_ssh_processes()

    # Get a list of all forwards
    forward_list = []
    for ssh_process in ssh_process_list:
        for forward in ssh_process.forwards:
            forward_list.append(forward)

    # Find duplicate forwards
    find_duplicate_forwards(forward_list)

    # Find socket dependencies
    assign_socket_children(ssh_process_list)

    # Find dependencies by forward
    assign_forward_children(ssh_process_list, forward_list, max_depth=3)

    # Create the trees
    tree_list = []
    for ssh_process in ssh_process_list:
        if ssh_process is None:
            continue
        tree_list.append(build_process_branch(parent_tree=None, ssh_process=ssh_process))
    if len(tree_list) == 0:
        tree_list.append(Text(text="No ssh connections detected", style="white"))
    return Group(*tree_list)


def render_tree(interval: float = 2.0):
    """Continuously refresh the tree output every `interval` seconds."""
    with Live(create_ssh_tree_group(), refresh_per_second=interval, console=console) as live:
        while True:
            new_group = create_ssh_tree_group()
            live.update(new_group)
            time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="WhereMyTunnels", description="Tool for viewing SSH connections", usage="wheremytunnels [options]"
    )
    parser.add_argument("--version", "-v", action="version", version=f"WhereMyTunnels v{VERSION}")
    parser.add_argument("--about", "-a", action="store_true", help="Show information about WhereMyTunnels")
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"Refresh interval in seconds (default: {DEFAULT_INTERVAL})",
    )
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument(
        "--show-connections",
        action="store_true",
        help='Displays attached connections I.E: "LISTEN 127.0.0.1:8081", "ESTABLISHED 15.1.2.5:12385 -> 8.5.1.4:80"',
    )
    parser.add_argument(
        "--show-arguments", action="store_true", help='Shows SSH arguments I.E: "ssh test.com -L 8080:localhost:80"'
    )
    args = parser.parse_args()

    # Set console color mode
    if args.no_color:
        console.no_color = True

    # Show about information
    if args.about:
        console.print(
            return_with_color(text="WhereMyTunnels ", color=TITLE_COLOR, bold=True)
            + return_with_color(text=f"v{VERSION}\n", color=TITLE_COLOR)
            + "A tool for viewing SSH tunnels and connections.\n"
            "Created by Androsh7\n"
            f"GitHub:  {return_with_color(text='https://github.com/androsh7/WhereMyTunnels', color=LINK_COLOR)}\n"
            f"Website: {return_with_color(text='https://androsh7.com', color=LINK_COLOR)}"
        )
        sys.exit(0)

    # Set global flags
    if args.show_connections:
        SHOW_CONNECTIONS = True
    if args.show_arguments:
        SHOW_ARGUMENTS = True

    try:
        console.rule(
            f"{return_with_color(text='WhereMyTunnels', color=TITLE_COLOR, bold=True)} {return_with_color(text=f'v{VERSION}', color=TITLE_COLOR)}",
            style=TITLE_COLOR,
            characters="=",
        )
        render_tree(interval=args.interval)
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        raise Exception("WhereMyTunnels crashed (╯°□°)╯︵ ┻━┻") from ex
