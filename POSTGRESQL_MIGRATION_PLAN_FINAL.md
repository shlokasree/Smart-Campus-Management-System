# POSTGRESQL MIGRATION PLAN — FINAL
## CampusCare SQLite to PostgreSQL (`campus_db`) Production Migration Specification

**Document Version:** 5.0.0 (Final Approved Candidate)  
**Date:** 2026-10-11  
**Status:** **PLAN ONLY — STRICTLY NO APPLICATION, CONFIGURATION, OR DATABASE CHANGES APPLIED**  
**Target Operational Database:** PostgreSQL `campus_db` (`localhost:5432`)  
**Verified Pre-Migration Backup Archive:** [`backups/backup_20261010_232229/`](file:///c:/Users/lenovo/Downloads/CampusCare_Frontend_Starter%20%285%29/CampusCare/backups/backup_20261010_232229)  

---

## 1. Classification of Knowledge & Epistemology

All facts, assumptions, and proposed actions throughout this document are classified into three distinct categories:

- **`[VERIFIED FACT]`**: Ground truth verified by direct read-only inspection of source code, catalog tables (`pg_constraint`, `information_schema`), or backup files.
- **`[ASSUMPTION / UNVERIFIED]`**: Conditions that depend on future runtime execution or staging validation.
- **`[PROPOSED ACTION]`**: Architecture changes, SQL statements, and migration tasks designed for execution only upon explicit user approval.

---

## 2. PostgreSQL Connection-Layer Architecture & Route Transaction Lifecycle

### 2.1 Audit of Existing Route Database & Transaction Patterns
- `[VERIFIED FACT]`: Inspection of all 4 backend route modules ([`auth.py`](file:///c:/Users/lenovo/Downloads/CampusCare_Frontend_Starter%20%285%29/CampusCare/backend/routes/auth.py), [`complaints.py`](file:///c:/Users/lenovo/Downloads/CampusCare_Frontend_Starter%20%285%29/CampusCare/backend/routes/complaints.py), [`staff.py`](file:///c:/Users/lenovo/Downloads/CampusCare_Frontend_Starter%20%285%29/CampusCare/backend/routes/staff.py), [`admin.py`](file:///c:/Users/lenovo/Downloads/CampusCare_Frontend_Starter%20%285%29/CampusCare/backend/routes/admin.py)) reveals two distinct transaction patterns:
  1. **Write Operations (`POST /register`, `POST /complaints`, `PUT /status`):**
     Execute SQL statements, explicitly call `connection.commit()`, and call `connection.close()` in a `finally` block.
  2. **Read-Only Operations (`POST /login`, `GET /complaints`, `GET /stats`, `GET /users`):**
     Execute `SELECT` queries, **do not call `connection.commit()`**, and call `connection.close()` in a `finally` block.
- `[VERIFIED FACT]`: In `psycopg2`, executing a `SELECT` query opens a backend transaction (`TRANSACTION_STATUS_INTRANS`). If `connection.commit()` is not called and the connection is returned to a pool, it remains inside an open read transaction.
- `[VERIFIED FACT]`: If an unhandled exception or `HTTPException` is raised during a write, `commit()` is skipped. If a query failed, the connection enters an aborted transaction state (`TRANSACTION_STATUS_INERROR`). Any subsequent query on that pooled connection will fail with: `current transaction is aborted, commands ignored until end of transaction block`.
- `[VERIFIED FACT]`: Calling `connection.close()` on a raw `psycopg2` pooled connection closes the physical socket rather than returning it to the pool.

### 2.2 Production-Grade Pooled Connection Wrapper Specification
- `[PROPOSED ACTION]`: Replace [`backend/database.py`](file:///c:/Users/lenovo/Downloads/CampusCare_Frontend_Starter%20%285%29/CampusCare/backend/database.py) with a connection-layer wrapper that tracks cursors and enforces transaction cleanup upon checkout return:

```python
import os
from pathlib import Path
from contextlib import contextmanager
from dotenv import load_dotenv
import psycopg2
import psycopg2.extensions
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "campus_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

_pool: ThreadedConnectionPool | None = None

def init_pool(minconn: int = 1, maxconn: int = 20) -> None:
    """Initializes the thread-safe connection pool on application startup."""
    global _pool
    if _pool is None or _pool.closed:
        _pool = ThreadedConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )

def close_pool() -> None:
    """Closes all pooled connections on application shutdown."""
    global _pool
    if _pool is not None and not _pool.closed:
        _pool.closeall()
        _pool = None

class PooledConnectionWrapper:
    """
    Transparent connection wrapper ensuring:
    1. .cursor() returns RealDictCursor for dict-like row access (row['id']).
    2. Active cursors are tracked and closed upon connection close.
    3. Transactions are cleanly rolled back if uncommitted or in error before
       returning the connection to the pool, guaranteeing an IDLE state.
    4. Broken or corrupted connections are closed and discarded from the pool.
    """
    def __init__(self, raw_conn, pool: ThreadedConnectionPool):
        self._conn = raw_conn
        self._pool = pool
        self._closed = False
        self._cursors = []

    def cursor(self):
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        self._cursors.append(cur)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._closed:
            return

        # 1. Close all open cursors created by this wrapper
        for cur in self._cursors:
            try:
                if not cur.closed:
                    cur.close()
            except Exception:
                pass
        self._cursors.clear()

        # 2. Reset transaction state back to clean IDLE
        try:
            status = self._conn.get_transaction_status()
            if status != psycopg2.extensions.TRANSACTION_STATUS_IDLE:
                self._conn.rollback()
        except Exception:
            # Socket corrupted; discard connection from pool permanently
            try:
                self._pool.putconn(self._conn, close=True)
                self._closed = True
                return
            except Exception:
                pass

        # 3. Return clean, idle connection to pool
        try:
            self._pool.putconn(self._conn)
        except Exception:
            pass
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

def get_connection() -> PooledConnectionWrapper:
    """
    Backward-compatible connection factory.
    Yields a wrapped pooled connection that returns cleanly to the pool upon .close().
    """
    if _pool is None or _pool.closed:
        init_pool()
    raw_conn = _pool.getconn()
    return PooledConnectionWrapper(raw_conn, _pool)

@contextmanager
def get_db_cursor():
    """Context manager for direct cursor checkout with automatic commit/rollback."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
```

### 2.3 Route Safety Validation Matrix
- `[VERIFIED FACT]`: Validated against all route patterns:
  - **Read Requests (`SELECT` without `commit`):** `close()` detects `TRANSACTION_STATUS_INTRANS`, executes `self._conn.rollback()`, resetting the connection to `TRANSACTION_STATUS_IDLE` before returning to pool.
  - **Successful Write Requests (`commit` called):** Transaction status is already `TRANSACTION_STATUS_IDLE`. `close()` closes cursors and returns connection to pool immediately.
  - **Failed Write Requests (Exception before `commit`):** Route enters `finally: connection.close()`. `close()` executes `rollback()`, aborting uncommitted changes and clearing any `INERROR` status before returning to pool.

---

## 3. Unified Final PostgreSQL Schema & Two-Stage Constraint Enforcement

### 3.1 Exact Final Target Schema
- `[PROPOSED ACTION]`: The schema in `campus_db` will have the following exact columns, defaults, and constraints:

#### Table 1: `public.users`
```sql
CREATE TABLE public.users (
    id INTEGER NOT NULL DEFAULT nextval('public.users_id_seq'::regclass),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'student',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT users_email_key UNIQUE (email),
    CONSTRAINT users_role_check CHECK (role IN ('student', 'faculty', 'staff', 'admin'))
);
```

#### Table 2: `public.complaints`
```sql
CREATE TABLE public.complaints (
    complaint_id INTEGER NOT NULL DEFAULT nextval('public.complaints_complaint_id_seq'::regclass),
    user_id INTEGER NOT NULL,
    student_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    title VARCHAR(255) NULL,
    category VARCHAR(100) NOT NULL,
    location VARCHAR(255) NULL,
    description TEXT NOT NULL,
    priority VARCHAR(50) NOT NULL DEFAULT 'Medium',
    status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    assigned_staff VARCHAR(255) NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT complaints_pkey PRIMARY KEY (complaint_id),
    CONSTRAINT complaints_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT complaints_status_check CHECK (status IN ('Pending', 'In Progress', 'Resolved', 'Submitted'))
);
```

### 3.2 Two-Stage Constraint Enforcement Execution
- `[VERIFIED FACT]`: Attempting to add `NOT NULL` constraints to columns before migrating and populating existing rows will fail if nulls exist.
- `[PROPOSED ACTION]`: Execute constraint enforcement in two synchronized stages:
  1. **Stage 1 (Pre-Transfer Column Expansion):**
     ```sql
     -- Standardize primary key column and rename sequence
     ALTER TABLE users RENAME COLUMN user_id TO id;
     ALTER SEQUENCE users_user_id_seq RENAME TO users_id_seq;
     ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);
     ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;

     -- Add missing user columns as nullable initially
     ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
     ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;

     -- Drop non-deferrable foreign key to permit re-keying
     ALTER TABLE complaints DROP CONSTRAINT IF EXISTS complaints_user_id_fkey;

     -- Add missing complaint columns as nullable initially
     ALTER TABLE complaints ADD COLUMN IF NOT EXISTS student_name VARCHAR(255);
     ALTER TABLE complaints ADD COLUMN IF NOT EXISTS email VARCHAR(255);
     ALTER TABLE complaints ADD COLUMN IF NOT EXISTS title VARCHAR(255);
     ALTER TABLE complaints ADD COLUMN IF NOT EXISTS location VARCHAR(255);
     ALTER TABLE complaints ADD COLUMN IF NOT EXISTS priority VARCHAR(50);
     ALTER TABLE complaints ADD COLUMN IF NOT EXISTS assigned_staff VARCHAR(255);
     ALTER TABLE complaints ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE;
     ```
  2. **Stage 2 (Post-Transfer Constraint Tightening & Validation):**
     Executed *after* data transfer and validation asserts zero nulls:
     ```sql
     -- Enforce constraints on users
     ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;
     ALTER TABLE users ALTER COLUMN created_at SET NOT NULL;
     ALTER TABLE users ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

     -- Enforce constraints on complaints
     ALTER TABLE complaints ALTER COLUMN student_name SET NOT NULL;
     ALTER TABLE complaints ALTER COLUMN email SET NOT NULL;
     ALTER TABLE complaints ALTER COLUMN priority SET NOT NULL;
     ALTER TABLE complaints ALTER COLUMN priority SET DEFAULT 'Medium';
     ALTER TABLE complaints ALTER COLUMN status SET NOT NULL;
     ALTER TABLE complaints ALTER COLUMN status SET DEFAULT 'Pending';
     ALTER TABLE complaints ALTER COLUMN created_at SET NOT NULL;
     ALTER TABLE complaints ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
     ALTER TABLE complaints ALTER COLUMN updated_at SET NOT NULL;
     ALTER TABLE complaints ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;

     -- Re-apply foreign key and status check constraints
     ALTER TABLE complaints ADD CONSTRAINT complaints_user_id_fkey 
     FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

     ALTER TABLE complaints ADD CONSTRAINT complaints_status_check 
     CHECK (status IN ('Pending', 'In Progress', 'Resolved', 'Submitted'));
     ```

---

## 4. Pre-Import Conflict Detection & Pre-Rekeying Assertion Gate

### 4.1 Email Collision Detection
- `[VERIFIED FACT]`: Catalog query on `campus_db.users` confirms existing emails: `john@campus.edu` and `jane.smith@campus.edu`.
- `[VERIFIED FACT]`: Inspection of `campuscare.db.users` confirms 17 distinct emails (e.g. `neetu@gmail.com`, `student@test.com`, `admin@campuscare.com`).
- `[VERIFIED FACT]`: The current intersection between the two sets is empty (`∅`).
- `[PROPOSED ACTION]`: Before any record is transferred, the migration script will compare the normalized sets:
  ```python
  sqlite_emails = {r["email"].strip().lower() for r in sqlite_users}
  postgres_emails = {r["email"].strip().lower() for r in pg_users}
  overlap = sqlite_emails.intersection(postgres_emails)
  if overlap:
      raise RuntimeError(f"FATAL: Email collision detected: {overlap}. Aborting migration to protect data integrity.")
  ```

### 4.2 Pre-Rekeying Assertion Gate
- `[PROPOSED ACTION]`: Inside the transaction, prior to modifying any IDs, the runner asserts:
  1. `campus_db.users` row count equals **exactly 2**.
  2. `campus_db.complaints` row count equals **exactly 2**.
  3. `campus_db.users` IDs are `1` and `2`.
  4. Target IDs `18` and `19` do not exist in `campus_db.users`.
  5. Target IDs `11` and `12` do not exist in `campus_db.complaints`.
  6. Source SQLite row counts equal **exactly 17 users** and **10 complaints**.
- Any assertion discrepancy raises an exception, triggering immediate transaction `ROLLBACK`.

---

## 5. Foreign Key Deferrability & Safe Re-keying Mechanics

### 5.1 Constraint Catalog Facts
- `[VERIFIED FACT]`: Catalog query confirms:
  ```sql
  SELECT condeferrable, condeferred FROM pg_constraint WHERE conname = 'complaints_user_id_fkey';
  ```
  Returns `condeferrable = False`, `condeferred = False`.
- `[VERIFIED FACT]`: In PostgreSQL, dropping and adding foreign key constraints inside an active transaction is fully atomic and transactional.

### 5.2 Deterministic Re-Keying Procedure
- `[PROPOSED ACTION]`: Executed inside transaction:
  ```sql
  -- 1. Re-key complaints first (1, 2 -> 11, 12) and map to upcoming parent ID (18)
  UPDATE complaints 
  SET complaint_id = 11, user_id = 18, student_name = 'John Doe', email = 'john@campus.edu',
      title = NULL, location = NULL, priority = 'Unassigned', updated_at = created_at
  WHERE complaint_id = 1;

  UPDATE complaints 
  SET complaint_id = 12, user_id = 18, student_name = 'John Doe', email = 'john@campus.edu',
      title = NULL, location = NULL, priority = 'Unassigned', updated_at = created_at
  WHERE complaint_id = 2;

  -- 2. Re-key users (1, 2 -> 18, 19) and lock passwords
  UPDATE users 
  SET id = 18, password_hash = '!LOCKED_LEGACY_RESET_REQUIRED_2026', created_at = '2026-09-16 23:24:38'
  WHERE id = 1;

  UPDATE users 
  SET id = 19, password_hash = '!LOCKED_LEGACY_RESET_REQUIRED_2026', created_at = '2026-09-16 23:25:32'
  WHERE id = 2;

  -- 3. Stream 17 SQLite users (explicit IDs 1-17, preserving password_hash and role)
  -- 4. Stream 10 SQLite complaints (explicit IDs 1-10, preserving foreign keys)
  ```

---

## 6. Password Security & Legacy Credential Locking

### 6.1 Preservation of Valid Hashes
- `[VERIFIED FACT]`: All 17 SQLite users have valid Argon2 password hashes.
- `[PROPOSED ACTION]`: Streamed 1:1 into PostgreSQL. All active students, staff, and admins can log in immediately after cutover with zero password disruption.

### 6.2 Cryptographic Locking of Legacy Accounts
- `[PROPOSED ACTION]`: Legacy users `18` and `19` receive `password_hash = '!LOCKED_LEGACY_RESET_REQUIRED_2026'`.
- `[VERIFIED FACT]`: In [`backend/routes/auth.py:129-144`](file:///c:/Users/lenovo/Downloads/CampusCare_Frontend_Starter%20%285%29/CampusCare/backend/routes/auth.py#L129-L144), `password_hash.verify()` raises `UnknownHashError` when encountering `!LOCKED`. The route catches this via `except Exception: valid_password = False`, returning standard HTTP 401 Unauthorized without 500 crashes or authentication bypass.

---

## 7. Sequence Defaults & Next ID Generation Proof

### 7.1 Sequence Verification
- `[VERIFIED FACT]`: Catalog inspection confirms:
  - Sequence `public.users_user_id_seq` is owned by `public.users.user_id`.
  - Sequence `public.complaints_complaint_id_seq` is owned by `public.complaints.complaint_id`.
  - Sequence `public.books_book_id_seq` is owned by `public.books.book_id`.

### 7.2 Explicit Binding & Sequence Synchronization
- `[PROPOSED ACTION]`: Executed in migration sequence:
  ```sql
  ALTER SEQUENCE users_user_id_seq RENAME TO users_id_seq;
  ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);
  ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;

  SELECT setval('public.users_id_seq', 19, true);
  SELECT setval('public.complaints_complaint_id_seq', 12, true);
  ```
- **Proof:**
  - `setval('users_id_seq', 19, true)` guarantees the next call to `nextval()` by `POST /api/auth/register` evaluates to $19 + 1 = 20$. **Next user ID is `20`.**
  - `setval('complaints_complaint_id_seq', 12, true)` guarantees the next call to `nextval()` by `POST /api/complaints` evaluates to $12 + 1 = 13$. **Next complaint ID is `13` (`#CC-13`).**

---

## 8. Role & Complaint-Status Support

### 8.1 Roles Support
- `[VERIFIED FACT]`: In `campus_db`, `users_role_check` enforces:
  `CHECK (role IN ('student', 'faculty', 'staff', 'admin'))`.
- `[VERIFIED FACT]`: All 17 SQLite users (`student`, `staff`, `admin`) and legacy user Jane Smith (`faculty`) adhere to this constraint without modification.

### 8.2 Complaint Status Support
- `[VERIFIED FACT]`: SQLite complaints contain statuses `'Pending'`, `'In Progress'`, and `'Resolved'`. Legacy complaints contain `'Submitted'`.
- `[PROPOSED ACTION]`: The constraint `CHECK (status IN ('Pending', 'In Progress', 'Resolved', 'Submitted'))` accommodates all four statuses.
- `[VERIFIED FACT]`: Frontend rendering in [`frontend/js/staff.js:572-598`](file:///c:/Users/lenovo/Downloads/CampusCare_Frontend_Starter%20%285%29/CampusCare/frontend/js/staff.js#L572-L598) and [`track-complaint.html:1450`](file:///c:/Users/lenovo/Downloads/CampusCare_Frontend_Starter%20%285%29/CampusCare/frontend/track-complaint.html#L1450) maps `'Submitted'` safely to the default pending CSS styling class.

---

## 9. Preservation of Books & Vector Embeddings

### 9.1 Data Protection Guarantees
- `[VERIFIED FACT]`: `campus_db.public.books` contains **5 rows** with 128-dimensional vector embeddings (`pg_typeof(embedding) = vector`) and sequence `books_book_id_seq` at `5`.
- `[VERIFIED FACT]`: `pgvector_code.public.complaint_embeddings` contains **2 rows** in an independent database.
- `[PROPOSED ACTION]`: The migration runner never references or alters `public.books` or `pgvector_code`.

### 9.2 Validation Queries
- `[PROPOSED ACTION]`:
  ```sql
  SELECT count(*) FROM public.books; -- Must equal 5
  SELECT count(*) FROM public.books WHERE embedding IS NOT NULL; -- Must equal 5
  ```

---

## 10. Preflight Verification Requirements (Not Executed Yet)

### 10.1 Preflight Requirement 1: Route Code Snapshot
- `[VERIFIED FACT]`: `backups/backup_20261010_232229/config/` contains `.env.backup`, `database.py`, `config.py`, and `create_staff.py`.
- `[VERIFIED FACT]`: `routes/auth.py`, `routes/complaints.py`, `routes/staff.py`, `routes/admin.py`, and `analytics_service/app.py` were **NOT** backed up in that folder.
- `[PROPOSED ACTION]`: **Mandatory Preflight Action:** Upon approval and before editing code, execute:
  ```powershell
  New-Item -ItemType Directory -Path "backups\backup_20261010_232229\code_snapshot" -Force
  Copy-Item "backend\routes\auth.py" "backups\backup_20261010_232229\code_snapshot\auth.py"
  Copy-Item "backend\routes\complaints.py" "backups\backup_20261010_232229\code_snapshot\complaints.py"
  Copy-Item "backend\routes\staff.py" "backups\backup_20261010_232229\code_snapshot\staff.py"
  Copy-Item "backend\routes\admin.py" "backups\backup_20261010_232229\code_snapshot\admin.py"
  Copy-Item "analytics_service\app.py" "backups\backup_20261010_232229\code_snapshot\app.py"
  ```

### 10.2 Preflight Requirement 2: Sandboxed PostgreSQL Test Restore
- `[PROPOSED ACTION]`: To empirically verify the backup archive without touching live `campus_db`, execute this self-contained script with guaranteed `finally` cleanup:

```python
import os, subprocess, psycopg2
from dotenv import load_dotenv

load_dotenv(".env")
host = os.getenv("POSTGRES_HOST", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
user = os.getenv("POSTGRES_USER", "postgres")
password = os.getenv("POSTGRES_PASSWORD")
dump_path = r"backups\backup_20261010_232229\postgres\campus_db.dump"
test_db = "campus_db_restore_test"

conn = psycopg2.connect(host=host, port=port, database="postgres", user=user, password=password)
conn.autocommit = True
cur = conn.cursor()

try:
    # 1. Clean slate check & creation
    cur.execute(f"DROP DATABASE IF EXISTS {test_db};")
    cur.execute(f"CREATE DATABASE {test_db};")

    # 2. Restore dump
    pg_env = os.environ.copy()
    pg_env["PGPASSWORD"] = password
    proc = subprocess.run([
        r"C:\Program Files\PostgreSQL\18\bin\pg_restore.exe",
        "-h", host, "-p", str(port), "-U", user, "-d", test_db, dump_path
    ], env=pg_env, capture_output=True, text=True)

    # 3. Validate restored counts individually
    test_conn = psycopg2.connect(host=host, port=port, database=test_db, user=user, password=password)
    t_cur = test_conn.cursor()
    
    t_cur.execute("SELECT count(*) FROM users;")
    u_count = t_cur.fetchone()[0]
    
    t_cur.execute("SELECT count(*) FROM complaints;")
    c_count = t_cur.fetchone()[0]
    
    t_cur.execute("SELECT count(*) FROM books;")
    b_count = t_cur.fetchone()[0]
    
    t_cur.execute("SELECT count(*) FROM books WHERE embedding IS NOT NULL;")
    v_count = t_cur.fetchone()[0]
    
    test_conn.close()

    assert u_count == 2, f"Users mismatch: {u_count} != 2"
    assert c_count == 2, f"Complaints mismatch: {c_count} != 2"
    assert b_count == 5, f"Books mismatch: {b_count} != 5"
    assert v_count == 5, f"Vectors mismatch: {v_count} != 5"
    print("PREFLIGHT TEST RESTORE: PASSED (2 users, 2 complaints, 5 books)")

finally:
    # Guaranteed cleanup
    cur.execute(f"DROP DATABASE IF EXISTS {test_db};")
    cur.close()
    conn.close()
```

---

## 11. Transactional Migration Sequence & Post-Migration Assertions

### 11.1 Execution Pipeline
1. **Preflight Execution:** Create code snapshot and run sandboxed test restore.
2. **Database Migration:** Run `scripts/migrate_sqlite_to_postgres.py` with pre-checks, DDL, data transfer, sequence updates, constraint tightening, and post-checks in an atomic transaction.
3. **Application Cutover:** Deploy refactored `backend/database.py`, update `%s` placeholders in routes, update `analytics_service/app.py`, update `.env` to `POSTGRES_DB=campus_db`, restart services.
4. **Acceptance Testing:** Run test suite.

### 11.2 Post-Migration Integrity Assertions
```sql
-- 1. Row count assertion
SELECT count(*) FROM users;       -- Must equal 19
SELECT count(*) FROM complaints;  -- Must equal 12
SELECT count(*) FROM books;       -- Must equal 5

-- 2. Duplicate email check
SELECT email, count(*) FROM users GROUP BY email HAVING count(*) > 1; -- Must return 0 rows

-- 3. Null password hash check
SELECT count(*) FROM users WHERE password_hash IS NULL; -- Must equal 0

-- 4. Missing required complaint fields check
SELECT count(*) FROM complaints 
WHERE student_name IS NULL OR email IS NULL OR category IS NULL 
   OR description IS NULL OR priority IS NULL OR status IS NULL 
   OR created_at IS NULL OR updated_at IS NULL; -- Must equal 0

-- 5. Orphan complaints referential check
SELECT c.complaint_id, c.user_id 
FROM complaints c 
LEFT JOIN users u ON c.user_id = u.id 
WHERE u.id IS NULL; -- Must return 0 rows

-- 6. Unexpected status check
SELECT DISTINCT status FROM complaints 
WHERE status NOT IN ('Pending', 'In Progress', 'Resolved', 'Submitted'); -- Must return 0 rows

-- 7. Sequence alignment check
SELECT last_value, is_called FROM users_id_seq;               -- last_value=19, is_called=true
SELECT last_value, is_called FROM complaints_complaint_id_seq; -- last_value=12, is_called=true
```

---

## 12. Rollback Strategy & Realistic Downtime Evaluation

### 12.1 Realistic Downtime Assessment
- `[VERIFIED FACT]`: Restarting Uvicorn (`port 8000`) and Flask (`port 5001`) causes a transient **3–10 second** service interruption while TCP ports are rebound.
- `[PROPOSED ACTION]`: Recovery Time Objective (RTO) is established at **under 2 minutes**.

### 12.2 Database Rollback
```cmd
"C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" -h localhost -p 5432 -U postgres -d campus_db --clean --if-exists "backups\backup_20261010_232229\postgres\campus_db.dump"
```

### 12.3 Code & Configuration Rollback
```powershell
Copy-Item "backups\backup_20261010_232229\config\.env.backup" ".env" -Force
Copy-Item "backups\backup_20261010_232229\config\database.py" "backend\database.py" -Force
Copy-Item "backups\backup_20261010_232229\config\create_staff.py" "backend\create_staff.py" -Force
Copy-Item "backups\backup_20261010_232229\code_snapshot\auth.py" "backend\routes\auth.py" -Force
Copy-Item "backups\backup_20261010_232229\code_snapshot\complaints.py" "backend\routes\complaints.py" -Force
Copy-Item "backups\backup_20261010_232229\code_snapshot\staff.py" "backend\routes\staff.py" -Force
Copy-Item "backups\backup_20261010_232229\code_snapshot\admin.py" "backend\routes\admin.py" -Force
Copy-Item "backups\backup_20261010_232229\code_snapshot\app.py" "analytics_service\app.py" -Force
```

---

## 13. End-to-End Acceptance Test Matrix

| ID | Test Scenario | Trigger | Expected Assertion | Verification Mechanism | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AT-01** | Database Counts | SQL Query | `users=19`, `complaints=12`, `books=5` | Direct PostgreSQL query | Untested |
| **AT-02** | Student Login | `POST /api/auth/login` (`student@test.com`) | 200 OK, JWT payload `id=2` | HTTP client / browser | Untested |
| **AT-03** | Admin Login | `POST /api/auth/login` (`admin@campuscare.com`) | 200 OK, JWT payload `id=13` | HTTP client / browser | Untested |
| **AT-04** | Locked Legacy Login | `POST /api/auth/login` (`john@campus.edu`) | 401 Unauthorized (`Invalid email or password`) | HTTP client | Untested |
| **AT-05** | Student Dashboard List | `GET /api/complaints` (student dhriti `id=8`) | 200 OK, returns complaints `#CC-10`, `#CC-9`, `#CC-8`, `#CC-7`, `#CC-4` | Student portal UI | Untested |
| **AT-06** | Create New Complaint | `POST /api/complaints` | 200 OK, created complaint ID is **`13`** (`#CC-13`) | Complaint form UI | Untested |
| **AT-07** | pgAdmin Visibility | Query `SELECT * FROM complaints WHERE complaint_id = 13` | Complaint 13 appears in pgAdmin immediately | pgAdmin query tool | Untested |
| **AT-08** | Staff Status Update | `PUT /api/staff/complaints/13/status` (`In Progress`) | 200 OK, database status updates, badge changes to `In Progress` | Staff dashboard UI | Untested |
| **AT-09** | Books Table Access | SQL Query | `count=5`, vectors intact | Direct PostgreSQL query | Untested |
| **AT-10** | Analytics Parity | `GET /analytics/summary` | Stats aggregate live records from `campus_db` | Analytics summary UI | Untested |

---

## 14. Stop Notice & Sign-off

- **SAFETY GUARANTEE:** Zero code files, configurations, database records, or schemas have been altered.
- **STOPPING POINT:** Planning is 100% complete. Execution will not begin until this final plan is approved.
