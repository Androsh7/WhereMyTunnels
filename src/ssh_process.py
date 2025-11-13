"""Defines the SshProcess, SshArguments, and ValueArgument classes"""

# Standard libraries
import psutil
from typing import Union
from ipaddress import IPv4Address, IPv6Address, ip_address

# Third-party libraries
import psutil
from attrs import define, field, validators
from loguru import logger

# Project libraries
from src.default import SSH_FLAGS, SSH_VALUE_ARGUMENTS


@define
class SshArguments:
    """Class for organizing the ssh command list"""

    executable_name: str = field(validator=validators.instance_of(str))
    destination_host: Union[IPv4Address, IPv6Address, str] = field(
        validator=validators.or_(
            validators.instance_of(IPv4Address), validators.instance_of(IPv6Address), validators.instance_of(str)
        )
    )
    destination_port: int = field(
        validator=validators.and_(validators.instance_of(int), validators.ge(1), validators.le(65535))
    )
    flags: list[str] = field(
        validator=validators.deep_iterable(
            member_validator=validators.instance_of(str), iterable_validator=validators.instance_of(list)
        )
    )
    value_arguments: list[tuple[str, str]] = field(
        validator=validators.deep_iterable(
            member_validator=validators.deep_iterable(
                member_validator=validators.instance_of(str), iterable_validator=validators.instance_of(tuple)
            ),
            iterable_validator=validators.instance_of(list),
        )
    )

    @classmethod
    def from_command_list(cls, cmd_list: list[str]):
        executable_name = cmd_list[0]
        destination_host = None
        destination_port = 22
        flags = []
        value_args = []

        # logger.debug(f"Parsing command list: {cmd_list}")
        # logger.debug(f'executable_name="{executable_name}"')
        argument_index = 1
        while argument_index < len(cmd_list):
            # logger.debug(f"Parsing argument index {argument_index}: {cmd_list[argument_index]}")

            # Search for arguments
            if cmd_list[argument_index].startswith("-"):

                # Search the arguments character-by-character
                char_index = 1
                while char_index < len(cmd_list[argument_index]):

                    # Search for arguments that require a value
                    char = cmd_list[argument_index][char_index]
                    if char in SSH_VALUE_ARGUMENTS:

                        # Grabs the argument type ("L", "R", "D", etc)
                        arg_type = char

                        # Normalize arguments so "-D9050" and ["-D", "9050"] both appear as ("D", "9050")
                        if len(arg_value := cmd_list[argument_index][char_index + 1 :]) == 0:
                            # logger.debug(f"Parsing argument index {argument_index + 1} for argument value: {cmd_list[argument_index + 1]}")
                            arg_value = cmd_list[argument_index + 1]
                            argument_index += 1

                        # Add the arg_value and arg_type to the value_args list
                        # logger.debug(f'Found value_argument: argument="{arg_type}", value="{arg_value}"')
                        value_args.append((arg_type, arg_value))
                        break

                    elif char in SSH_FLAGS:
                        flags.append(char)
                        char_index += 1
                        continue

                    # logger.error(f"Unknown argument {char}, treating as flag")
                    flags.append(char)
                    char_index += 1
                    continue

            # Grab the destination host
            elif destination_host is None:
                try:
                    destination_host = ip_address(cmd_list[argument_index])
                except ValueError:
                    destination_host = cmd_list[argument_index]
                # logger.debug(f'Found host="{destination_host}"')
            else:
                raise ValueError(f"Unexpected argument: {cmd_list[argument_index]}")

            argument_index += 1

        # Find the destination port
        for argument, value in value_args:
            if argument == "p":
                destination_port = int(value)

        return cls(
            executable_name=executable_name,
            destination_host=destination_host,
            destination_port=destination_port,
            flags=flags,
            value_arguments=value_args,
        )


@define
class SshProcess:
    """Stores the SSH process information"""

    username: str = field(validator=validators.instance_of(str))
    connections: list[psutil._common.pconn] = field(
        validator=validators.deep_iterable(
            member_validator=validators.instance_of(psutil._common.pconn),
            iterable_validator=validators.instance_of(list),
        )
    )
    pid: int = field(validator=validators.and_(validators.instance_of(int), validators.ge(1)))
    arguments: SshArguments = field(validator=validators.instance_of(SshArguments))
    raw_arguments: str = field(validator=validators.instance_of(str))

    @classmethod
    def from_process(cls, process: psutil.Process):
        username = process.info["username"]
        pid = process.info["pid"]
        connections = process.net_connections()
        arguments = SshArguments.from_command_list(process.info["cmdline"])

        return cls(
            username=username,
            arguments=arguments,
            pid=pid,
            connections=connections,
            raw_arguments=" ".join(process.info["cmdline"]),
        )
