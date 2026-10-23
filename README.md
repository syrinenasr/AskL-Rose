# AskL-Rose

Ask a data warehouse questions in plain English. A local LLM writes the T-SQL, the app runs it on SQL Server and shows the results in a chat.

> 🚧 **Work in progress.** The chatbox and the semantic layer work end to end today; safety checks, self-repair and an evaluation are next (see the roadmap).

## What works now

**A chatbox** (Streamlit) where you type a question and get the model's explanation, the SQL it wrote, and the result table. The conversation stays on screen, and a query that fails shows its SQL Server error instead of crashing.

```
question ──► schema + business definitions + question ──► local LLM (Ollama) writes T-SQL ──► SQL Server runs it ──► table
```

| File | Its job |
|---|---|
| `app.py` | the chatbox: shows questions, answers and errors |
| `ask.py` | `answer_question()`: question → SQL → columns and rows |
| `llm.py` | `generate_sql()`: sends the schema, the business definitions and the question to the model, gets back `{"sql", "explanation"}` as JSON |
| `schema.py` | reads the tables, columns and foreign keys, and formats them as text for the model |
| `semantic_layer.yaml` | the semantic layer: business definitions of metrics, terms and rules (see below) |
| `semantic.py` | reads `semantic_layer.yaml` and formats it as text for the model |
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

## The semantic layer

The schema tells the model which tables and columns exist, but not what the business words mean. Without that, it guesses. `semantic_layer.yaml` gives it **one trusted definition of each metric and business term**, the same idea as the dbt Semantic Layer or Power BI measures, so people and the AI use the same definitions.

It has three sections:

| Section | What it defines | Examples |
|---|---|---|
| `metrics` | things you measure | units sold = `SUM(OrderQuantity)`; number of orders = `COUNT(DISTINCT SalesOrderNumber)`; revenue, gross profit, customers |
| `terms` | business words, with the joins to reach them | *bikes* is the product category `Bikes` (product → subcategory → category); *in 2011* is `DimDate.CalendarYear` through `OrderDateKey`; country goes through the customer |
| `rules` | facts the model kept getting wrong | "sales" without a channel means internet sales; there is no `ProductName` column; sort results that are per year or per month |

Each entry has a `name` and its `sql`, plus optional `synonyms`, `joins` and `notes`:

```yaml
terms:
  - name: product category
    synonyms: [bikes, bike, bicycles, components, clothing, accessories, category]
    sql: DimProductCategory.EnglishProductCategoryName = 'Bikes'  (or 'Components', 'Clothing', 'Accessories')
    joins: FactInternetSales.ProductKey -> DimProduct.ProductKey; DimProduct.ProductSubcategoryKey -> DimProductSubcategory.ProductSubcategoryKey; DimProductSubcategory.ProductCategoryKey -> DimProductCategory.ProductCategoryKey
    notes: Bikes, Components, Clothing and Accessories are categories. Never search product names for "bike".
```

Every table, column and value in the file was checked against the database. To add a definition, add an entry to the YAML file and restart the app.

### Before and after

Same model (`qwen2.5-coder:7b`), same question, temperature 0: **"how many bikes were sold in 2011"**.

**Before, with the schema only:** SQL Server rejects the query.

```sql
SELECT COUNT(*) FROM FactInternetSales AS fis
JOIN DimProduct AS dp ON fis.ProductKey = dp.ProductKey
WHERE dp.ProductName LIKE '%bike%'
  AND fis.OrderDateKey BETWEEN (SELECT DateKey FROM DimDate WHERE CalendarYear = 2011 AND CalendarQuarter = 1)
                           AND (SELECT DateKey FROM DimDate WHERE CalendarYear = 2011 AND CalendarQuarter = 4)
-- Invalid column name 'ProductName'.
```

Four mistakes: the column is `EnglishProductName`; "bikes" is a category, not a word in product names; `COUNT(*)` counts order lines, not bikes; and each date subquery returns about 90 rows where `BETWEEN` needs one value.

**After, with the semantic layer:** the right answer, **2,216** bikes.

```sql
SELECT SUM(FactInternetSales.OrderQuantity) AS TotalBikesSold
FROM FactInternetSales
JOIN DimProduct            ON FactInternetSales.ProductKey = DimProduct.ProductKey
JOIN DimProductSubcategory ON DimProduct.ProductSubcategoryKey = DimProductSubcategory.ProductSubcategoryKey
JOIN DimProductCategory    ON DimProductSubcategory.ProductCategoryKey = DimProductCategory.ProductCategoryKey
JOIN DimDate               ON FactInternetSales.OrderDateKey = DimDate.DateKey
WHERE DimProductCategory.EnglishProductCategoryName = 'Bikes'
  AND DimDate.CalendarYear = 2011
```

It used each definition: *units sold* (`SUM(OrderQuantity)`), the *product category* join path, and *year* through `DimDate`. The rules also fixed smaller problems in other questions:

| Question | Before | After |
|---|---|---|
| how many bikes were sold in 2011 | ❌ error: `Invalid column name 'ProductName'` | ✅ 2,216 |
| total internet sales per calendar year | ⚠️ right totals, years unsorted | ✅ sorted 2010 → 2014 |
| number of customers per country | ✅ right, unsorted | ✅ right, sorted by number of customers |

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

To test without the web page: `uv run --env-file .env python ask.py`. To see the text the model gets from the semantic layer: `uv run python semantic.py`.

**Troubleshooting, macOS:** `OpenSSL library could not be loaded, make sure OpenSSL 1.0, 1.1, or 3.0 is installed` means Homebrew's `openssl` points to OpenSSL 4 (installing Ollama with Homebrew can do this), which the SQL Server driver doesn't support. Add this line to `.env` and start the app with `--env-file .env` as above:

```
DYLD_LIBRARY_PATH=/opt/homebrew/opt/openssl@3/lib
```

### Known limits

The 7B model handles questions well when the semantic layer defines their words. Questions with business words the YAML file doesn't define, or with many joins, can still produce wrong SQL or a SQL Server error, and the model doesn't retry yet. Two ideas from the roadmap address this: self-repair (send the error back to the model once) and an evaluation set that measures how often answers are right.

## Roadmap

- [x] SQL Server in Docker Compose with a volume and health check
- [x] Automatic restore of AdventureWorksDW2022
- [x] Python project with uv: connection to SQL Server and a schema reader
- [x] Local LLM (Ollama) writes T-SQL from the schema and the question
- [x] Web interface: Streamlit chatbox with conversation history
- [x] Semantic layer: business definitions of metrics, terms and rules (`semantic_layer.yaml`)
- [ ] Safety: only SELECT statements, a read-only login, row limits and timeouts
- [ ] Self-repair: send SQL errors back to the model once
- [ ] Evaluation: 50 test questions, scored by comparing query results; compare models
- [ ] The app in its own container

## License note

SQL Server runs as the free Developer edition, licensed for development and testing only. AdventureWorksDW2022 comes from Microsoft's [sql-server-samples](https://github.com/microsoft/sql-server-samples) repository.
