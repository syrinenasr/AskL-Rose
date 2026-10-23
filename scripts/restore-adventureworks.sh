#!/bin/bash
# Restores AdventureWorksDW2022 into the "db" service, once,
# then makes sure the app's read-only login exists (every run, safe to repeat).
set -euo pipefail   # stop at the first error, treat unset variables as errors

SQLCMD="/opt/mssql-tools18/bin/sqlcmd -S db -U sa -P $MSSQL_SA_PASSWORD -C -b"
BAK=/var/opt/mssql/backup/AdventureWorksDW2022.bak
URL=https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorksDW2022.bak

# 1. Already restored? Then skip the download and restore.
EXISTS=$($SQLCMD -h -1 -Q "SET NOCOUNT ON; SELECT COUNT(*) FROM sys.databases WHERE name = 'AdventureWorksDW2022'" | tr -d '[:space:]')
if [ "$EXISTS" = "1" ]; then
  echo "AdventureWorksDW2022 already exists. Skipping the restore."
else
  # 2. Download the backup if it isn't in the volume yet.
  if [ ! -f "$BAK" ]; then
    echo "Downloading AdventureWorksDW2022.bak..."
    mkdir -p "$(dirname "$BAK")"
    wget -q -O "$BAK" "$URL"
  fi

  # 3. Restore it, moving the files to Linux paths.
  echo "Restoring AdventureWorksDW2022..."
  $SQLCMD -Q "RESTORE DATABASE AdventureWorksDW2022 FROM DISK = '$BAK' WITH
    MOVE 'AdventureWorksDW2022' TO '/var/opt/mssql/data/AdventureWorksDW2022.mdf',
    MOVE 'AdventureWorksDW2022_log' TO '/var/opt/mssql/data/AdventureWorksDW2022_log.ldf'"
fi

# 4. The app's login: it can read every table and change nothing (db_datareader).
#    Created if missing; its password is updated to the one in .env.
echo "Setting up the read-only login askl_reader..."
$SQLCMD -Q "
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'askl_reader')
  CREATE LOGIN askl_reader WITH PASSWORD = '$APP_DB_PASSWORD', DEFAULT_DATABASE = AdventureWorksDW2022;
ELSE
  ALTER LOGIN askl_reader WITH PASSWORD = '$APP_DB_PASSWORD';"
$SQLCMD -d AdventureWorksDW2022 -Q "
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'askl_reader')
  CREATE USER askl_reader FOR LOGIN askl_reader;
ALTER ROLE db_datareader ADD MEMBER askl_reader;"
echo "Done."
