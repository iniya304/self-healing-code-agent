import streamlit as st
from agent_core import app as agent_app

st.set_page_config(
    page_title="Enterprise Self-Healing AI Platform",
    page_icon="🤖",
    layout="wide"
)

st.title("🛡️ Enterprise Self-Healing AI Code & Test Platform")
st.markdown("Powered by **LangGraph**, **Groq (Llama 3.1)**, **AST Analysis**, **Docker/Pytest Sandbox**, and **Code Coverage Metrics**.")

st.sidebar.header("Agent Execution Settings")
max_iters = st.sidebar.slider("Max Self-Healing Retries", min_value=1, max_value=5, value=3)

user_task = st.text_area(
    "Enter Code Task / Prompt:",
    height=100,
    placeholder="e.g., Write a function to check if two strings are anagrams and include tests for edge cases."
)

if st.button("🚀 Run Enterprise Autonomous Pipeline", type="primary"):
    if not user_task.strip():
        st.warning("Please enter a valid task description.")
    else:
        st.divider()
        initial_state = {
            "task": user_task,
            "generated_code": "",
            "generated_tests": "",
            "ast_valid": False,
            "execution_result": "",
            "execution_engine": "",
            "coverage_score": 0.0,
            "error_logs": [],
            "iteration_count": 0,
            "max_iterations": max_iters
        }

        status_box = st.status("Running Agentic State Machine...", expanded=True)
        with status_box:
            st.write("🔄 Invoking LLM Code & Test Generator...")
            st.write("🔍 Running AST Static Syntax Check...")
            st.write("⚡ Executing Pytest & Measuring Code Coverage...")
            final_output = agent_app.invoke(initial_state)
            status_box.update(label="✅ Agent Execution Flow Complete!", state="complete", expanded=False)

        # Metrics Row
        m1, m2, m3 = st.columns(3)
        m1.metric("Execution Engine", final_output.get("execution_engine", "N/A"))
        m2.metric("Code Coverage Score", f"{final_output.get('coverage_score', 0)}%")
        m3.metric("Healing Iterations", f"{final_output.get('iteration_count', 0)} / {max_iters}")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📜 Generated Solution Code")
            st.code(final_output.get("generated_code", ""), language="python")
            
            st.subheader("🧪 Auto-Generated Pytest Suite")
            st.code(final_output.get("generated_tests", ""), language="python")

        with col2:
            st.subheader("🎯 Pytest & Coverage Report")
            if final_output.get("execution_result"):
                st.success("All Unit Tests Passed!")
                st.code(final_output["execution_result"], language="text")
            else:
                st.error("Pipeline Failed / Coverage Threshold Not Met")
                if final_output.get("error_logs"):
                    st.code(final_output["error_logs"][-1], language="text")

        if final_output.get("error_logs"):
            with st.expander("⚠️ View Self-Healing Trail & Error Logs"):
                for idx, log in enumerate(final_output["error_logs"]):
                    st.error(f"Attempt {idx + 1} Log:\n{log}")