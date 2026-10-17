import os

import mssql_python
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables


def connect():
    """Open a connection to the AdventureWorksDW2022 database."""
    password = os.environ["MSSQL_SA_PASSWORD"]
    return mssql_python.connect(
        "Server=localhost,1433;"
        "Database=AdventureWorksDW2022;"
        "UID=sa;"
        f"PWD={password};"
        "Encrypt=yes;TrustServerCertificate=yes"
    )
