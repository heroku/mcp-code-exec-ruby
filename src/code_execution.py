import subprocess
import os
import shutil
import tempfile
from typing import Annotated, Optional, List, Dict, Any
from pydantic import Field

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


def install_dependencies(packages: Optional[List[str]], install_cmd_path: str = "gem") -> Dict[str, Any]:
    """
    Installs Ruby gems using the specified gem executable.

    Args:
        packages: A list of gem names to install.
        install_cmd_path: Path to the gem executable to use.

    Returns:
        The result of the package installation command, or a no-op result if no install is needed.
    """
    if not packages:
        return {"returncode": 0, "stdout": "", "stderr": ""}  # No installation needed

    cmd = [install_cmd_path, "install", "--user-install"] + packages
    return run_command(cmd)

def run_in_tempdir(code: str, packages: Optional[List[str]]) -> Dict[str, Any]:
    """
    Runs Ruby code in a temporary directory after installing optional gems.
    Note ruby gems are not installed in an isolated fashion.

    Note that this does NOT mean the code is fully isolated or secure - it just means the gem installations
    are isolated.

    Note that this does NOT mean the code is fully isolated or secure - it just means the package installations
    are isolated.

    Args:
        code: The code to run.
        packages: Optional gem packages to install before execution.

    Returns:
        Dictionary of returncode, stdout, and stderr.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        install_result = install_dependencies(packages, install_cmd_path="gem")
        if install_result["returncode"] != 0:
            return {
                "returncode": install_result["returncode"],
                "stdout": install_result["stdout"],
                "stderr": f"Dependency install failed:\n{install_result['stderr']}"
            }

        temp_path = os.path.join(temp_dir, "script.rb")
        with open(temp_path, "w") as f:
            f.write(code)

        env = os.environ.copy()
        # ensure package installs are installed to the temporary directory for installation isolation:
        env["GEM_HOME"] = os.path.join(temp_dir, ".gem")
        env["PATH"] = f"{os.path.join(env['GEM_HOME'], 'bin')}:{env['PATH']}"
        env["GEM_PATH"] = env["GEM_HOME"]

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
    ] = None,
    use_temp_dir: Annotated[
        bool,
        Field(description=(
            "If True, code and dependencies are run in a temporary working directory. "
            "Gems are installed in an isolated directory and will not affect or reuse the user's ~/.gem folder. "
            "Not a secure sandbox."
        ))
    ] = False
) -> Dict[str, Any]:
    """Executes a Ruby code snippet with optional gem dependencies.

    When `use_temp_dir` is True, the code and any installed gems are run in a throwaway temporary directory,
    and gems are isolated. When False, gems are installed to ~/.gem.

    The Ruby runtime has access to networking, the filesystem, and standard libraries.

    Returns:
        JSON containing:
            - 'returncode': Exit status of the execution.
            - 'stdout': Captured standard output.
            - 'stderr': Captured standard error or install failure messages.
    """
    if use_temp_dir:
        return run_in_tempdir(code, packages)

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
