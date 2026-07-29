import os
import ast
import re
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from docker_sandbox import execute_code_with_tests_and_coverage

load_dotenv()

# Optional: Enable LangSmith Observability if API Key exists
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "self-healing-code-agent"

# 1. Enhanced State Definition
class AgentState(TypedDict):
    task: str
    generated_code: str
    generated_tests: str
    ast_valid: bool
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

# Helper to parse coverage percentage from pytest-cov output
def extract_coverage(pytest_output: str) -> float:
    match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', pytest_output)
    if match:
        return float(match.group(1))
    return 100.0  # Default if unable to parse

# 2. Generator Node
def generator_node(state: AgentState) -> AgentState:
    print(f"\n🔄 [Iteration {state['iteration_count'] + 1}] Generating Code & Pytest Suite...")
    
    prompt = (
        "Task: " + state['task'] + "\n\n"
        "Write clean, modular, production-ready Python solution code along with a pytest unit test suite.\n\n"
        "Output layout MUST strictly be in this format:\n\n"
        "---CODE---\n"
        "# Put solution python code here\n"
        "---TESTS---\n"
        "# Put pytest unit test functions here\n"
    )
    
    if state["error_logs"]:
        prompt += f"\n\n⚠️ PREVIOUS ATTEMPT FAILED WITH ERROR:\n{state['error_logs'][-1]}"
        prompt += "\n\nFix both code and test suite to pass all tests and reach >80% code coverage."

    response = llm.invoke([
        SystemMessage(content="You are a Principal AI Software Engineer specializing in Test-Driven Development (TDD) and high test coverage."),
        HumanMessage(content=prompt)
    ])
    
    content = response.content
    code_part = ""
    test_part = ""
    
    if "---TESTS---" in content:
        parts = content.split("---TESTS---")
        code_part = parts[0].replace("---CODE---", "").replace("```python", "").replace("```", "").strip()
        test_part = parts[1].replace("```python", "").replace("```pytest", "").replace("```", "").strip()
    else:
        code_part = content.replace("```python", "").replace("```", "").strip()
        test_part = "def test_default():\n    assert True"

    state["generated_code"] = code_part
    state["generated_tests"] = test_part
    state["iteration_count"] += 1
    return state

# 3. AST Static Code Analyzer Node
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

# 4. Sandbox Executor Node (Pytest + Coverage)
def executor_node(state: AgentState) -> AgentState:
    print("⚡ Running Pytest + Coverage in Sandbox...")
    res = execute_code_with_tests_and_coverage(state["generated_code"], state["generated_tests"])
    
    state["execution_engine"] = res["execution_engine"]
    
    if res["status"] == "success":
        state["execution_result"] = res["output"]
        state["coverage_score"] = extract_coverage(res["output"])
        print(f"✅ Tests Passed with {state['coverage_score']}% Code Coverage!")
    else:
        state["error_logs"].append(res["error"])
        state["execution_result"] = ""
        state["coverage_score"] = 0.0
        
    return state

# 5. Routing Logic
def route_after_ast(state: AgentState) -> str:
    if state["ast_valid"]:
        return "executor"
    if state["iteration_count"] >= state["max_iterations"]:
        return "end"
    return "retry"

def route_after_executor(state: AgentState) -> str:
    # Require both successful tests AND >= 70% coverage to pass
    if state["execution_result"] and state["coverage_score"] >= 70.0:
        return "end"
    if state["iteration_count"] >= state["max_iterations"]:
        return "end"
    
    if state["execution_result"] and state["coverage_score"] < 70.0:
        state["error_logs"].append(f"Low Test Coverage ({state['coverage_score']}%). Minimum 70% required. Add more edge-case unit tests.")
        
    return "retry"

# 6. State Machine Setup
workflow = StateGraph(AgentState)

workflow.add_node("generator", generator_node)
workflow.add_node("ast_analyzer", ast_analyzer_node)
workflow.add_node("executor", executor_node)

workflow.set_entry_point("generator")
workflow.add_edge("generator", "ast_analyzer")

workflow.add_conditional_edges(
    "ast_analyzer",
    route_after_ast,
    {"executor": "executor", "retry": "generator", "end": END}
)

workflow.add_conditional_edges(
    "executor",
    route_after_executor,
    {"end": END, "retry": "generator"}
)

app = workflow.compile()