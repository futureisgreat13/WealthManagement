import streamlit as st
import sys, json
from pathlib import Path
from datetime import datetime
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))
import utils

TODOS_PATH = utils.DATA_DIR / "todos.json"

st.title("📝 To Do")
st.caption("Task management with AI analysis support.")
st.markdown('<style>div[data-testid="stMetric"]{padding:8px 0}div[data-testid="stExpander"] summary{padding:4px 0}</style>', unsafe_allow_html=True)


def load_todos():
    return utils.load_json(TODOS_PATH, [])


def save_todos(todos):
    utils.save_json(TODOS_PATH, todos)


# --- Add new task ---
new_desc = st.text_area("New task description", key="todo_new_desc", height=80)
if st.button("Add Task", type="primary", key="todo_add_btn"):
    if new_desc.strip():
        todos = load_todos()
        todos.append({
            "id": str(uuid.uuid4()),
            "description": new_desc.strip(),
            "status": "pending",
            "ai_response": "",
            "approved": False,
            "created": datetime.now().isoformat(),
        })
        save_todos(todos)
        st.success("Task added!")
        st.rerun()
    else:
        st.warning("Please enter a task description.")

st.divider()

# --- Clear completed ---
todos = load_todos()
completed_count = sum(1 for t in todos if t["status"] == "completed")
if completed_count > 0:
    if st.button(f"Clear Completed ({completed_count})", key="todo_clear_completed"):
        todos = [t for t in todos if t["status"] != "completed"]
        save_todos(todos)
        st.rerun()

# --- Group tasks by status ---
STATUS_ORDER = ["pending", "in_progress", "completed"]
STATUS_LABELS = {"pending": "⏳ Pending", "in_progress": "🔄 In Progress", "completed": "✅ Completed"}

grouped = {s: [] for s in STATUS_ORDER}
for t in todos:
    grouped.get(t["status"], grouped["pending"]).append(t)

for status in STATUS_ORDER:
    tasks = grouped[status]
    if not tasks:
        continue
    st.subheader(STATUS_LABELS[status])
    for task in tasks:
        tid = task["id"]
        with st.expander(f"{task['description'][:80]}{'…' if len(task['description']) > 80 else ''}", expanded=(status != "completed")):
            st.markdown(f"**Description:**\n\n{task['description']}")
            st.caption(f"Created: {task['created'][:19]}  |  Approved for AI: {'Yes' if task.get('approved') else 'No'}")

            ai_val = st.text_area(
                "AI Analysis",
                value=task.get("ai_response", ""),
                key=f"todo_ai_{tid}",
                height=100,
            )

            # Save AI response if changed
            if ai_val != task.get("ai_response", ""):
                current_todos = load_todos()
                for ct in current_todos:
                    if ct["id"] == tid:
                        ct["ai_response"] = ai_val
                        break
                save_todos(current_todos)

            cols = st.columns(4)
            with cols[0]:
                if status != "in_progress" and st.button("▶ Mark In Progress", key=f"todo_ip_{tid}"):
                    current_todos = load_todos()
                    for ct in current_todos:
                        if ct["id"] == tid:
                            ct["status"] = "in_progress"
                            break
                    save_todos(current_todos)
                    st.rerun()
            with cols[1]:
                if status != "completed" and st.button("✅ Mark Done", key=f"todo_done_{tid}"):
                    current_todos = load_todos()
                    for ct in current_todos:
                        if ct["id"] == tid:
                            ct["status"] = "completed"
                            break
                    save_todos(current_todos)
                    st.rerun()
            with cols[2]:
                if not task.get("approved") and st.button("🤖 Approve for AI Execution", key=f"todo_approve_{tid}"):
                    current_todos = load_todos()
                    for ct in current_todos:
                        if ct["id"] == tid:
                            ct["approved"] = True
                            break
                    save_todos(current_todos)
                    st.rerun()
            with cols[3]:
                if st.button("🗑 Delete", key=f"todo_del_{tid}"):
                    current_todos = load_todos()
                    current_todos = [ct for ct in current_todos if ct["id"] != tid]
                    save_todos(current_todos)
                    st.rerun()
