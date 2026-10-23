import json
import os

import ollama

MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")

SYSTEM_PROMPT = """You write T-SQL queries for Microsoft SQL Server.
Use only the tables and columns listed in the schema.
Join tables using the relationships listed in the schema.
Write a single SELECT statement. Never modify data.
When the question uses a business term or metric from the business definitions, use that definition exactly.
If the message is not a question about the data (a greeting, small talk, or something this warehouse can't answer),
set is_data_question to false, leave sql empty, and reply briefly in the explanation with an example question."""

# Sent after a query fails, together with the model's own failed answer.
REPAIR_PROMPT = """That SQL failed with this error:
{error}

Fix the query. Use only the tables and columns listed in the schema, and the business definitions.
Answer in the same JSON format, with the corrected SQL."""

# The shape of the answer we require from the model (a JSON schema).
ANSWER_FORMAT = {
    "type": "object",
    "properties": {
        "is_data_question": {"type": "boolean"},  # first, so the model decides before it writes SQL
        "sql": {"type": "string"},
        "explanation": {"type": "string"},
    },
    "required": ["is_data_question", "sql", "explanation"],
}


def generate_sql(question, schema_text, semantic_text, failed=None):
    """Ask the local LLM to write T-SQL for a question. Returns {"is_data_question": ..., "sql": ..., "explanation": ...}.

    For a repair, failed is (previous_answer, error): the model sees its own answer and the error, and fixes the SQL.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Schema:\n{schema_text}\n\nBusiness definitions:\n{semantic_text}\n\nQuestion: {question}"},
    ]
    if failed:
        previous_answer, error = failed
        messages.append({"role": "assistant", "content": json.dumps(previous_answer)})
        messages.append({"role": "user", "content": REPAIR_PROMPT.format(error=error)})
    response = ollama.chat(
        model=MODEL,
        messages=messages,
        format=ANSWER_FORMAT,
        options={"temperature": 0},
    )
    return json.loads(response.message.content)


if __name__ == "__main__":
    from schema import get_schema, get_schema_text
    from semantic import format_semantic_layer, load_semantic_layer

    schema_text = get_schema_text(*get_schema())
    semantic_text = format_semantic_layer(load_semantic_layer())
    answer = generate_sql("total internet sales per calendar year", schema_text, semantic_text)
    print(answer["sql"])
    print()
    print(answer["explanation"])
