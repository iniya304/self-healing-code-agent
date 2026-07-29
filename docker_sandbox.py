import subprocess
import sys
import tempfile
import os

def execute_code_with_tests_and_coverage(code_string: str, test_string: str, timeout: int = 15) -> dict:
    """
    Executes Python code and tests with pytest-cov for coverage metrics.
    Attempts Docker isolation first, falling back gracefully to process execution.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        code_file_path = os.path.join(temp_dir, "solution.py")
        test_file_path = os.path.join(temp_dir, "test_solution.py")

        with open(code_file_path, "w", encoding="utf-8") as f:
            f.write(code_string)

        full_test_content = "from solution import *\n\n" + test_string
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(full_test_content)

        # Try executing with Docker SDK if available
        try:
            import docker
            client = docker.from_env()
            
            # Mount temporary directory inside lightweight python container
            container_output = client.containers.run(
                image="python:3.11-slim",
                command="sh -c 'pip install pytest pytest-cov > /dev/null 2>&1 && pytest test_solution.py --cov=solution --cov-report=term-missing -v'",
                volumes={temp_dir: {'bind': '/app', 'mode': 'rw'}},
                working_dir="/app",
                network_mode="none",  # Prevent network access (Security)
                mem_limit="256m",     # Memory cap
                detach=False,
                remove=True,
                timeout=timeout
            )
            
            output_str = container_output.decode("utf-8").strip()
            return {
                "status": "success",
                "output": output_str,
                "execution_engine": "Docker Container (Isolated)",
                "error": None
            }

        except Exception as docker_err:
            # Fallback to local subprocess execution if Docker isn't running
            try:
                cmd = [
                    sys.executable, "-m", "pytest",
                    test_file_path,
                    "--cov=" + os.path.join(temp_dir, "solution"),
                    "--cov-report=term-missing",
                    "-v"
                ]
                
                result = subprocess.run(
                    cmd,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                if result.returncode == 0:
                    return {
                        "status": "success",
                        "output": result.stdout.strip(),
                        "execution_engine": "Local Subprocess (Fallback)",
                        "error": None
                    }
                else:
                    return {
                        "status": "failed",
                        "output": result.stdout.strip(),
                        "execution_engine": "Local Subprocess (Fallback)",
                        "error": result.stderr.strip() or result.stdout.strip()
                    }

            except subprocess.TimeoutExpired:
                return {
                    "status": "failed",
                    "output": "",
                    "execution_engine": "Local Subprocess",
                    "error": "Execution Timed Out (Possible infinite loop detected)."
                }