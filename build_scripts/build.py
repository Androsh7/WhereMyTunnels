"""Script to build WhereMyTunnels"""

# Standard libraries
import argparse
import subprocess
from pathlib import Path
from typing import Literal

# Third-party libraries
from python_on_whales import docker

# Constants for paths
PARENT_DIRECTORY = Path(__file__).parent.parent

# Default build configurations
DEFAULT_LIBC = "glibc-2.28"
DEFAULT_ARCHITECTURE = "x86_64"

# Supported build options
ARCHITECTURE_OPTIONS = ["x86_64", "aarch64"]
DOCKER_IMAGE_DICT = {
    "glibc-2.17": {
        "x86_64": "androsh7/nuitka-compiler-x86_64-glibc-2.17-python-3.13.11",
        "aarch64": "androsh7/nuitka-compiler-aarch64-glibc-2.17-python-3.13.11",
    },
    "glibc-2.28": {
        "x86_64": "androsh7/nuitka-compiler-x86_64-glibc-2.28-python-3.13.11",
        "aarch64": "androsh7/nuitka-compiler-aarch64-glibc-2.28-python-3.13.11",
    },
}


def build_linux_executable(
    libc: Literal[DOCKER_IMAGE_DICT.keys()],
    architecture: Literal[ARCHITECTURE_OPTIONS],
    output_path: Path,
) -> Path:
    """Builds a linux executable

    Args:
        libc: The libc implementation to use
        architecture: The architecture to build for
        output_path: The output path for the built executable

    Returns:
        The path to the built executable
    """

    # Set the container name
    container_name = f"wheremytunnels-builder-{libc}-{architecture}"

    # create the container
    docker_url = DOCKER_IMAGE_DICT[libc][architecture]
    print(f"Loading docker image: {docker_url}")
    docker.container.create(
        image=docker_url, name=container_name, workdir="/src", command=["bash", "-lc", "sleep infinity"]
    )

    try:
        docker.container.start(container_name)

        # Copy project files into the container
        print(f"Copying project files into container {container_name}")
        docker.copy(PARENT_DIRECTORY / "README.md", f"{container_name}:/src/README.md")
        docker.copy(PARENT_DIRECTORY / "pyproject.toml", f"{container_name}:/src/pyproject.toml")
        docker.copy(PARENT_DIRECTORY / "setup.py", f"{container_name}:/src/setup.py")
        docker.copy(PARENT_DIRECTORY / "where_my_tunnels", f"{container_name}:/src/where_my_tunnels")

        # Install python modules inside the container
        print(f"Installing python modules inside container {container_name}")
        for chunk in docker.container.execute(
            container_name, ["python3", "-m", "pip", "install", ".[dev]"], stream=True
        ):
            print(chunk[1].decode(), end="")

        # Compile with Nuitka inside the container
        print(f"Compiling with Nuitka inside container {container_name}")
        for chunk in docker.container.execute(
            container_name,
            [
                "python3",
                "-m",
                "nuitka",
                "--onefile",
                "--static-libpython=yes",
                "--follow-imports",
                "--lto=yes",
                "--output-file=/src/where_my_tunnels.bin",
                "/src/where_my_tunnels/main.py",
            ],
            stream=True,
        ):
            print(chunk[1].decode(), end="")

        # Copy the built executable from the container to the host
        print(f"Copying built executable from container {container_name} to {output_path}")
        docker.copy(f"{container_name}:/src/where_my_tunnels.bin", output_path)

    finally:
        # Cleanup containers
        try:
            docker.container.stop(container_name)
        except Exception:
            pass
        try:
            docker.container.remove(container_name, force=True)
        except Exception:
            pass

    # Return the path to the built executable
    return output_path


def build_windows_executable(output_path: Path) -> Path:
    print("Installing python modules")
    subprocess.run(["pip", "install", ".[dev]"], shell=True, check=True, cwd=PARENT_DIRECTORY)
    print("Compiling with Nuitka")
    print(PARENT_DIRECTORY)
    subprocess.run(
        [
            "python",
            "-m",
            "nuitka",
            "--onefile",
            "--follow-imports",
            f"--output-file={output_path}",
            str(PARENT_DIRECTORY / "where_my_tunnels" / "main.py"),
        ],
        shell=True,
        check=True,
        cwd=PARENT_DIRECTORY,
    )
    return output_path


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
        "--libc",
        required=True,
        type=str,
        choices=DOCKER_IMAGE_DICT.keys(),
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
