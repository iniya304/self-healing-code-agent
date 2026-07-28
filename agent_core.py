import os
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from docker_sandbox import execute_code_locally

# Load environment variables
load_dotenv()

# 1. State Definition
class AgentState(TypedDict):
    task: str
    generated_code: str
    execution_result: str
    error_logs: List[str]
    iteration_count: int
    max_iterations: int

# Initialize LLM
llm = ChatGroq(
    model_name="llama-3.1-8b-instant",
    temperature=0.1
)

# 2. Generator Node
def generator_node(state: AgentState) -> AgentState:
    print(f"\n🔄 [Iteration {state['iteration_count'] + 1}] Generating/fixing code...")
    
    prompt = f"Task: {state['task']}\n\n"
    prompt += "Write clean, complete, executable Python code. Include print statements to display output."
    
    if state["error_logs"]:
        prompt += f"\n\n⚠️ PREVIOUS CODE FAILED WITH ERROR:\n{state['error_logs'][-1]}"
        prompt += "\n\nAnalyze the error above and write FIXED Python code."

    prompt += "\n\nReturn ONLY raw executable Python code inside ```python ``` blocks."

    response = llm.invoke([
        SystemMessage(content="You are an expert Python developer. Fix errors precisely when provided."),
        HumanMessage(content=prompt)
    ])
    
    raw = response.content
    code = raw.split("```python")[1].split("```")[0].strip() if "```python" in raw else raw.strip()
    
    state["generated_code"] = code
    state["iteration_count"] += 1
    return state

# 3. Execution Sandbox Node
def executor_node(state: AgentState) -> AgentState:
    print("⚡ Running code in Execution Sandbox...")
    code = state["generated_code"]
    
    res = execute_code_locally(code)
    
    if res["status"] == "success":
        print("✅ Execution Succeeded!")
        state["execution_result"] = res["output"]
    else:
        print(f"❌ Execution Failed: {res['error']}")
        state["error_logs"].append(res["error"])
        
    return state

# 4. Conditional Edge Decision Function
def decide_next_step(state: AgentState) -> str:
    if state["execution_result"]:
        return "end"
    if state["iteration_count"] >= state["max_iterations"]:
        print("\n🛑 Reached maximum iteration limit!")
        return "end"
    return "retry"

# 5. Build Graph
workflow = StateGraph(AgentState)

workflow.add_node("generator", generator_node)
workflow.add_node("executor", executor_node)

workflow.set_entry_point("generator")
workflow.add_edge("generator", "executor")

workflow.add_conditional_edges(
    "executor",
    decide_next_step,
    {
        "end": END,
        "retry": "generator"
    }
)

app = workflow.compile()

# Test with a intentionally tricky prompt or bug scenario
if __name__ == "__main__":
    test_task = "Write a function to divide numbers in a list [10, 5, 0, 2] by 2, but intentionally try dividing by zero first or handle ZeroDivisionError correctly."
    
    initial_state = {
        "task": test_task,
        "generated_code": "",
        "execution_result": "",
        "error_logs": [],
        "iteration_count": 0,
        "max_iterations": 3
    }
    
    final_output = app.invoke(initial_state)
    
    print("\n" + "="*50)
    print("🎯 FINAL EXECUTION OUTPUT:")
    print("="*50)
    print(final_output["execution_result"])
    print("\n📜 FINAL WORKING CODE:")
    print(final_output["generated_code"])