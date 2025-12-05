"""Defines the SshArgument classes"""

# Standard libraries
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Optional, Union

# Third-party libraries
from attrs import define, field, validators

# Project libraries
from src.default import SSH_FLAGS, SSH_VALUE_ARGUMENTS


@define
class SshArguments:
    """Class for organizing the ssh command arguments"""

    executable_name: str = field(validator=validators.instance_of(str))
    username: Optional[str] = field(validator=validators.optional(validator=validators.instance_of(str)))
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
    raw_arguments: list[str] = field(
        validator=validators.deep_iterable(
            member_validator=validators.instance_of(str), iterable_validator=validators.instance_of(list)
        )
    )

    @classmethod
    def from_command_list(cls, cmd_list: list[str]):
        """Converts a list of commands into an SshArguments object

        Args:
            cmd_list: The list of ssh arguments

        Raises:
            ValueError: If an unexpected ssh argument is encountered
        """
        executable_name = cmd_list[0]
        username = None
        destination_host = None
        destination_port = 22
        flags = []
        value_args = []

        argument_index = 1
        while argument_index < len(cmd_list):

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
                            arg_value = cmd_list[argument_index + 1]
                            argument_index += 1

                        # Add the arg_value and arg_type to the value_args list
                        value_args.append((arg_type, arg_value))
                        break

                    if char in SSH_FLAGS:
                        flags.append(char)
                        char_index += 1
                        continue

                    flags.append(char)
                    char_index += 1
                    continue

            # Grab the destination host and username
            elif destination_host is None:
                if "@" in cmd_list[argument_index]:
                    username = cmd_list[argument_index].split("@")[0]
                    host_str = cmd_list[argument_index].split("@")[1]
                else:
                    host_str = cmd_list[argument_index]
                try:
                    destination_host = ip_address(host_str)
                except ValueError:
                    destination_host = host_str
            else:
                raise ValueError(f"Unexpected argument: {host_str}")

            argument_index += 1

        # Find the destination port
        for argument, value in value_args:
            if argument == "p":
                destination_port = int(value)

        return cls(
            username=username,
            executable_name=executable_name,
            destination_host=destination_host,
            destination_port=destination_port,
            flags=flags,
            value_arguments=value_args,
            raw_arguments=cmd_list,
        )
