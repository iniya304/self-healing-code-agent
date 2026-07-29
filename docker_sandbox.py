import subprocess
import sys
import tempfile
import os

def execute_code_with_tests(code_string: str, test_string: str, timeout: int = 10) -> dict:
    """
    Executes Python code along with generated pytest unit tests in an isolated temporary directory.
    """
    # Create a temporary directory for code and test files
    with tempfile.TemporaryDirectory() as temp_dir:
        code_file_path = os.path.join(temp_dir, "solution.py")
        test_file_path = os.path.join(temp_dir, "test_solution.py")

        # Write code and tests to files
        with open(code_file_path, "w", encoding="utf-8") as f:
            f.write(code_string)

        # Prepend import statement so test file can import solution functions
        full_test_content = f"from solution import *\n\n" + test_string
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(full_test_content)

        try:
            # Run pytest in the temporary directory
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file_path, "-v"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                return {
                    "status": "success",
                    "output": result.stdout.strip(),
                    "error": None
                }
            else:
                return {
                    "status": "failed",
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() or result.stdout.strip()
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "failed",
                "output": "",
                "error": "Execution Timed Out (Possible infinite loop detected in test suite)."
            }
        except Exception as e:
            return {
                "status": "error",
                "output": "",
                "error": str(e)
            }

# Quick Test
if __name__ == "__main__":
    sample_code = """
def add_numbers(a, b):
    return a + b
"""
    sample_test = """
def test_add_numbers():
    assert add_numbers(2, 3) == 5
    assert add_numbers(-1, 1) == 0
"""
    print("Testing Sandbox with pytest...")
    res = execute_code_with_tests(sample_code, sample_test)
    print("Sandbox Result Status:", res["status"])
    print("Sandbox Output:\n", res["output"])