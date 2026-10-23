import os

import mssql_python
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables


def connect():
    """Open a read-only connection to the AdventureWorksDW2022 database.

    The app logs in as askl_reader, which can read every table and change nothing.
    The admin login (sa) is only used by the restore script.
    """
    password = os.environ["APP_DB_PASSWORD"]
    return mssql_python.connect(
        "Server=localhost,1433;"
        "Database=AdventureWorksDW2022;"
        "UID=askl_reader;"
        f"PWD={password};"
        "Encrypt=yes;TrustServerCertificate=yes"
    )
