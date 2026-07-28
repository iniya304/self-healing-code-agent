import os
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

# Load environment variables from .env file
load_dotenv()

# 1. Define the Agent State
class AgentState(TypedDict):
    task: str
    generated_code: str
    error_logs: List[str]
    iteration_count: int

# 2. Initialize LLM (Groq Llama 3)
llm = ChatGroq(
    model_name="llama-3.1-8b-instant",
    temperature=0.1
)

# 3. Node 1: Code Generator
def code_generator_node(state: AgentState) -> AgentState:
    print(f"\n[AGENT] Generating code for task: '{state['task']}'...")
    
    prompt = f"""
    You are an expert Python developer. Write clean, executable Python code for the following task:
    Task: {state['task']}
    
    Return ONLY the executable Python code inside standard Python markdown code blocks (```python ... ```). Do not include conversational explanations.
    """
    
    if state["error_logs"]:
        prompt += f"\n\nPrevious Execution Error:\n{state['error_logs'][-1]}\nPlease fix this error in your new output."

    response = llm.invoke([
        SystemMessage(content="You generate production-ready Python code."),
        HumanMessage(content=prompt)
    ])
    
    state["generated_code"] = response.content
    state["iteration_count"] += 1
    return state

# 4. Node 2: Syntax & Code Extractor
def syntax_validator_node(state: AgentState) -> AgentState:
    print("[AGENT] Validating code format...")
    raw_output = state["generated_code"]
    
    if "```python" in raw_output:
        code = raw_output.split("```python")[1].split("```")[0].strip()
        state["generated_code"] = code
    elif "```" in raw_output:
        code = raw_output.split("```")[1].split("```")[0].strip()
        state["generated_code"] = code
        
    return state

# 5. Build the LangGraph State Machine Workflow
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("generator", code_generator_node)
workflow.add_node("validator", syntax_validator_node)

# Connect Edges
workflow.set_entry_point("generator")
workflow.add_edge("generator", "validator")
workflow.add_edge("validator", END)

# Compile Graph
agent_app = workflow.compile()

# 6. Test Run
if __name__ == "__main__":
    initial_state: AgentState = {
        "task": "Write a Python function that takes a list of numbers and returns the top 3 highest numbers.",
        "generated_code": "",
        "error_logs": [],
        "iteration_count": 0
    }
    
    result = agent_app.invoke(initial_state)
    
    print("\n" + "="*50)
    print("FINAL GENERATED CODE:")
    print("="*50)
    print(result["generated_code"]) 