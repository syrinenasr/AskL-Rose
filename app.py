import streamlit as st
import pandas as pd

from ask import answer_question
from schema import get_schema, get_schema_text
from semantic import format_semantic_layer, load_semantic_layer

st.title("AskL-Rose")
st.caption("Ask the AdventureWorks data warehouse a question in plain English.")


@st.cache_data
def load_schema_text():
    """Load the schema text from the database once and reuse it for every question."""
    return get_schema_text(*get_schema())


@st.cache_data
def load_semantic_text():
    """Load the semantic layer one time and reuse it for every question."""
    return format_semantic_layer(load_semantic_layer())


def show_answer(answer):
    """Show one answer: the explanation, then the SQL and the result table if a query ran."""
    st.write(answer["explanation"])
    if answer["sql"]:
        with st.expander("SQL"):
            st.code(answer["sql"], language="sql")
        st.dataframe(answer["table"], hide_index=True)


if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.write(message["content"])
        elif "error" in message["content"]:
            st.error(message["content"]["error"])
        else:
            show_answer(message["content"])


question = st.chat_input("Ask a question about the data")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Writing SQL and running it..."):
                result = answer_question(question, load_schema_text(), load_semantic_text())
        except Exception as e:
            error = f"The query failed: {e}"
            st.error(error)
            st.session_state.messages.append({"role": "assistant", "content": {"error": error}})
            st.stop()
        answer = {
            "sql": result["sql"],
            "explanation": result["explanation"],
            "table": pd.DataFrame([list(row) for row in result["rows"]], columns=result["columns"]),
        }
        show_answer(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
        