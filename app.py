import streamlit as st
import time
from agent_core import app as agent_app

# Page Configuration
st.set_page_config(
    page_title="Self-Healing AI Agent",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Self-Healing Code Execution Agent")
st.markdown("An autonomous AI agent powered by **LangGraph** & **Groq** that writes, executes, tests, and auto-corrects Python code in a sandbox.")

st.sidebar.header("Configuration")
max_iters = st.sidebar.slider("Maximum Self-Healing Iterations", min_value=1, max_value=5, value=3)

# User Input Task
user_task = st.text_area(
    "Enter Code Task / Prompt:",
    height=100,
    placeholder="e.g., Write a function that calculates fibonacci numbers and print the top 10 values."
)

if st.button("🚀 Run Agent Pipeline", type="primary"):
    if not user_task.strip():
        st.warning("Please enter a valid prompt task first.")
    else:
        st.divider()
        st.subheader("⚙️ Agent Execution Graph Output")
        
        # Prepare Initial Agent State
        initial_state = {
            "task": user_task,
            "generated_code": "",
            "execution_result": "",
            "error_logs": [],
            "iteration_count": 0,
            "max_iterations": max_iters
        }

        status_container = st.status("Initializing Agent Flow...", expanded=True)
        
        # Stream or Run Graph
        with status_container:
            st.write("🔄 Invoking LLM Generator & Execution Sandbox...")
            final_output = agent_app.invoke(initial_state)
            status_container.update(label="✅ Pipeline Execution Complete!", state="complete", expanded=False)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📜 Final Generated & Repaired Code")
            st.code(final_output.get("generated_code", ""), language="python")

        with col2:
            st.markdown("### 🎯 Execution Output")
            if final_output.get("execution_result"):
                st.success("Execution Successful!")
                st.code(final_output["execution_result"], language="text")
            else:
                st.error("Execution Failed / Limit Reached")
                if final_output.get("error_logs"):
                    st.code(final_output["error_logs"][-1], language="text")

        # Show Error Log Timeline if retries happened
        if len(final_output.get("error_logs", [])) > 0:
            with st.expander("⚠️ View Self-Healing Retry Logs"):
                for idx, log in enumerate(final_output["error_logs"]):
                    st.error(f"Attempt {idx + 1} Error:\n{log}")
                    