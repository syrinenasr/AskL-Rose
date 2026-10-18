from db import connect

REQ1 = """SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME LIKE 'Fact%' OR TABLE_NAME LIKE 'Dim%'
ORDER BY TABLE_NAME, ORDINAL_POSITION;"""

REQ2 = """SELECT  OBJECT_NAME(fk.parent_object_id), pc.name,
OBJECT_NAME(fk.referenced_object_id), rc.name
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.columns pc ON pc.object_id = fkc.parent_object_id AND pc.column_id = fkc.parent_column_id
JOIN sys.columns rc ON rc.object_id = fkc.referenced_object_id AND rc.column_id = fkc.referenced_column_id
ORDER BY 1,2;"""


def get_schema():
    """Read the warehouse schema: the column rows and the foreign-key rows."""
    conn = connect()
    cur = conn.cursor()
    cur.execute(REQ1)
    schema = cur.fetchall()
    cur.execute(REQ2)
    relationships = cur.fetchall()
    conn.close()
    return schema, relationships


def get_schema_text(schema, relationships):
    """Build the schema text for the LLM from the raw rows."""
    tables = group_schema_by_table(schema)
    relations = group_relations(relationships)
    return format_schema(tables, relations)


def group_schema_by_table(schema):
    """Group the (table, column, type) rows by table in a dictionary."""
    tables = {}
    for table, column, dtype in schema:
        tables.setdefault(table, []).append(f"{column} {dtype}")
    return tables


def group_relations(relationships):
    """Map each foreign-key column (Table.Column) to the column(s) it references."""
    relations = {}
    for table, column, ref_table, ref_column in relationships:
        relations.setdefault(f"{table}.{column}", []).append(f"{ref_table}.{ref_column}")
    return relations


def format_schema(tables, relations):
    """Return the schema as text: one line per table, then the relationships."""
    lines = [f"{table}({', '.join(cols)})" for table, cols in tables.items()]
    lines.append("\nRelationships:")
    lines.extend([f"{table_col} -> {', '.join(refs)}" for table_col, refs in relations.items()])
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_schema_text(*get_schema()))
