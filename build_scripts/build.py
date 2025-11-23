# Standard libraries
import argparse
import json
import os
import shutil
import subprocess

PARENT_DIR = "/".join(__file__.replace("\\", "/").split("/")[:-2])
with open(file=f"{PARENT_DIR}/VERSION.txt", mode="r", encoding="utf-8") as version_file:
    VERSION = version_file.read().strip()

# ANSI color codes
RESET = "\033[0m"
CYAN = "\033[36m"
RED = "\033[31m"
YELLOW = "\033[1;33m"
WHITE = "\033[1;37m"

# Table column sizes
BUILD_COLUMN_SIZE = 7
ARCHITECTURE_COLUMN_SIZE = 14
OS_COLUMN_SIZE = 10
LIBC_COLUMN_SIZE = 12
PYTHON_COLUMN_SIZE = 10
TOTAL_COLUMN_SIZE = (
    BUILD_COLUMN_SIZE + ARCHITECTURE_COLUMN_SIZE + OS_COLUMN_SIZE + LIBC_COLUMN_SIZE + PYTHON_COLUMN_SIZE + 4
)


def run_command(command: str, capture_output: bool = True) -> tuple[str, str]:
    print(YELLOW + f'Running command: "{command}"' + RESET)
    result = subprocess.run(
        command.split(" "),
        shell=True,
        text=True,
        capture_output=capture_output,
        cwd=PARENT_DIR,
    )
    if result.returncode != 0:
        raise RuntimeError(f'Command: "{command}" failed with return code {result.returncode}\n\n{result.stderr}')
    return result.stdout, result.stderr


def create_windows_image(python_version: str) -> None:
    os.makedirs(f"{PARENT_DIR}/dist/windows/", exist_ok=True)
    executable_name = f"wheremytunnels_v{VERSION}_windows_py{python_version}.exe"
    python_minor_version = ".".join(python_version.split(".")[:2])
    create_python_env_command = (
        f"python{python_minor_version} -m venv {PARENT_DIR}/build_scripts/windows_python_env_py{python_version}"
    )
    install_python_libraries = (
        f"{PARENT_DIR}/build_scripts/windows_python_env_py{python_version}/Scripts/activate.ps1 "
        f"&& pip install --upgrade pip setuptools wheel nuitka "
        f"&& pip install {PARENT_DIR}"
    )
    nuitka_build_command = (
        f'nuitka --onefile --follow-imports --output-filename={PARENT_DIR}/dist/windows/{executable_name} {PARENT_DIR}/main.py'
    )
    run_command(create_python_env_command, capture_output=False)
    run_command(install_python_libraries, capture_output=False)
    run_command(nuitka_build_command, capture_output=False)
    shutil.rmtree(f"{PARENT_DIR}/build_scripts/windows_python_env_py{python_version}")
    print(CYAN + f"Created executable: {PARENT_DIR}/dist/windows/{executable_name}" + RESET)


def create_linux_image(libc: str, libc_version: str, architecture: str, python_version: str) -> str:
    """Build a linux image

    Args:
        libc: Specifies whether to use glibc or musl
        libc_version: Specifies the version of the libc to use
        architecture: Specifies the architecture to build for
        python_version: The Python version to use

    Raises:
        ValueError: If an unsupported libc type is provided

    Returns:
        Returns the name of the created executable
    """
    os.makedirs(f"{PARENT_DIR}/dist/linux/", exist_ok=True)
    compile_info = f"{libc}_{libc_version}_{architecture}_py{python_version}"
    compile_name = f"wheremytunnels-compiler-{compile_info}"
    executable_name = f"wheremytunnels_v{VERSION}_linux_{compile_info}.bin"

    # Set the repository type and version based on libc
    if libc == "glibc":
        repository = "manylinux"
    elif libc == "musl":
        repository = "musllinux"
    else:
        raise ValueError(f"Unsupported libc type: {libc}")
    repository_version = libc_version.replace(".", "_")

    print(CYAN + f"----- Building wheremytunnels {compile_info} -----" + RESET)

    create_compiler_image_command = (
        "docker build "
        f"-t {compile_name}:{VERSION} "
        f"-f {PARENT_DIR}/build_scripts/{repository}-compiler-Dockerfile "
        f"--build-arg ARCHITECTURE={architecture} "
        f"--build-arg REPOSITORY_VERSION={repository_version} "
        f"--build-arg PYTHON_VERSION={python_version} "
        "."
    )
    create_compiler_container_command = f"docker run --name {compile_name} " f"{compile_name}:{VERSION}"
    copy_executable_command = (
        f"docker cp " f"{compile_name}:/src/wheremytunnels.bin " f"{PARENT_DIR}/dist/linux/{executable_name}"
    )
    delete_image_command = f"docker rmi --force {compile_name}:{VERSION}"
    delete_container_command = f"docker rm --force {compile_name}"
    run_command(delete_container_command, capture_output=True)
    run_command(create_compiler_image_command, capture_output=False)
    run_command(create_compiler_container_command, capture_output=True)
    run_command(copy_executable_command, capture_output=True)
    run_command(delete_container_command, capture_output=True)
    run_command(delete_image_command, capture_output=True)
    return executable_name


def create_linux_images(build_list: list[dict[str, str]]) -> None:
    executable_name_list = []
    for build_config in build_list:
        if build_config["operating_system"] != "linux":
            continue
        executable_name_list.append(
            create_linux_image(
                libc=build_config["libc"],
                libc_version=build_config["libc_version"],
                architecture=build_config["architecture"],
                python_version=build_config["python_version"],
            )
        )
    print("----- Build complete -----")
    print(f"Created {len(executable_name_list)} executables:")
    for executable_name in executable_name_list:
        print(f"Created executable: {PARENT_DIR}/dist/linux/{executable_name}")


def print_build_list(build_list: list[dict[str, str]]) -> None:
    print(
        f'#{"-" * BUILD_COLUMN_SIZE}-{"-" * ARCHITECTURE_COLUMN_SIZE}-{"-" * OS_COLUMN_SIZE}-{"-" * LIBC_COLUMN_SIZE}-{"-" * PYTHON_COLUMN_SIZE}#'
    )
    print(f"|{'Available Builds':^{TOTAL_COLUMN_SIZE}}|")
    print(
        f'#{"-" * BUILD_COLUMN_SIZE}-{"-" * ARCHITECTURE_COLUMN_SIZE}-{"-" * OS_COLUMN_SIZE}-{"-" * LIBC_COLUMN_SIZE}-{"-" * PYTHON_COLUMN_SIZE}#'
    )
    print(
        f'|{"Build":^{BUILD_COLUMN_SIZE}}|{"Architecture":^{ARCHITECTURE_COLUMN_SIZE}}|{"OS":^{OS_COLUMN_SIZE}}|{"libc":^{LIBC_COLUMN_SIZE}}|{"Python":^{PYTHON_COLUMN_SIZE}}|'
    )
    print(
        f'#{"-" * BUILD_COLUMN_SIZE}+{"-" * ARCHITECTURE_COLUMN_SIZE}+{"-" * OS_COLUMN_SIZE}+{"-" * LIBC_COLUMN_SIZE}+{"-" * PYTHON_COLUMN_SIZE}#'
    )
    for build_config in build_list:
        if build_config["operating_system"] == "linux":
            libc_string = build_config["libc"] + "-" + build_config["libc_version"]
        else:
            libc_string = "N/A"
        print(
            (
                f"|{build_list.index(build_config) + 1:^{BUILD_COLUMN_SIZE}}|"
                f'{build_config["architecture"]:^{ARCHITECTURE_COLUMN_SIZE}}|'
                f'{build_config["operating_system"]:^{OS_COLUMN_SIZE}}|'
                f"{libc_string:^{LIBC_COLUMN_SIZE}}|"
                f'{build_config["python_version"]:^{PYTHON_COLUMN_SIZE}}|'
            )
        )
    print(
        f'#{"-" * BUILD_COLUMN_SIZE}-{"-" * ARCHITECTURE_COLUMN_SIZE}-{"-" * OS_COLUMN_SIZE}-{"-" * LIBC_COLUMN_SIZE}-{"-" * PYTHON_COLUMN_SIZE}#'
    )
    print("Use the --build/-b option with the build number to build a specific image.")
    print("NOTE: glibc version <2.28 are not supported due to package manager limitations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="build.py", description="Build script for wheremytunnels")

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
    parser.add_argument("--version", "-v", action="version", version=f"WhereMyTunnels v{VERSION}")
    parser.add_argument("--build-all", action="store_true", help="Build all images", default=False, required=False)
    parser.add_argument("--list", action="store_true", help="List all available images", default=False, required=False)

    args = parser.parse_args()

    with open(file=f"{PARENT_DIR}/build_scripts/build_list.json", mode="r", encoding="utf-8") as build_list_file:
        build_list = json.load(build_list_file)

    if args.list:
        print_build_list(build_list)
        exit(0)
    if args.build_linux or args.build_all:
        create_linux_images(build_list)
    if args.build_windows or args.build_all:
        for build_config in build_list:
            if build_config["operating_system"] == "windows":
                create_windows_image(python_version=build_config["python_version"])
    if args.build is not None:
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
            executable_name = create_windows_image(python_version=build_config["python_version"])
        print(f"Created executable: {PARENT_DIR}/dist/{build_config['operating_system']}/{executable_name}")
