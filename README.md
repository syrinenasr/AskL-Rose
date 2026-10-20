# AskL-Rose

Ask a data warehouse questions in plain English. A local LLM writes the T-SQL, the app runs it on SQL Server and shows the results in a chat.

> 🚧 **Work in progress.** The chatbox works end to end today; safety checks, business definitions and an evaluation are next (see the roadmap).

## What works now

**A chatbox** (Streamlit) where you type a question and get the model's explanation, the SQL it wrote, and the result table. The conversation stays on screen, and a query that fails shows its SQL Server error instead of crashing.

```
question ──► schema text + question ──► local LLM (Ollama) writes T-SQL ──► SQL Server runs it ──► table
```

| File | Its job |
|---|---|
| `app.py` | the chatbox: shows questions, answers and errors |
| `ask.py` | `answer_question()`: question → SQL → columns and rows |
| `llm.py` | `generate_sql()`: sends the schema and the question to the model, gets back `{"sql", "explanation"}` as JSON |
| `schema.py` | reads the tables, columns and foreign keys, and formats them as text for the model |
| `db.py` | opens the connection to SQL Server |

The model runs **on your machine** with [Ollama](https://ollama.com): no data leaves it. The default is `qwen2.5-coder:7b`; set `OLLAMA_MODEL` to try another one.

**The database:** one command starts **SQL Server 2022** in Docker and loads Microsoft's **AdventureWorksDW2022** sample data warehouse:

- `db`: SQL Server 2022 (Developer edition), with a health check that runs `SELECT 1`, and its data on a named volume so it survives restarts.
- `init`: a one-shot container that waits until `db` is healthy, downloads the AdventureWorksDW2022 backup, and restores it. It checks first, so running it again does nothing.

```
docker compose up -d
   ├─► db    SQL Server starts ──► healthy
   └─► init  waits for db ──► database exists? ──► no: download .bak ──► RESTORE ──► exits
```

AdventureWorksDW is a star schema for a fictional bike company: internet and reseller sales facts, with date, product, customer, geography and promotion dimensions.

## Run it

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/), [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com).

### 1. The database

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

### 2. The model

```sh
ollama pull qwen2.5-coder:7b   # 4.7 GB
```

Ollama runs natively, not in Docker: on a Mac, Docker can't use the Apple GPU.

### 3. The chatbox

```sh
uv sync
uv run --env-file .env streamlit run app.py
```

It opens at `http://localhost:8501`. Try *"number of customers per country"* or *"total internet sales per calendar year"*.

To test without the web page: `uv run --env-file .env python ask.py`.

**Troubleshooting, macOS:** `OpenSSL library could not be loaded, make sure OpenSSL 1.0, 1.1, or 3.0 is installed` means Homebrew's `openssl` points to OpenSSL 4 (installing Ollama with Homebrew can do this), which the SQL Server driver doesn't support. Add this line to `.env` and start the app with `--env-file .env` as above:

```
DYLD_LIBRARY_PATH=/opt/homebrew/opt/openssl@3/lib
```

### Known limits

The 7B model guesses well on one or two tables but often fails on longer joins or business words. For example, *"how many bikes were sold in 2011"* produces a column that doesn't exist (`ProductName` instead of `EnglishProductName`), searches product names for "bike" instead of using the *Bikes* category, and counts order lines instead of quantities. The semantic layer and self-repair steps below are meant to fix this.

## Roadmap

- [x] SQL Server in Docker Compose with a volume and health check
- [x] Automatic restore of AdventureWorksDW2022
- [x] Python project with uv: connection to SQL Server and a schema reader
- [x] Local LLM (Ollama) writes T-SQL from the schema and the question
- [x] Web interface: Streamlit chatbox with conversation history
- [ ] Semantic layer: business definitions such as revenue, fiscal year and the order date
- [ ] Safety: only SELECT statements, a read-only login, row limits and timeouts
- [ ] Self-repair: send SQL errors back to the model once
- [ ] Evaluation: 50 test questions, scored by comparing query results; compare models
- [ ] The app in its own container

## License note

SQL Server runs as the free Developer edition, licensed for development and testing only. AdventureWorksDW2022 comes from Microsoft's [sql-server-samples](https://github.com/microsoft/sql-server-samples) repository.
