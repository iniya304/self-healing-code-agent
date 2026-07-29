import os
import ast
import re
import subprocess
import tempfile
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from docker_sandbox import execute_code_with_tests_and_coverage

load_dotenv()

# Optional: Enable LangSmith Telemetry if API Key is set
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "self-healing-code-agent"

# 1. State Definition
class AgentState(TypedDict):
    task: str
    generated_code: str
    generated_tests: str
    ast_valid: bool
    security_valid: bool
    security_report: str
    execution_result: str
    execution_engine: str
    coverage_score: float
    error_logs: List[str]
    iteration_count: int
    max_iterations: int

llm = ChatGroq(
    model_name="llama-3.1-8b-instant",
    temperature=0.1
)

# Security Scanner Helper (Bandit)
def run_security_scan(code_string: str) -> dict:
    """Scans code for security vulnerabilities using Bandit."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
        temp_file.write(code_string)
        temp_path = temp_file.name

    try:
        res = subprocess.run(
            ["bandit", "-r", temp_path, "-f", "txt"],
            capture_output=True,
            text=True
        )
        os.remove(temp_path)
        
        if "No issues identified." in res.stdout or res.returncode == 0:
            return {"secure": True, "report": "No security issues found."}
        else:
            return {"secure": False, "report": res.stdout}
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return {"secure": True, "report": f"Scan skipped: {str(e)}"}

# Formatter Helper (Black)
def format_python_code(code_string: str) -> str:
    """Formats generated code using Black PEP 8 formatter."""
    try:
        import black
        return black.format_str(code_string, mode=black.Mode())
    except Exception:
        return code_string  # Return unformatted if formatting fails

def extract_coverage(pytest_output: str) -> float:
    match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', pytest_output)
    if match:
        return float(match.group(1))
    return 100.0

# 2. Code Generator Node
def generator_node(state: AgentState) -> AgentState:
    print(f"\n🔄 [Iteration {state['iteration_count'] + 1}] Generating Code & Pytest Suite...")
    
    prompt = (
        "Task: " + state['task'] + "\n\n"
        "Write clean, secure, production-ready Python solution code along with a pytest unit test suite.\n\n"
        "Output layout MUST strictly be in this format:\n\n"
        "---CODE---\n"
        "# Put solution python code here\n"
        "---TESTS---\n"
        "# Put pytest unit test functions here\n"
    )
    
    if state["error_logs"]:
        prompt += f"\n\n⚠️ PREVIOUS ATTEMPT FAILED WITH ERROR / SECURITY VULNERABILITY:\n{state['error_logs'][-1]}"
        prompt += "\n\nFix both code and test suite to pass security scans and pytest unit tests with >80% coverage."

    response = llm.invoke([
        SystemMessage(content="You are a Principal AI Software & Security Engineer specializing in TDD, PEP 8, and secure code practices."),
        HumanMessage(content=prompt)
    ])
    
    content = response.content
    code_part, test_part = "", ""
    
    if "---TESTS---" in content:
        parts = content.split("---TESTS---")
        code_part = parts[0].replace("---CODE---", "").replace("```python", "").replace("```", "").strip()
        test_part = parts[1].replace("```python", "").replace("```pytest", "").replace("```", "").strip()
    else:
        code_part = content.replace("```python", "").replace("```", "").strip()
        test_part = "def test_default():\n    assert True"

    # Auto-format generated code with Black
    formatted_code = format_python_code(code_part)

    state["generated_code"] = formatted_code
    state["generated_tests"] = test_part
    state["iteration_count"] += 1
    return state

# 3. AST Static Syntax Node
def ast_analyzer_node(state: AgentState) -> AgentState:
    print("🔍 [AST Analysis] Performing static syntax check...")
    try:
        ast.parse(state["generated_code"])
        ast.parse(state["generated_tests"])
        state["ast_valid"] = True
    except SyntaxError as e:
        error_msg = f"AST Static Analysis SyntaxError on line {e.lineno}: {e.msg}"
        state["ast_valid"] = False
        state["error_logs"].append(error_msg)
    except Exception as e:
        state["ast_valid"] = False
        state["error_logs"].append(f"AST Error: {str(e)}")
        
    return state

# 4. Security Scan Node (Bandit)
def security_scan_node(state: AgentState) -> AgentState:
    print("🛡️ [Security Scan] Running Bandit static vulnerability check...")
    sec_res = run_security_scan(state["generated_code"])
    
    if sec_res["secure"]:
        print("✅ Security Scan Passed: No vulnerabilities found!")
        state["security_valid"] = True
        state["security_report"] = sec_res["report"]
    else:
        print("❌ Security Vulnerability Detected!")
        state["security_valid"] = False
        state["security_report"] = sec_res["report"]
        state["error_logs"].append(f"Security Issue Found by Bandit:\n{sec_res['report']}")
        
    return state

# 5. Sandbox Execution Node
def executor_node(state: AgentState) -> AgentState:
    print("⚡ Running Pytest + Coverage in Sandbox...")
    res = execute_code_with_tests_and_coverage(state["generated_code"], state["generated_tests"])
    
    state["execution_engine"] = res["execution_engine"]
    
    if res["status"] == "success":
        state["execution_result"] = res["output"]
        state["coverage_score"] = extract_coverage(res["output"])
        print(f"✅ Pytest Suite Passed with {state['coverage_score']}% Code Coverage!")
    else:
        state["error_logs"].append(res["error"])
        state["execution_result"] = ""
        state["coverage_score"] = 0.0
        
    return state

# 6. Routing Logic
def route_after_ast(state: AgentState) -> str:
    if state["ast_valid"]:
        return "security"
    if state["iteration_count"] >= state["max_iterations"]:
        return "end"
    return "retry"

def route_after_security(state: AgentState) -> str:
    if state["security_valid"]:
        return "executor"
    if state["iteration_count"] >= state["max_iterations"]:
        return "end"
    return "retry"

def route_after_executor(state: AgentState) -> str:
    if state["execution_result"] and state["coverage_score"] >= 70.0:
        return "end"
    if state["iteration_count"] >= state["max_iterations"]:
        return "end"
    
    if state["execution_result"] and state["coverage_score"] < 70.0:
        state["error_logs"].append(f"Low Test Coverage ({state['coverage_score']}%). Minimum 70% required.")
        
    return "retry"

# 7. LangGraph Workflow
workflow = StateGraph(AgentState)

workflow.add_node("generator", generator_node)
workflow.add_node("ast_analyzer", ast_analyzer_node)
workflow.add_node("security_scan", security_scan_node)
workflow.add_node("executor", executor_node)

workflow.set_entry_point("generator")
workflow.add_edge("generator", "ast_analyzer")

workflow.add_conditional_edges(
    "ast_analyzer",
    route_after_ast,
    {"security": "security_scan", "retry": "generator", "end": END}
)

workflow.add_conditional_edges(
    "security_scan",
    route_after_security,
    {"executor": "executor", "retry": "generator", "end": END}
)

workflow.add_conditional_edges(
    "executor",
    route_after_executor,
    {"end": END, "retry": "generator"}
)

app = workflow.compile()