"""Defines the Forward class"""

# Standard libraries
import psutil
from ipaddress import ip_address, IPv4Address, IPv6Address
from typing import Literal, Union, Optional

# Third-party libraries
from attrs import define, field, validators

# Project libraries
from src.default import FORWARD_TYPES


@define
class Forward:
    forward_type: Literal[FORWARD_TYPES] = field(
        validator=validators.and_(validators.instance_of(str), validators.in_(FORWARD_TYPES))
    )
    ssh_connection_destination: Union[IPv4Address, IPv6Address, str] = field(
        validator=validators.or_(
            validators.instance_of(IPv4Address), validators.instance_of(IPv6Address), validators.instance_of(str)
        )
    )
    source_port: int = field(
        validator=validators.and_(validators.instance_of(int), validators.ge(1), validators.le(65535))
    )
    destination_host: Union[IPv4Address, IPv6Address, str] = field(
        validator=validators.or_(
            validators.instance_of(IPv4Address), validators.instance_of(IPv6Address), validators.instance_of(str)
        )
    )
    destination_port: int = field(
        validator=validators.and_(validators.instance_of(int), validators.ge(1), validators.le(65535))
    )
    gateway_ip: Optional[Union[IPv4Address, IPv6Address, str]] = field(
        default=None,
        validator=validators.optional(
            validators.or_(
                validators.instance_of(IPv4Address), validators.instance_of(IPv6Address), validators.instance_of(str)
            )
        ),
    )
    malformed_message: Optional[str] = field(default=None, validator=validators.optional(validators.instance_of(str)))
    attached_connections: list[psutil._common.pconn] = field(
        factory=list,
        validator=validators.deep_iterable(
            member_validator=validators.instance_of(psutil._common.pconn),
            iterable_validator=validators.instance_of(list),
        ),
    )

    def __str__(self):
        out_string = ""

        # Print starting color
        if self.malformed_message:
            out_string += "[bold red]"
        else:
            out_string += "[green]"

        # print local forward
        if self.forward_type == "local":
            if self.gateway_ip:
                out_string += "LOCAL GATEWAY FORWARD: "
                out_string += f'{self.gateway_ip}:{self.source_port}'
            else:
                out_string += "LOCAL FORWARD: "
                out_string += f'127.0.0.1:{self.source_port}'

            if self.destination_host != ip_address("127.0.0.1"):
                out_string += f' -> {self.ssh_connection_destination}'
                out_string += f' -> {self.destination_host}:{self.destination_port}'
            else:
                out_string += f' -> {self.ssh_connection_destination}:{self.destination_port}'
        elif self.forward_type == "reverse":
            if self.gateway_ip:
                out_string += "REVERSE GATEWAY FORWARD: "
            else:
                out_string += "REVERSE FORWARD: "
            
            if self.destination_host != ip_address('127.0.0.1'):
                out_string += f'{self.destination_host}:{self.destination_port} <- '
                out_string += f'127.0.0.1 <- '
            else:
                out_string += f'{self.destination_host}:{self.destination_port} <- '
            
            out_string += f'{self.ssh_connection_destination}:{self.source_port}'

        # print ending color
        if self.malformed_message:
            out_string += f' - {self.malformed_message}'
            out_string += "[/bold red]"
        else:
            out_string += "[/green]"

        return out_string

    @classmethod
    def from_argument(cls, forward_type: Literal[FORWARD_TYPES], argument: str, ssh_connection_destination: Union[IPv4Address, IPv6Address, str]):
        split_arguments = Forward.split_forward_arguments(argument)

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
    def split_forward_arguments(argument: str):
        split_arguments = []
        reading_ipv6 = False
        out_string = ""
        for char in argument:
            if char == "[":
                reading_ipv6 = True
            elif char == "]":
                reading_ipv6 = False
            elif char == ":" and not reading_ipv6:
                split_arguments.append(out_string)
                out_string = ""
            else:
                out_string += char
        split_arguments.append(out_string)
        return split_arguments
