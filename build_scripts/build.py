# Standard libraries
import argparse
import json
import os
import shutil
import subprocess
import time

PARENT_DIR = "/".join(__file__.replace("\\", "/").split("/")[:-2])
with open(file=f"{PARENT_DIR}/VERSION.txt", encoding="utf-8") as version_file:
    VERSION = version_file.read().strip()

# ANSI color codes
RESET = "\033[0m"
CYAN = "\033[36m"
YELLOW = "\033[1;33m"
RED = "\033[31m"
GREEN = "\033[32m"

# Table column sizes
BUILD_COLUMN_SIZE = 7
ARCHITECTURE_COLUMN_SIZE = 14
OS_COLUMN_SIZE = 10
LIBC_COLUMN_SIZE = 12
PYTHON_COLUMN_SIZE = 10
TOTAL_COLUMN_SIZE = (
    BUILD_COLUMN_SIZE + ARCHITECTURE_COLUMN_SIZE + OS_COLUMN_SIZE + LIBC_COLUMN_SIZE + PYTHON_COLUMN_SIZE + 4
)


def print_timespan(start_time: float) -> str:
    """Returns the timespan (start time - current time) as a string

    Args:
        start_time: Seconds since the epoch

    Returns:
        Timespan as a string
    """
    timespan = time.time() - start_time
    hours = timespan // 3600
    minutes = (timespan % 3600) // 60
    seconds = timespan % 60
    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    elif minutes > 0:
        return f"{int(minutes)}m {int(seconds)}s"
    return f"{seconds:.2f}s"


def run_command(command: str, capture_output: bool = True) -> subprocess.CompletedProcess:
    """Runs a command and prints statistics on the output

    Args:
        command: The command to run
        capture_output: Whether to capture the output

    Raises:
        RuntimeError: If the command returns a non-zero exit code

    Returns:
        The completed process
    """
    print(YELLOW + f'Running command: "{command}"' + RESET, end=" ", flush=True)
    start_time = time.time()
    result = subprocess.run(
        command.split(" "),
        shell=True,
        text=True,
        capture_output=capture_output,
        cwd=PARENT_DIR,
        encoding="utf-8",
        errors="backslashreplace",
    )
    time_span_str = print_timespan(start_time)
    if result.returncode != 0:
        error_message = f'Command: "{command}" failed with return code {result.returncode} after {time_span_str}'
        if result.stdout is not None or result.stderr is not None:
            error_message += f"\nstdout: {result.stdout}\nstderr: {result.stderr}"
        raise RuntimeError(error_message)
    print(CYAN + f"- completed in {time_span_str}" + RESET)
    return result


def create_windows_image(python_version: str, python_executable_path: str) -> str:
    """Builds a windows image

    Args:
        python_version: The version of python to use (this is used to check the python executable version)
        python_executable_path: Path to the python executable to use

    Raises:
        RuntimeError: Raised if the python version does not match the expected version

    Returns:
        The name of the created executable
    """
    os.makedirs(f"{PARENT_DIR}/dist/windows/", exist_ok=True)
    executable_name = f"wheremytunnels_v{VERSION}_windows_py{python_version}.exe"

    print(CYAN + f"{'-' * 15} Building wheremytunnels for windows using {python_executable_path} {'-' * 15}" + RESET)

    venv_dir = f"{PARENT_DIR}/build_scripts/windows_build_python{python_version}.venv"
    get_python_version_command = f"{python_executable_path} --version"
    create_python_env_command = f"{python_executable_path} -m venv {venv_dir}"
    install_python_libraries = (
        f"{venv_dir}/Scripts/activate.ps1 "
        f"&& pip install --upgrade pip setuptools wheel nuitka "
        f"&& pip install {PARENT_DIR}"
    )
    nuitka_build_command = f"{venv_dir}/Scripts/activate.ps1 && nuitka --onefile --follow-imports --output-filename={PARENT_DIR}/dist/windows/{executable_name} {PARENT_DIR}/main.py"
    test_executable_command = f"{PARENT_DIR}/dist/windows/{executable_name} --version"

    python_executable_version = run_command(get_python_version_command, capture_output=True).stdout.split()[-1].strip()
    if not python_executable_version.startswith(python_version):
        raise RuntimeError(
            RED
            + f"Error: Python version mismatch. Expected {python_version}, but got {python_executable_version}."
            + RESET
        )
    print(CYAN + f"Using Python version: {python_executable_version}" + RESET)
    run_command(create_python_env_command, capture_output=True)
    run_command(install_python_libraries, capture_output=True)
    run_command(nuitka_build_command, capture_output=True)
    run_command(test_executable_command, capture_output=True)
    shutil.rmtree(venv_dir)
    print(CYAN + f"Created executable: {PARENT_DIR}/dist/windows/{executable_name}" + RESET)
    return executable_name


def create_linux_image(libc: str, libc_version: str, architecture: str, python_version: str):
    """Build a linux image

    Args:
        libc: Specifies whether to use glibc or musl
        libc_version: Specifies the version of the libc to use
        architecture: Specifies the architecture to build for
        python_version: The Python version to use
    """
    os.makedirs(f"{PARENT_DIR}/dist/linux/", exist_ok=True)
    compile_info = f"{libc}_{libc_version}_{architecture}_py{python_version}"
    compile_name = f"wheremytunnels-compiler-{compile_info}"
    executable_name = f"wheremytunnels_v{VERSION}_linux_{compile_info}.bin"
    repository_version = libc_version.replace(".", "_")

    print(CYAN + f"{'-' * 15} Building wheremytunnels for linux {compile_info} {'-' * 15}" + RESET)

    create_compiler_image_command = (
        "docker build "
        f"-t {compile_name}:{VERSION} "
        f"-f {PARENT_DIR}/build_scripts/{libc}-compiler-Dockerfile "
        f"--build-arg ARCHITECTURE={architecture} "
        f"--build-arg REPOSITORY_VERSION={repository_version} "
        f"--build-arg PYTHON_VERSION={python_version} "
        f"--progress=plain "
        "."
    )
    create_compiler_container_command = f"docker run --name {compile_name} {compile_name}:{VERSION}"
    copy_executable_command = (
        f"docker cp {compile_name}:/src/wheremytunnels.bin {PARENT_DIR}/dist/linux/{executable_name}"
    )
    delete_image_command = f"docker rmi --force {compile_name}:{VERSION}"
    delete_container_command = f"docker rm --force {compile_name}"
    run_command(delete_container_command, capture_output=True)
    run_command(create_compiler_image_command, capture_output=True)
    run_command(create_compiler_container_command, capture_output=True)
    run_command(copy_executable_command, capture_output=True)
    run_command(delete_container_command, capture_output=True)
    run_command(delete_image_command, capture_output=True)
    print(GREEN + f"Created executable: {PARENT_DIR}/dist/linux/{executable_name}" + RESET)


def create_linux_images(build_list: list[dict[str, str]]) -> None:
    """Builds all linux images in the build list

    Args:
        build_list: The parsed build list
    """
    for build_config in build_list:
        if build_config["operating_system"] != "linux":
            continue
        create_linux_image(
            libc=build_config["libc"],
            libc_version=build_config["libc_version"],
            architecture=build_config["architecture"],
            python_version=build_config["python_version"],
        )


def print_build_list(build_list: list[dict[str, str]]) -> None:
    """Prints the build list as a table

    Args:
        build_list: The parsed build list
    """
    print(
        f"┌{'─' * BUILD_COLUMN_SIZE}─{'─' * ARCHITECTURE_COLUMN_SIZE}─{'─' * OS_COLUMN_SIZE}─{'─' * LIBC_COLUMN_SIZE}─{'─' * PYTHON_COLUMN_SIZE}┐"
    )
    print(f"│{'Available Builds':^{TOTAL_COLUMN_SIZE}}│")
    print(
        f"├{'─' * BUILD_COLUMN_SIZE}┬{'─' * ARCHITECTURE_COLUMN_SIZE}┬{'─' * OS_COLUMN_SIZE}┬{'─' * LIBC_COLUMN_SIZE}┬{'─' * PYTHON_COLUMN_SIZE}┤"
    )
    print(
        f"│{'Build':^{BUILD_COLUMN_SIZE}}│{'Architecture':^{ARCHITECTURE_COLUMN_SIZE}}│{'OS':^{OS_COLUMN_SIZE}}│{'libc':^{LIBC_COLUMN_SIZE}}│{'Python':^{PYTHON_COLUMN_SIZE}}│"
    )
    print(
        f"├{'─' * BUILD_COLUMN_SIZE}┼{'─' * ARCHITECTURE_COLUMN_SIZE}┼{'─' * OS_COLUMN_SIZE}┼{'─' * LIBC_COLUMN_SIZE}┼{'─' * PYTHON_COLUMN_SIZE}┤"
    )
    for build_config in build_list:
        if build_config["operating_system"] == "linux":
            libc_string = build_config["libc"] + "─" + build_config["libc_version"]
        else:
            libc_string = "N/A"
        print(
            f"│{build_list.index(build_config) + 1:^{BUILD_COLUMN_SIZE}}│"
            f"{build_config['architecture']:^{ARCHITECTURE_COLUMN_SIZE}}│"
            f"{build_config['operating_system']:^{OS_COLUMN_SIZE}}│"
            f"{libc_string:^{LIBC_COLUMN_SIZE}}│"
            f"{build_config['python_version']:^{PYTHON_COLUMN_SIZE}}│"
        )
    print(
        f"└{'─' * BUILD_COLUMN_SIZE}┴{'─' * ARCHITECTURE_COLUMN_SIZE}┴{'─' * OS_COLUMN_SIZE}┴{'─' * LIBC_COLUMN_SIZE}┴{'─' * PYTHON_COLUMN_SIZE}┘"
    )
    print(YELLOW + "Use the --build/-b option with the build number to build a specific image." + RESET)
    print(YELLOW + "NOTE: glibc version <2.28 are not supported due to package manager limitations" + RESET)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="build.py", description="Build script for compiling wheremytunnels with Nuitka"
    )

    parser.add_argument("--version", "-v", action="version", version=f"WhereMyTunnels v{VERSION}")
    parser.add_argument("--list", action="store_true", help="List all available images", default=False, required=False)
    parser.add_argument("--build-all", action="store_true", help="Build all images", default=False, required=False)
    parser.add_argument(
        "--build-linux", action="store_true", help="Build all linux images", default=False, required=False
    )
    parser.add_argument(
        "--build-windows", action="store_true", help="Build all windows images", default=False, required=False
    )
    parser.add_argument(
        "--build",
        "-b",
        type=int,
        help="Build specific image by its number from the build list",
        default=None,
        required=False,
    )
    parser.add_argument(
        "--set-python-executable",
        type=str,
        help="Set the python executable path for windows builds (default: python)",
        default="python",
    )

    args = parser.parse_args()

    with open(file=f"{PARENT_DIR}/build_scripts/build_list.json", encoding="utf-8") as build_list_file:
        build_list = json.load(build_list_file)

    # Validate build list
    windows_build_info = {
        "operating_system": "windows",
        "architecture": "x86_64",
        "python_version": "",
    }
    for build in build_list:
        if "operating_system" not in build:
            raise KeyError(f'Error: "operating_system" key missing in build configuration: {build}')
        if "python_version" not in build:
            raise KeyError(f'Error: "python_version" key missing in build configuration: {build}')
        if build["operating_system"] == "linux":
            if "libc" not in build:
                raise KeyError(f'Error: "libc" key missing in build configuration: {build}')
            if "libc_version" not in build:
                raise KeyError(f'Error: "libc_version" key missing in build configuration: {build}')
            if "architecture" not in build:
                raise KeyError(f'Error: "architecture" key missing in build configuration: {build}')
        elif build["operating_system"] == "windows":
            if "architecture" not in build:
                raise KeyError(f'Error: "architecture" key missing in build configuration: {build}')
            if build["architecture"] != "x86_64":
                raise ValueError(f"Error: Unsupported architecture for windows build: {build['architecture']}")
            windows_build_info = build

    if args.list:
        print_build_list(build_list)
        exit(0)
    elif args.build_all:
        create_linux_images(build_list)
        create_windows_image(
            python_version=windows_build_info["python_version"], python_executable_path=args.set_python_executable
        )
    elif args.build_linux:
        create_linux_images(build_list)
    elif args.build_windows:
        create_windows_image(
            python_version=windows_build_info["python_version"], python_executable_path=args.set_python_executable
        )
    elif args.build:
        try:
            build_config = build_list[args.build - 1]
        except IndexError:
            print(RED + f"Error: Build number {args.build} is out of range." + RESET)
            print_build_list(build_list)
            exit(1)
        if build_config["operating_system"] == "linux":
            executable_name = create_linux_image(
                libc=build_config["libc"],
                libc_version=build_config["libc_version"],
                architecture=build_config["architecture"],
                python_version=build_config["python_version"],
            )
        elif build_config["operating_system"] == "windows":
            executable_name = create_windows_image(
                python_version=build_config["python_version"], python_executable_path=args.set_python_executable
            )
    else:
        parser.print_help()
