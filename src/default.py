"""Defines default values and constants"""

VERSION = "1.0.0"
FORWARD_ARGUMENT_TO_STRING = {
    "L": "local",
    "R": "reverse",
    "D": "dynamic",
}
FORWARD_TYPES = tuple(FORWARD_ARGUMENT_TO_STRING.values())
SSH_TYPES = ("master_socket", "socket_forward", "socket_session", "traditional_tunnel", "traditional_session")
SSH_FLAGS = tuple("46AaCfGgKkMNnqsTtVvXxYy")
SSH_VALUE_ARGUMENTS = (
    "p",
    "l",
    "i",
    "S",
    "J",
    "W",
    "o",
    "F",
    "E",
    "b",
    "w",
    "c",
    "m",
    "O",
    "B",
    "Q",
    "I",
    "K",
    "t",
    "T",
    "R",
    "L",
    "D",
)
