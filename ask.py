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
    If the SQL fails, the model gets its SQL and the error and tries once more (self-repair).
    """
    response = generate_sql(question, schema_text, semantic_text)
    sql = response["sql"].strip()
    if not response["is_data_question"] or not sql:
        return {"sql": "", "columns": [], "rows": [], "truncated": False, "repaired": False, "first_error": None, "explanation": response["explanation"]}
    first_error = None
    try:
        check_sql(sql)
        columns, rows, truncated = run_query(sql)
    except Exception as error:
        if "timeout" in str(error).lower():
            raise  # the query was valid, just slow: retrying would only make the user wait again
        first_error = str(error)
        response = generate_sql(question, schema_text, semantic_text, failed=(response, first_error))
        sql = response["sql"].strip()
        check_sql(sql)
        columns, rows, truncated = run_query(sql)  # no second retry: if this fails, the error goes to the app
    return {
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "truncated": truncated,
        "repaired": first_error is not None,
        "first_error": first_error,
        "explanation": response["explanation"],
    }


if __name__ == "__main__":
    from semantic import format_semantic_layer, load_semantic_layer

    schema_text = get_schema_text(*get_schema())
    semantic_text = format_semantic_layer(load_semantic_layer())
    question = "What are the first 10 customers?"
    print(answer_question(question, schema_text, semantic_text))
