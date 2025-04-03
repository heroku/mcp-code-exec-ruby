import subprocess
from typing import Optional, Dict, Any, List

def run_command(cmd: List[str]) -> Dict[str, Any]:
    """Executes a command using subprocess and returns output and errors."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
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

def install_dependencies(packages: Optional[List[str]]) -> Dict[str, Any]:
    """
    Installs required packages for a given language using the appropriate package manager.

    Args:
        packages: A list of package names to install

    Returns:
        The result of the package installation command, or a no-op result if no install is needed.
    """

    if not packages:
        return {"returncode": 0, "stdout": "", "stderr": ""}  # No installation needed

    cmd = ["pip", "install"] + packages
    return run_command(cmd)

def code_exec_python(code: str, packages: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Executes a Python code snippet with optional pip dependencies.

    Args:
        code: The Python code to execute as a string.
        packages: An optional list of pip package names to install before execution.

    Returns:
        A dictionary containing:
            - 'returncode': Exit status of the execution
            - 'stdout': Captured standard output
            - 'stderr': Captured standard error or install failure messages
    """
    install_result = install_dependencies(packages)

    if install_result["returncode"] != 0:
        return {
            "returncode": install_result["returncode"],
            "stdout": install_result["stdout"],
            "stderr": f"Dependency install failed:\n{install_result['stderr']}"
        }

    return run_command(["python3", "-c", code])