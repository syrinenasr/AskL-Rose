# AskL-Rose

Ask a data warehouse questions in plain English. An LLM writes the T-SQL, the app checks it for safety, runs it read-only, and shows the results.

> 🚧 **Work in progress.** The database layer works today; the AI app is being built step by step (see the roadmap).

## What works now

One command starts **SQL Server 2022** in Docker and loads Microsoft's **AdventureWorksDW2022** sample data warehouse:

- `db`: SQL Server 2022 (Developer edition), with a health check that runs `SELECT 1`, and its data on a named volume so it survives restarts.
- `init`: a one-shot container that waits until `db` is healthy, downloads the AdventureWorksDW2022 backup, and restores it. It checks first, so running it again does nothing.

```
docker compose up -d
   ├─► db    SQL Server starts ──► healthy
   └─► init  waits for db ──► database exists? ──► no: download .bak ──► RESTORE ──► exits
```

AdventureWorksDW is a star schema for a fictional bike company: internet and reseller sales facts, with date, product, customer, geography and promotion dimensions.

## Run it

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```sh
git clone https://github.com/syrinenasr/AskL-Rose.git
cd AskL-Rose

cp .env.example .env   # then set your own password in .env
docker compose up -d
docker compose logs -f init   # wait for "Done."
```

The password must be at least 8 characters with uppercase, lowercase, a number and a symbol, or SQL Server won't start.

Connect with any SQL client (for example the SQL Server extension for VS Code):

| Setting | Value |
|---|---|
| Server | `localhost,1433` |
| Login | `sa` with the password from `.env` |
| Database | `AdventureWorksDW2022` |
| Trust server certificate | yes (local self-signed certificate) |

Try it:

```sql
SELECT COUNT(*) FROM FactInternetSales;   -- 60398
```

**Apple Silicon (M1/M2/M3):** SQL Server only ships for Intel, so it runs as `linux/amd64`. In Docker Desktop, turn on *Settings → General → Use Rosetta for x86_64/amd64 emulation on Apple Silicon*.

**Stop and reset:**

```sh
docker compose down      # stop; the database is kept in the volume
docker compose down -v   # stop and delete the data (the next "up" restores it again)
```

## Roadmap

- [x] SQL Server in Docker Compose with a volume and health check
- [x] Automatic restore of AdventureWorksDW2022
- [ ] Python app: read the schema and generate T-SQL with an LLM (Claude)
- [ ] Semantic layer: business definitions such as revenue, fiscal year and the order date
- [ ] Safety: only SELECT statements, a read-only login, row limits and timeouts
- [ ] Self-repair: send SQL errors back to the model once
- [ ] Evaluation: 50 test questions, scored by comparing query results
- [ ] Web interface and the app in its own container

## License note

SQL Server runs as the free Developer edition, licensed for development and testing only. AdventureWorksDW2022 comes from Microsoft's [sql-server-samples](https://github.com/microsoft/sql-server-samples) repository.
