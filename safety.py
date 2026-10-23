import sqlglot
from sqlglot import exp


def check_sql(sql):
    """Raise a ValueError unless the SQL is one read-only SELECT statement."""
    try:
        statements = sqlglot.parse(sql, read="tsql")
    except sqlglot.errors.ParseError as error:
        raise ValueError(f"The SQL couldn't be read: {error}") from error
    statements = [s for s in statements if s is not None]  # a trailing ";" gives an empty statement

    if len(statements) != 1:
        raise ValueError("Only a single SELECT statement is allowed.")
    statement = statements[0]
    if not isinstance(statement, (exp.Select, exp.Union)):
        raise ValueError(f"Only SELECT statements are allowed, not {statement.key.upper()}.")
    if statement.find(exp.Into):
        raise ValueError("SELECT ... INTO creates a table, so it isn't allowed.")


if __name__ == "__main__":
    tests = [
        ("SELECT TOP 5 * FROM DimProduct", True),
        ("SELECT TOP 5 * FROM DimProduct;", True),
        ("WITH x AS (SELECT 1 AS a) SELECT a FROM x", True),
        ("SELECT 1 UNION SELECT 2", True),
        ("SELECT * INTO NewT FROM DimProduct", False),
        ("DROP TABLE DimProduct", False),
        ("SELECT 1; DELETE FROM DimProduct", False),
        ("EXEC sp_who", False),
        ("UPDATE DimProduct SET Color = NULL", False),
        ("", False),
    ]
    for sql, should_pass in tests:
        try:
            check_sql(sql)
            result = "allowed"
        except ValueError as error:
            result = f"rejected ({error})"
        ok = "✅" if (result == "allowed") == should_pass else "❌ WRONG"
        print(f"{ok} {sql!r}: {result}")
