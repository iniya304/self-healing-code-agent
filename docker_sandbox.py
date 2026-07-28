import subprocess
import sys
import tempfile
import os

def execute_code_locally(code_string: str, timeout: int = 5) -> dict:
    """
    Executes Python code in a safe temporary file environment and captures output or errors.
    """
    # Create a temporary python file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code_string)
        temp_file_path = temp_file.name

    try:
        # Run the temporary python script in a separate process
        result = subprocess.run(
            [sys.executable, temp_file_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Cleanup temporary file
        os.remove(temp_file_path)

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
                "error": result.stderr.strip()
            }

    except subprocess.TimeoutExpired:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return {
            "status": "failed",
            "output": "",
            "error": "Execution Timed Out (Infinite loop detected)."
        }
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return {
            "status": "error",
            "output": "",
            "error": str(e)
        }

# Quick Test
if __name__ == "__main__":
    test_code = """
numbers = [12, 45, 7, 23, 56, 89, 34]
print(sorted(numbers, reverse=True)[:3])
"""
    print("Testing Sandbox Executor...")
    exec_result = execute_code_locally(test_code)
    print("Execution Result:", exec_result)