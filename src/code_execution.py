import subprocess
import os
import shutil
import tempfile
from typing import Annotated, Optional, List, Dict, Any
from pydantic import Field
# local:
from src import config

def run_command(cmd: List[str], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Executes a command using subprocess and returns output and errors."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {
            "returncode": -2,
            "stdout": "",
            "stderr": "Error: Execution timed out"
        }

def install_dependencies(
    packages: Optional[List[str]],
    install_cmd_path: str = "gem",
    env: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Installs Ruby gems using the specified gem executable.

    Args:
        packages: A list of gem names to install.
        install_cmd_path: Path to the gem executable to use.
        env: Optional environment variables to pass to the subprocess.

    Returns:
        The result of the package installation command, or a no-op result if no install is needed.
    """
    if not packages:
        return {"returncode": 0, "stdout": "", "stderr": ""}  # No installation needed

    if env is None:
        commands = [install_cmd_path, "install", "--user-install"]
    else:
        commands = [install_cmd_path, "install"]

    cmd = commands + packages
    return run_command(cmd, env=env)

def gem_already_installed(gem_name: str, env: Optional[Dict[str, str]] = None) -> bool:
    result = subprocess.run(
        ["gem", "list", "-i", gem_name],
        capture_output=True,
        text=True,
        env=env
    )
    return result.returncode == 0 and result.stdout.strip() == "true"

def run_in_tempdir(code: str, packages: Optional[List[str]]) -> Dict[str, Any]:
    """
    Runs Ruby code in a temporary directory with optional gem dependencies.

    Gems are installed into a temporary directory and isolated from the user's global gem environment
    by setting GEM_HOME and GEM_PATH. This avoids polluting ~/.gem and prevents access to previously installed gems.

    Note: This is not a secure sandbox. The code still has full access to the filesystem and network.

    Args:
        code: The Ruby code to run.
        packages: Optional list of gem names to install before execution.

    Returns:
        Dictionary of returncode, stdout, and stderr.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        env = os.environ.copy()
        gem_home = os.path.join(temp_dir, ".gem")
        env["GEM_HOME"] = gem_home
        env["GEM_PATH"] = gem_home
        env["PATH"] = f"{os.path.join(gem_home, 'bin')}:{env['PATH']}"

        # install gems using the temp GEM_HOME
        install_result = install_dependencies(packages, install_cmd_path="gem", env=env)
        if install_result["returncode"] != 0:
            return {
                "returncode": install_result["returncode"],
                "stdout": install_result["stdout"],
                "stderr": f"Dependency install failed:\n{install_result['stderr']}"
            }

        temp_path = os.path.join(temp_dir, "script.rb")
        with open(temp_path, "w") as f:
            f.write(code)

        return run_command(["ruby", temp_path], env=env)

    finally:
        shutil.rmtree(temp_dir)


def code_exec_ruby(
    code: Annotated[
        str,
        Field(description="The Ruby code to execute as a string.")
    ],
    packages: Annotated[
        Optional[List[str]],
        Field(description="Optional list of gem names to install before execution.")
    ] = None
) -> Dict[str, Any]:
    """Executes a Ruby code snippet with optional gem dependencies.

    When `use_temp_dir` is True, the code and any installed gems are run in a throwaway temporary directory,
    and gems are isolated. When False, gems are installed to ~/.gem.

    The Ruby runtime has access to networking, the filesystem, and standard libraries.
    A non-zero exit code is an error and should be fixed.

    Returns:
        JSON containing:
            - 'returncode': Exit status of the execution.
            - 'stdout': Captured standard output.
            - 'stderr': Captured standard error or install failure messages.
    """
    if config.USE_TEMP_DIR:
        return run_in_tempdir(code, packages)

    # Otherwise, you can rely on pre-installed shared packages, if they exist:
    if packages:
        packages = [pkg for pkg in packages if not gem_already_installed(pkg)]

    install_result = install_dependencies(packages, install_cmd_path="gem")
    if install_result["returncode"] != 0:
        return {
            "returncode": install_result["returncode"],
            "stdout": install_result["stdout"],
            "stderr": f"Dependency install failed:\n{install_result['stderr']}"
        }

    env = os.environ.copy()
    env["GEM_HOME"] = os.path.expanduser("~/.gem")

    return run_command(["ruby", "-e", code], env=env)
