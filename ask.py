from db import connect
from llm import generate_sql
from schema import get_schema, get_schema_text
from safety import check_sql

MAX_ROWS = 1000       # rows shown in the chatbox
QUERY_TIMEOUT = 30    # seconds before a query is stopped


def run_query(query):
    """Run a query and return the columns, at most MAX_ROWS rows, and whether rows were cut off."""
    conn = connect()
    conn.timeout = QUERY_TIMEOUT
    cur = conn.cursor()
    cur.execute(query)
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchmany(MAX_ROWS + 1)  # one extra row tells us if there were more
    conn.close()
    truncated = len(rows) > MAX_ROWS
    return columns, rows[:MAX_ROWS], truncated


def answer_question(question, schema_text, semantic_text):
    """Turn a question into SQL, run it, and return the SQL, explanation, columns and rows.

    For a message that isn't a data question (like "Hi"), no query runs: sql is empty and there are no rows.
    """
    response = generate_sql(question, schema_text, semantic_text)
    sql = response["sql"].strip()
    if not response["is_data_question"] or not sql:
        return {"sql": "", "columns": [], "rows": [], "truncated": False, "explanation": response["explanation"]}
    check_sql(sql)
    columns, rows, truncated = run_query(sql)
    return {
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "truncated": truncated,
        "explanation": response["explanation"],
    }


if __name__ == "__main__":
    from semantic import format_semantic_layer, load_semantic_layer

    schema_text = get_schema_text(*get_schema())
    semantic_text = format_semantic_layer(load_semantic_layer())
    question = "What are the first 10 customers?"
    print(answer_question(question, schema_text, semantic_text))
