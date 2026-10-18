import json
import os

import ollama

MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")

SYSTEM_PROMPT = """You write T-SQL queries for Microsoft SQL Server.
Use only the tables and columns listed in the schema.
Join tables using the relationships listed in the schema.
Write a single SELECT statement. Never modify data."""

# The shape of the answer we require from the model (a JSON schema).
ANSWER_FORMAT = {
    "type": "object",
    "properties": {
        "sql": {"type": "string"},
        "explanation": {"type": "string"},
    },
    "required": ["sql", "explanation"],
}


def generate_sql(question, schema_text):
    """Ask the local LLM to write T-SQL for a question. Returns {"sql": ..., "explanation": ...}."""
    response = ollama.chat(
        model=MODEL,
        messages=[  
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Schema:\n{schema_text}\n\nQuestion: {question}"},
        ],
        format=ANSWER_FORMAT,
        options={"temperature": 0},
    )
    return json.loads(response.message.content)


if __name__ == "__main__":
    from schema import get_schema, get_schema_text

    answer = generate_sql("total internet sales per calendar year", get_schema_text(*get_schema()))
    print(answer["sql"])
    print()
    print(answer["explanation"])
