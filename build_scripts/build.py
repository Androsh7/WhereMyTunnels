"""Script to build WhereMyTunnels"""

# Standard libraries
import argparse
from pathlib import Path
from typing import Literal

# Third-party libraries
from python_on_whales import docker

# Constants for paths
PARENT_DIRECTORY = Path(__file__).parent.parent

# Default build configurations
DEFAULT_PYTHON_VERSION = "3.13.11"
DEFAULT_LIBC = "glibc-2.24"
DEFAULT_ARCHITECTURE = "x86_64"

# Supported build options
ARCHITECTURE_OPTIONS = ["x86_64", "aarch64"]
LIBC_TO_DOCKERFILE = {
    "glibc-2.17": PARENT_DIRECTORY / "build_scripts" / "glibc-2_17-compiler-Dockerfile",
    "glibc-2.28": PARENT_DIRECTORY / "build_scripts" / "glibc-2_28-compiler-Dockerfile",
}


def build_linux_executable(
    python_version: str,
    libc: Literal[LIBC_TO_DOCKERFILE.keys()],
    architecture: Literal[ARCHITECTURE_OPTIONS],
    output_path: Path,
) -> Path:
    """Builds a linux executable

    Args:
        python_version: The python version to use
        libc: The libc implementation to use
        architecture: The architecture to build for
        output_path: The output path for the built executable

    Returns:
        The path to the built executable
    """

    # Set the container name
    container_name = f"wheremytunnels-builder-{python_version}-{libc}-{architecture}"
    print(f"Building container: {container_name}")

    # Build the Docker image
    docker.build(
        file=LIBC_TO_DOCKERFILE[libc],
        progress="plain",
        build_args={
            "PYTHON_VERSION": python_version,
            "ARCHITECTURE": architecture,
        },
        context_path=PARENT_DIRECTORY,
        tags=[f"{container_name}:latest"],
    )

    # Run the Docker container
    print(docker.run(image=f"{container_name}:latest", remove=False, name=container_name))

    # Download the executable from the container
    docker.copy(
        source=f"{container_name}:/src/wheremytunnels.bin",
        destination=output_path,
    )

    # Clean up the Docker container
    docker.remove(container_name)

    # Return the path to the built executable
    return output_path


def build_windows_executable(output_path: Path) -> Path:
    pass


def main():
    parser = argparse.ArgumentParser(
        prog="build.py", description="Build script for compiling wheremytunnels with Nuitka"
    )
    subparsers = parser.add_subparsers(dest="platform", required=True)

    # Windows argument parser
    windows = subparsers.add_parser("windows", help="Build wheremytunnels for Windows")
    windows.add_argument(
        "--output-path",
        required=True,
        type=Path,
        help="The output path for the built executable",
    )

    # Linux argument parser
    linux = subparsers.add_parser("linux", help="Build wheremytunnels for Linux")
    linux.add_argument(
        "--python-version",
        required=True,
        type=str,
        default=DEFAULT_PYTHON_VERSION,
        help=f"The python version to use for building wheremytunnels, default: {DEFAULT_PYTHON_VERSION}",
    )
    linux.add_argument(
        "--libc",
        required=True,
        type=str,
        choices=LIBC_TO_DOCKERFILE.keys(),
        default=DEFAULT_LIBC,
        help=f"The libc implementation to use, default: {DEFAULT_LIBC}",
    )
    linux.add_argument(
        "--architecture",
        required=True,
        type=str,
        choices=ARCHITECTURE_OPTIONS,
        default=DEFAULT_ARCHITECTURE,
        help=f"The architecture to build for, default: {DEFAULT_ARCHITECTURE}",
    )
    linux.add_argument(
        "--output-path",
        required=True,
        type=Path,
        help="The output path for the built executable",
    )
    args = parser.parse_args()

    if args.platform == "linux":
        built_executable_path = build_linux_executable(
            python_version=args.python_version,
            libc=args.libc,
            architecture=args.architecture,
            output_path=args.output_path,
        )
    elif args.platform == "windows":
        built_executable_path = build_windows_executable(
            output_path=args.output_path,
        )
    else:
        raise ValueError(f"Unsupported platform: {args.platform}")
    print(f"Built executable at: {built_executable_path}")


if __name__ == "__main__":
    main()
