# 🤖 Self-Healing Agentic Code Execution Platform

An autonomous AI platform powered by **LangGraph**, **Groq (Llama 3.1)**, and **Streamlit** that generates Python code, runs it in an isolated execution sandbox, catches runtime errors, and automatically self-heals its code in a recursive loop.

---

## 🌟 Key Features
- **Autonomous Error Repair:** Captures standard output & stack traces; automatically feeds errors back to LLM for patching.
- **State Machine Architecture:** Built with **LangGraph** state graph nodes for deterministic agent workflow management.
- **Execution Sandbox:** Runs user/LLM Python scripts safely in temporary isolated environments.
- **Interactive UI:** Real-time state progress, syntax highlighting, and execution logs powered by **Streamlit**.

---

## 🛠️ Architecture
1. **User Request** ➔ Submitted via Streamlit UI.
2. **LLM Code Generator Node** ➔ Generates executable Python code using Groq API.
3. **Execution Sandbox Node** ➔ Executes script and checks exit codes/errors.
4. **Conditional Router Node** ➔ If success, returns output; if error, routes traceback back to Generator for self-healing repair.

---

## 🚀 Quickstart

```bash
# Clone Repository
git clone [https://github.com/iniya304/self-healing-code-agent.git](https://github.com/iniya304/self-healing-code-agent.git)
cd self-healing-code-agent

# Create & Activate Virtual Environment
python -m venv venv
venv\Scripts\activate

# Install Dependencies
pip install -r requirements.txt

# Configure Environment Variables
# Create a .env file and add:
GROQ_API_KEY=your_groq_api_key_here

# Run Dashboard
streamlit run app.py
