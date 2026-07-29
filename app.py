import streamlit as st
from agent_core import app as agent_app

st.set_page_config(
    page_title="Enterprise Self-Healing AI Agent",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Enterprise Self-Healing Code & Test Agent")
st.markdown("Powered by **LangGraph**, **Groq (Llama 3.1)**, **AST Static Analysis**, and **Pytest Sandbox**.")

st.sidebar.header("Agent Settings")
max_iters = st.sidebar.slider("Max Self-Healing Retries", min_value=1, max_value=5, value=3)

user_task = st.text_area(
    "Enter Code Task / Prompt:",
    height=100,
    placeholder="e.g., Write a function to check if two strings are anagrams and write tests for edge cases."
)

if st.button("🚀 Execute Autonomous Pipeline", type="primary"):
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
            "error_logs": [],
            "iteration_count": 0,
            "max_iterations": max_iters
        }

        status_box = st.status("Running Agent State Machine...", expanded=True)
        with status_box:
            st.write("🔄 Invoking LLM Generator Node...")
            st.write("🔍 Running AST Static Code Analysis...")
            st.write("⚡ Executing Pytest Suite in Sandbox...")
            final_output = agent_app.invoke(initial_state)
            status_box.update(label="✅ Agent Execution Flow Finished!", state="complete", expanded=False)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📜 Solution Code")
            st.code(final_output.get("generated_code", ""), language="python")
            
            st.subheader("🧪 Auto-Generated Pytest Suite")
            st.code(final_output.get("generated_tests", ""), language="python")

        with col2:
            st.subheader("🎯 Pytest Execution Report")
            if final_output.get("execution_result"):
                st.success("All Unit Tests Passed!")
                st.code(final_output["execution_result"], language="text")
            else:
                st.error("Pipeline Failed / Max Retries Exceeded")
                if final_output.get("error_logs"):
                    st.code(final_output["error_logs"][-1], language="text")

        if len(final_output.get("error_logs", [])) > 0:
            with st.expander("⚠️ View Self-Healing Audit Trail Logs"):
                for idx, log in enumerate(final_output["error_logs"]):
                    st.error(f"Attempt {idx + 1} Error Traceback:\n{log}")