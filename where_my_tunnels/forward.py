"""Defines the Forward class"""

# Standard libraries
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Literal

# Third-party libraries
from attrs import define, field, validators

# Project libraries
from where_my_tunnels.default import FORWARD_ARGUMENT_TO_STRING, FORWARD_TYPES
from where_my_tunnels.ssh_arguments import SshArguments
from where_my_tunnels.utils import conn_validator


@define
class Forward:
    """Class to define an ssh forward"""

    forward_type: Literal[FORWARD_TYPES] = field(
        validator=validators.and_(validators.instance_of(str), validators.in_(FORWARD_TYPES))
    )
    ssh_connection_destination: IPv4Address | IPv6Address | str = field(
        validator=validators.or_(
            validators.instance_of(IPv4Address), validators.instance_of(IPv6Address), validators.instance_of(str)
        )
    )
    source_port: int = field(
        validator=validators.and_(validators.instance_of(int), validators.ge(1), validators.le(65535))
    )
    destination_host: IPv4Address | IPv6Address | str = field(
        validator=validators.or_(
            validators.instance_of(IPv4Address), validators.instance_of(IPv6Address), validators.instance_of(str)
        )
    )
    destination_port: int = field(
        validator=validators.and_(validators.instance_of(int), validators.ge(1), validators.le(65535))
    )
    gateway_ip: IPv4Address | IPv6Address | str | None = field(
        default=None,
        validator=validators.optional(
            validators.or_(
                validators.instance_of(IPv4Address), validators.instance_of(IPv6Address), validators.instance_of(str)
            )
        ),
    )
    malformed_message: str | None = field(default=None, validator=validators.optional(validators.instance_of(str)))
    malformed_message_color: str | None = field(
        default="bold red", validator=validators.optional(validators.instance_of(str))
    )
    attached_connections: list[object] = field(
        factory=list,
        validator=validators.deep_iterable(
            member_validator=conn_validator,
            iterable_validator=validators.instance_of(list),
        ),
    )
    children: list = field(factory=list, validator=validators.instance_of(list))

    def __str__(self):
        out_string = ""

        # Print starting color
        if self.malformed_message:
            out_string += f"[{self.malformed_message_color}]"
        else:
            out_string += "[green]"

        # print local forward
        if self.forward_type == "local":
            if self.gateway_ip:
                out_string += "LOCAL GATEWAY FORWARD: "
                out_string += f"{self.gateway_ip}:{self.source_port}"
            else:
                out_string += "LOCAL FORWARD: "
                out_string += f"127.0.0.1:{self.source_port}"

            if self.destination_host != ip_address("127.0.0.1"):
                out_string += f" -> {self.ssh_connection_destination}"
                out_string += f" -> {self.destination_host}:{self.destination_port}"
            else:
                out_string += f" -> {self.ssh_connection_destination}:{self.destination_port}"
        elif self.forward_type == "reverse":
            if self.gateway_ip:
                out_string += "REVERSE GATEWAY FORWARD: "
            else:
                out_string += "REVERSE FORWARD: "

            if self.destination_host != ip_address("127.0.0.1"):
                out_string += f"{self.destination_host}:{self.destination_port} <- "
                out_string += "127.0.0.1 <- "
            else:
                out_string += f"{self.destination_host}:{self.destination_port} <- "

            out_string += f"{self.ssh_connection_destination}:{self.source_port}"
        elif self.forward_type == "dynamic":
            out_string += "DYNAMIC FORWARD: "
            out_string += f"127.0.0.1:{self.source_port} -> {self.destination_host} -> *:*"

        # print ending color
        if self.malformed_message:
            out_string += f" - {self.malformed_message}"
            out_string += f"[/{self.malformed_message_color}]"
        else:
            out_string += "[/green]"

        return out_string

    @classmethod
    def from_argument(
        cls,
        forward_type: Literal[FORWARD_TYPES],
        argument: str,
        ssh_connection_destination: IPv4Address | IPv6Address | str,
    ):
        """Creates an ssh forward

        Args:
            forward_type: The forward type
            argument: The forward argument string
            ssh_connection_destination: The ssh connection's destination host
        """
        split_arguments = Forward.split_forward_arguments(argument)

        if forward_type == "dynamic":
            return cls(
                forward_type=forward_type,
                ssh_connection_destination=ssh_connection_destination,
                source_port=int(split_arguments[0]),
                destination_host=ssh_connection_destination,
                destination_port=1,
                gateway_ip=None,
            )

        try:
            destination_host = ip_address(split_arguments[-2])
        except ValueError:
            destination_host = split_arguments[-2]

        if len(split_arguments) != 4:
            gateway_ip = None
        else:
            try:
                gateway_ip = ip_address(split_arguments[-4])
            except ValueError:
                gateway_ip = split_arguments[-4]
        return cls(
            forward_type=forward_type,
            ssh_connection_destination=ssh_connection_destination,
            source_port=int(split_arguments[-3]),
            destination_host=destination_host,
            destination_port=int(split_arguments[-1]),
            gateway_ip=gateway_ip,
        )

    @staticmethod
    def split_forward_arguments(argument: str) -> list[str]:
        """Splits the 4 elements of a forward into a list
        [forward/reverse, source port, destination host, destination port]

        Args:
            argument: the argument string to split

        Returns:
            list of split arguments
        """
        split_arguments = []
        reading_ipv6 = False
        out_string = ""
        for char in argument:
            if char == "[":
                reading_ipv6 = True
                out_string += char
            elif char == "]":
                reading_ipv6 = False
                out_string += char
            elif char == ":" and not reading_ipv6:
                split_arguments.append(out_string)
                out_string = ""
            else:
                out_string += char
        split_arguments.append(out_string)
        return split_arguments


def build_forward_list(
    arguments: SshArguments, connections: list[object], has_socket_file: bool = False
) -> list[Forward]:
    """Creates a list of forward objects

    Args:
        arguments: The ssh arguments
        connections: Any attached connections
        has_socket_file: Whether or not the the parent process has a socket file
            this disables the "NO ATTACHED LISTENING CONNECTION" message

    Raises:
        ValueError: If an invalid forward type is provided

    Returns:
        List of forwards
    """
    out_list = []
    for argument, value in arguments.value_arguments:
        # Create forward object
        if argument not in ("L", "R", "D"):
            continue
        forward = Forward.from_argument(
            forward_type=FORWARD_ARGUMENT_TO_STRING[argument],
            argument=value,
            ssh_connection_destination=arguments.destination_host,
        )

        # Attach connections
        for index, connection in enumerate(connections):
            if connection is None:
                continue
            if (
                (
                    forward.forward_type in ("local", "dynamic")
                    and connection.status == "LISTEN"
                    and isinstance(connection.laddr, tuple)
                    and connection.laddr.port == forward.source_port
                )
                or (connection.status == "ESTABLISHED" and connection.laddr.port == forward.source_port)
                or (
                    forward.forward_type == "reverse"
                    and connection.status == "LISTEN"
                    and isinstance(connection.raddr, tuple)
                    and connection.raddr.port == forward.source_port
                )
            ):
                forward.attached_connections.append(connection)
                connections[index] = None

        # Mark forwards with missing connections as malformed
        if len(forward.attached_connections) == 0:
            if forward.forward_type in ("local", "dynamic") and not has_socket_file:
                forward.malformed_message = "NO ATTACHED LISTENING CONNECTION"
            elif forward.forward_type == "reverse" and not has_socket_file:
                forward.malformed_message = "REVERSE FORWARD NOT CURRENTLY IN USE"
                forward.malformed_message_color = "dark_orange"

        out_list.append(forward)

    if len(out_list) is None:
        return None
    return out_list
