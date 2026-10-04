# SQL to ORM Refactoring: `mysql.connector` to SQLAlchemy 2.0

A small learning project that takes a procedural Python script (raw SQL with `mysql.connector`) and refactors it into a SQLAlchemy 2.0 ORM version that manages a `users` table.

## Project files

| File | Description |
|---|---|
| `original_raw_sql.py` | The original script. It contains `get_connection()` and `create_user()` using a parameterized query. The other functions mentioned in the source (`get_user_by_username`, `update_user_email`, `delete_user`, `list_users`) were not provided, so they are not included. |
| `refactored_sqlalchemy.py` | The SQLAlchemy 2.0 version: a declarative `User` model, engine creation, table creation, a Session, add and commit with rollback on error, and a query by username. |
| `README.md` | This file. |

## Requirements

- Python 3.10 or newer (the code uses the `User | None` annotation syntax)
- SQLAlchemy 2.0 or newer
- `mysql-connector-python` (the MySQL driver)
- A running MySQL server with a database named `example_db`

```bash
pip install sqlalchemy mysql-connector-python
```

## Setup

1. Create the database. SQLAlchemy creates the `users` table, but not the database itself.

   ```sql
   CREATE DATABASE example_db;
   ```

2. Provide the database password through an environment variable instead of writing it in the code.

   macOS / Linux:

   ```bash
   export DB_PASSWORD="your_real_password"
   ```

   Windows (PowerShell):

   ```powershell
   $env:DB_PASSWORD = "your_real_password"
   ```

   If `DB_PASSWORD` is not set, the code falls back to the placeholder `"yourpassword"`, which will not work on a real server.

3. If your MySQL user or host is not `root` on `localhost`, edit the values in `create_db_engine()`.

## Running

```bash
python refactored_sqlalchemy.py
```

On a first run with an empty table, the script creates the user `alice` and then looks it up. You should see output similar to this (the `id` value depends on your table):

```
User 'alice' created successfully.
Found: User(id=1, username='alice', email='alice@example.com')
```

On a second run, `alice` already exists. The unique constraint rejects the insert, the script rolls back the transaction and prints an "already exists" message, and the lookup that follows still finds the existing user.

## How the refactored code works

1. **Model:** `User` maps to the `users` table with an auto-incrementing integer primary key, a unique and non-nullable `username` (`String(50)`), and a unique and non-nullable `email` (`String(255)`). MySQL requires a length for `VARCHAR` columns, which is why `String` has a size.
2. **Engine:** `create_engine` creates the connection pool. The URL is built with `URL.create()`, which handles special characters in the password safely.
3. **Table creation:** `Base.metadata.create_all(engine)` creates any missing tables defined by the models. It does not modify tables that already exist.
4. **Session:** `with Session(engine) as session:` guarantees the session is closed when the block ends.
5. **Insert:** `session.add(user)` stages the object and `session.commit()` writes it. `IntegrityError` (for example a duplicate username or email) and other `SQLAlchemyError` exceptions trigger `session.rollback()`.
6. **Query:** `select(User).where(User.username == username)` produces a query with a bound parameter, and `session.scalars(stmt).one_or_none()` returns the matching `User` or `None`.

## Why the ORM version is more professional and secure

- **SQL injection:** SQL injection happens when user input is mixed into the SQL text. With the ORM you do not build SQL strings by hand, so that mistake is much harder to make.
- **Parameter binding:** Values are sent separately from the SQL statement and are treated as data. Raw SQL can also do this (the original `%s` placeholders do), but it relies on the developer doing it correctly every time. In the ORM it is the default.
- **Type and schema consistency:** The `User` class is the single definition of the table. Columns are Python attributes, so a typo in a column name fails early, editors can autocomplete, and type hints such as `Mapped[str]` can be checked by tools.
- **Maintainability:** Rows are objects (`user.email`) instead of tuples (`row[2]`), and a schema change is made in one place. Tools such as Alembic can generate migrations from model changes.
- **Database portability:** SQLAlchemy dialects translate the same Python code into the SQL of each database, so moving to another database mostly means changing the connection URL and driver. Portability is not perfect for database-specific features.
- **Transaction management:** The Session collects changes and writes them together on `commit()`. `rollback()` discards everything since the last commit if something fails.

Note that the original `create_user` already used a parameterized query, so it was not vulnerable to injection. The comparison above is between the ORM and raw SQL in general, including the unsafe style of building queries with string formatting:

```python
# Unsafe: never build SQL this way
sql = f"SELECT * FROM users WHERE username = '{username}'"
```

## Trying it without MySQL (optional)

To test the logic without a MySQL server, temporarily replace the engine creation in `create_db_engine()` with SQLite, which is included with Python and needs no extra driver:

```python
return create_engine("sqlite:///test.db")
```

## Troubleshooting

| Problem | Likely cause |
|---|---|
| `Access denied for user 'root'` | Wrong password or user. Check `DB_PASSWORD` and the values in `create_db_engine()`. |
| `Unknown database 'example_db'` | The database has not been created. Run `CREATE DATABASE example_db;`. |
| `Can't connect to MySQL server` | The server is not running or the host/port is wrong. |
| `ModuleNotFoundError: sqlalchemy` or `mysql` | Packages are not installed in the Python environment you are using. Re-run the `pip install` command. |
| `TypeError` on `User \| None` | Python version is older than 3.10. |

## Limitations and next steps

- Only creating a user and finding one by username are implemented. Update, delete, and list operations can be added using the same Session pattern.
- `create_all` does not change existing tables. For schema changes in a real project, use a migration tool such as Alembic.
- The script has not been tested against a live MySQL server in this project; test it in your own environment first.
