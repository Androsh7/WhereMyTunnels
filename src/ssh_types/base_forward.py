"""Defines the Forward class"""

# Standard libraries
import psutil
from ipaddress import ip_address, IPv4Address, IPv6Address
from typing import Literal, Union, Optional

# Third-party libraries
from attrs import define, field, validators

# Project libraries
from src.ssh_types.default import FORWARD_TYPES


@define
class Forward:
    forward_type: Literal[FORWARD_TYPES] = field(
        validator=validators.and_(validators.instance_of(str), validators.in_(FORWARD_TYPES))
    )
    source_port: int = field(
        validator=validators.and_(validators.instance_of(int), validators.ge(1), validators.le(65535))
    )
    destination_host: Union[IPv4Address, IPv6Address, str] = field(
        validator=validators.or_(
            validators.instance_of(IPv4Address), validators.instance_of(IPv6Address), validators.instance_of(str)
        )
    )
    remote_port: int = field(
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
        if self.forward_type == "local":
            return (
                f'{"[red]" if self.malformed_message else ""}'
                f'{self.gateway_ip if self.gateway_ip else "127.0.0.1"}:{self.source_port} -> '
                f"{self.destination_host}:{self.remote_port}"
                f'{ " - " + self.malformed_message + "[/red]" if self.malformed_message else ""}'
            )
        return (
            f'{"[red]" if self.malformed_message else ""}'
            f"127.0.0.1:{self.remote_port}"
            f' <- {self.gateway_ip if self.gateway_ip else "127.0.0.1"}:{self.source_port}'
            f'{ " - " + self.malformed_message + "[/red]" if self.malformed_message else ""}'
        )

    @classmethod
    def from_argument(cls, forward_type: Literal[FORWARD_TYPES], argument: str):
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
            source_port=int(split_arguments[-3]),
            destination_host=destination_host,
            remote_port=int(split_arguments[-1]),
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
