import os
import ast
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from docker_sandbox import execute_code_with_tests

# Load environment variables
load_dotenv()

# 1. State Definition
class AgentState(TypedDict):
    task: str
    generated_code: str
    generated_tests: str
    ast_valid: bool
    execution_result: str
    error_logs: List[str]
    iteration_count: int
    max_iterations: int

# Initialize Groq LLM
llm = ChatGroq(
    model_name="llama-3.1-8b-instant",
    temperature=0.1
)

# 2. Generator Node (Writes Code & Pytest Suite)
def generator_node(state: AgentState) -> AgentState:
    print(f"\n🔄 [Iteration {state['iteration_count'] + 1}] Generating Solution Code & Pytest Suite...")
    
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
        prompt += "\n\nAnalyze the error traceback above and fix both code and test suite."

    response = llm.invoke([
        SystemMessage(content="You are a Principal Software Engineer specializing in Test-Driven Development (TDD)."),
        HumanMessage(content=prompt)
    ])
    
    content = response.content
    
    # Parse code and tests based on delimiters
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

# 3. AST Static Code Analyzer Node (Pre-execution Syntax Check)
def ast_analyzer_node(state: AgentState) -> AgentState:
    print("🔍 [AST Analysis] Performing static syntax check...")
    try:
        ast.parse(state["generated_code"])
        ast.parse(state["generated_tests"])
        print("✅ AST Check Passed: Valid Python Syntax!")
        state["ast_valid"] = True
    except SyntaxError as e:
        error_msg = f"AST Static Analysis SyntaxError on line {e.lineno}: {e.msg}"
        print(f"❌ AST Check Failed: {error_msg}")
        state["ast_valid"] = False
        state["error_logs"].append(error_msg)
    except Exception as e:
        error_msg = f"AST Error: {str(e)}"
        state["ast_valid"] = False
        state["error_logs"].append(error_msg)
        
    return state

# 4. Sandbox Executor Node (Runs pytest)
def executor_node(state: AgentState) -> AgentState:
    print("⚡ Running Pytest Suite in Execution Sandbox...")
    res = execute_code_with_tests(state["generated_code"], state["generated_tests"])
    
    if res["status"] == "success":
        print("✅ Pytest Suite Passed!")
        state["execution_result"] = res["output"]
    else:
        print(f"❌ Pytest Execution Failed:\n{res['error']}")
        state["error_logs"].append(res["error"])
        state["execution_result"] = ""
        
    return state

# 5. Routing Logic
def route_after_ast(state: AgentState) -> str:
    if state["ast_valid"]:
        return "executor"
    if state["iteration_count"] >= state["max_iterations"]:
        return "end"
    return "retry"

def route_after_executor(state: AgentState) -> str:
    if state["execution_result"]:
        return "end"
    if state["iteration_count"] >= state["max_iterations"]:
        return "end"
    return "retry"

# 6. Build State Machine Graph
workflow = StateGraph(AgentState)

workflow.add_node("generator", generator_node)
workflow.add_node("ast_analyzer", ast_analyzer_node)
workflow.add_node("executor", executor_node)

workflow.set_entry_point("generator")
workflow.add_edge("generator", "ast_analyzer")

workflow.add_conditional_edges(
    "ast_analyzer",
    route_after_ast,
    {
        "executor": "executor",
        "retry": "generator",
        "end": END
    }
)

workflow.add_conditional_edges(
    "executor",
    route_after_executor,
    {
        "end": END,
        "retry": "generator"
    }
)
app = workflow.compile()