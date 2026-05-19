"""Defines the format for printing SshProcess objects"""

# Third-party libraries

# Project libraries
from where_my_tunnels.ssh_process import SshProcess

RENDER_DICT = {
    "master_socket": {
        "color": "cyan",
        "title": "MASTER SOCKET",
    },
    "socket_forward": {
        "color": "magenta",
        "title": "SOCKET FORWARD",
    },
    "socket_session": {
        "color": "yellow",
        "title": "SOCKET SESSION",
    },
    "traditional_tunnel": {
        "color": "magenta",
        "title": "TRADITIONAL TUNNEL",
    },
    "traditional_session": {
        "color": "yellow",
        "title": "TRADITIONAL SESSION",
    },
    "LISTEN": {
        "color": "blue",
    },
    "ESTABLISHED": {
        "color": "blue",
    },
}


def return_with_color(text: str, color: str, bold: bool = False) -> str:
    """Returns text wrapped in color tags

    Args:
        text: The text to wrap
        color: The color to use

    Returns:
        The text wrapped in color tags
    """
    if bold:
        color = f"bold {color}"
    return f"[{color}]{text}[/{color}]"


def render_ssh_process(process: SshProcess) -> str:
    """Turns an ssh process into a printable string

    Args:
        process: The ssh process

    Returns:
        The ssh process as a string
    """
    out_string = f"{RENDER_DICT[process.ssh_type]['title']}: "
    if process.socket_file:
        out_string += f"{process.socket_file} "
    out_string += f"{process.username.split('\\')[-1].lower()}@"
    out_string += f"{process.arguments.destination_host}:{process.arguments.destination_port} "
    out_string += f"({process.pid}) "
    if process.malformed_message is not None:
        out_string += f"- {process.malformed_message}"

    return return_with_color(
        text=out_string,
        color=(
            RENDER_DICT[process.ssh_type]["color"]
            if process.malformed_message is None
            else process.malformed_message_color
        ),
    )


def render_connection(connection: object) -> str:
    """Turns a connection into a printable string

    Args:
        connection: The psutil connection

    Returns:
        The connection as a string
    """
    if connection.status == "LISTEN":
        return return_with_color(
            text=f"LISTEN {connection.laddr.ip}:{connection.laddr.port}", color=RENDER_DICT[connection.status]["color"]
        )
    if connection.status == "ESTABLISHED":
        return return_with_color(
            text=(
                f"ESTABLISHED {connection.laddr.ip}:{connection.laddr.port} -> "
                f"{connection.raddr.ip}:{connection.raddr.port}"
            ),
            color=RENDER_DICT[connection.status]["color"],
        )
    return str(connection)
