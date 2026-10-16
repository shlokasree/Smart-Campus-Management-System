# DATABASE CONNECTION AUDIT — CAMPUSCARE

**Audit Date:** 2026-10-10  
**Audit Scope:** Read-Only Database & Architectural Connection Audit  
**Target Project:** CampusCare Complaint Management System  
**Audit Author:** Antigravity Coding Assistant  

---

## 1. Executive Summary

A comprehensive, non-destructive, read-only audit of the CampusCare web application was conducted to determine why complaints and status updates visible on the frontend do not appear in the PostgreSQL database inspected via pgAdmin.

### Core Finding
**The frontend, backend, and PostgreSQL database are NOT connected in the complaint workflow.**
- The **frontend** connects correctly to the **FastAPI backend** running on port `8000`.
- The **FastAPI backend** and the **Flask analytics service** are hardcoded to store and query all user accounts, complaints, and status changes in a local **SQLite database** located at `database/campuscare.db`.
- A secondary cloud database (**MongoDB Atlas**) is used solely to log complaint submission events in a `complaint_activity` collection.
- The **PostgreSQL database** (`pgvector_code` on `localhost:5432`, inspected in pgAdmin) is configured in `.env` and referenced in an isolated helper file (`backend/services/vector_service.py`), but that file is **never imported, referenced, or executed** by any active backend route handler or application lifecycle script.
- Furthermore, the PostgreSQL database contains no `complaints` or `users` tables; its only relation is `complaint_embeddings` containing two test vector rows.

Therefore, pgAdmin displays no complaint records or status updates because the backend never attempts to write them to PostgreSQL.

---

## 2. Overall Connection Status

```
OVERALL CONNECTION STATUS: FAILED (DISCONNECTED ARCHITECTURE)
```

- **Frontend to FastAPI Backend:** `VERIFIED` (HTTP REST API communication active and functional).
- **Backend to SQLite Database:** `VERIFIED` (Active read/write store for complaints and authentication).
- **Backend to MongoDB Atlas:** `VERIFIED` (Active write store for complaint submission activity log).
- **Backend to PostgreSQL (pgAdmin):** `FAILED` (Completely detached; zero active calls from route handlers).

---

## 3. Actual Frontend API Base URL and Backend Framework

| Component | Framework / Technology | Base URL / Host | Source Location |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | HTML5 / Vanilla ES6 JavaScript | `http://127.0.0.1:5500` | `frontend/` |
| **Primary Backend** | FastAPI (Python 3.13 / Uvicorn) | `http://127.0.0.1:8000` | `backend/main.py` |
| **Analytics Service** | Flask (Python 3.13) | `http://127.0.0.1:5001` | `analytics_service/app.py` |

### Frontend Base URL Declarations
- `frontend/js/api.js`: Line 1: `const API_BASE_URL = "http://127.0.0.1:8000";`
- `frontend/js/complaints.js`: Line 1: `const COMPLAINTS_API_URL = "http://127.0.0.1:8000";`
- `frontend/js/dashboard.js`: Line 1: `const DASHBOARD_API_URL = "http://127.0.0.1:8000";`
- `frontend/js/staff.js`: Line 5: `const STAFF_API_URL = "http://127.0.0.1:8000";`
- `frontend/js/auth.js`: Line 4: `window.API_BASE_URL = "http://127.0.0.1:8000";`
- `frontend/admin-dashboard.html`: Line 287: `const API_BASE_URL = "http://127.0.0.1:8000";`
- `frontend/track-complaint.html`: Line 1205: `const API_BASE = "http://127.0.0.1:8000";`
- `frontend/js/analytics.js`: Line 1: `const ANALYTICS_BASE_URL = "http://127.0.0.1:5001";`

---

## 4. Database Technologies Found in Source Code

Four distinct database technologies/drivers exist within the repository:

1. **SQLite (`sqlite3`) — ACTIVE PRIMARY STORE**
   - Standard Python standard library module.
   - Used for core application persistence: users, authentication, complaints, and status updates.
   - File location: `database/campuscare.db`.
2. **MongoDB Atlas (`pymongo`) — ACTIVE ACTIVITY LOG**
   - Cloud MongoDB instance connected via connection string.
   - Used only for audit trail inserts (`complaint_activity` collection) upon complaint creation.
3. **PostgreSQL / pgvector (`psycopg2`, `pgvector`) — DORMANT / UNWIRED**
   - Driver installed and configured in `.env`.
   - Used exclusively in `backend/services/vector_service.py` to store/query embeddings.
   - Not integrated into complaint CRUD routes.
4. **SQLAlchemy (`sqlalchemy`) — UNUSED**
   - Present in the virtual environment dependencies, but no ORM models, session factories, or engine configurations exist in application code.

---

## 5. Sanitised Active Database Configuration

### Active Primary Database (SQLite)
- **Engine:** SQLite 3
- **Configuration File:** `backend/database.py` (Lines 9–18)
- **Path Resolution:** `Path(__file__).resolve().parent.parent / "database" / "campuscare.db"`
- **Connection Mode:** Direct local file connection (`sqlite3.connect()`), row factory configured to `sqlite3.Row`.
- **Pooling / ORM:** None. Each request creates and closes a connection.

### Secondary Database (MongoDB Atlas)
- **Engine:** MongoDB
- **Configuration File:** `backend/services/mongodb_service.py` (Lines 8–24)
- **Target Database Name:** `campuscare` (loaded from `.env` `MONGO_DB`)
- **Connection URI:** Configured via `.env` (`MONGO_URI`, credentials sanitised)
- **Connection Mode:** Singleton `pymongo.MongoClient` instance.

### Dormant Database Configuration (PostgreSQL)
- **Engine:** PostgreSQL with `pgvector` extension
- **Configuration File:** `backend/services/vector_service.py` (Lines 23–34)
- **Host:** Configured via `.env` (`POSTGRES_HOST=localhost`)
- **Port:** Configured via `.env` (`POSTGRES_PORT=5432`)
- **Database Name:** Configured via `.env` (`POSTGRES_DB=pgvector_code`)
- **User:** Configured via `.env` (`POSTGRES_USER=postgres`)
- **Password:** Configured via `.env` (`POSTGRES_PASSWORD=[REDACTED]`)
- **Active Callers:** **None**.

---

## 6. Actual Application Database Identity (Verified via Safe Read-Only Inspection)

Inspection of the running backend's active store confirms:
- **Database Engine:** SQLite 3 (version 3.45.1+)
- **Absolute File Path:** `C:\Users\lenovo\Downloads\CampusCare_Frontend_Starter (5)\CampusCare\database\campuscare.db`
- **File Size:** ~20,480 bytes
- **Existing Relations & Row Counts:**
  - `users`: **17 records** (Roles: `admin`, `staff`, `student`)
  - `complaints`: **10 records** (Statuses: 6 `Resolved`, 1 `In Progress`, 3 `Pending`)
  - `sqlite_sequence`: Internal autoincrement sequence tracker

---

## 7. pgAdmin Database Identity (Verified via Safe Read-Only Inspection)

Inspection of the PostgreSQL server running on localhost confirms:
- **Server Address:** `localhost` / `::1`
- **Server Port:** `5432`
- **`current_database()`:** `pgvector_code`
- **`current_schema()`:** `public`
- **`current_user`:** `postgres`
- **Tables Present in Public Schema:** Exactly 1 table: `complaint_embeddings`
- **Table Schema:** `complaint_embeddings (id integer, complaint_id integer, description text, embedding vector, created_at timestamp)`
- **Total Rows in PostgreSQL:** **2 records** (both referencing test `complaint_id: 9999`)
- **Tables Missing in PostgreSQL:**
  - `complaints` table does **NOT** exist.
  - `users` table does **NOT** exist.

### Direct Comparison
| Metric | Application Active Store | pgAdmin Target Database |
| :--- | :--- | :--- |
| **System** | SQLite 3 | PostgreSQL 16+ |
| **Database Identifier** | `database/campuscare.db` | `pgvector_code` |
| **Complaints Table Exists** | **Yes** (`complaints`) | **No** (Table does not exist) |
| **Complaints Row Count** | **10 records** | **0 records** |
| **Users Table Exists** | **Yes** (`users`) | **No** (Table does not exist) |
| **Users Row Count** | **17 records** | **0 records** |

---

## 8. Complaint Submission Data-Flow Trace

The lifecycle of a student complaint submission proceeds as follows:

```
[Frontend: complaint-form.html]
    │
    ▼ (Form submit event)
[frontend/js/complaints.js: submitComplaint()]
    │
    ▼ (HTTP POST http://127.0.0.1:8000/api/complaints with Bearer JWT)
[backend/main.py: FastAPI Router]
    │
    ▼ (Dispatches to route handler)
[backend/routes/complaints.py: create_complaint()]
    │
    ├── 1. Validates JWT via get_current_user() (backend/routes/complaints.py:22)
    ├── 2. Opens SQLite connection via get_connection() (backend/database.py:25)
    ├── 3. Executes SQL:
    │      INSERT INTO complaints (
    │          user_id, student_name, email, title, category,
    │          location, description, priority, status, assigned_staff
    │      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', None)
    │      (backend/routes/complaints.py:100-128)
    ├── 4. Commits SQLite transaction: connection.commit() (Line 132)
    ├── 5. Calls add_complaint_activity() (backend/services/mongodb_service.py:32)
    │      Inserts activity document into MongoDB Atlas 'complaint_activity'
    └── 6. Closes SQLite connection in finally block (Line 171)
    │
    ▼ (HTTP 200 JSON Response: { message, complaint_id, status: "Pending", ... })
[Frontend: redirected to track-complaint.html]
    │
    ▼ (HTTP GET http://127.0.0.1:8000/api/complaints)
[backend/routes/complaints.py: get_my_complaints()]
    │
    ▼ (SELECT * FROM complaints WHERE user_id = ? ORDER BY complaint_id DESC)
[Frontend displays complaint card with status "Pending"]
```

**PostgreSQL Involvement:** **0% (Never invoked).**

---

## 9. Complaint Status-Update Data-Flow Trace

The lifecycle of a staff status update proceeds as follows:

```
[Frontend: staff-dashboard.html]
    │
    ▼ (Staff clicks "Mark In Progress" or "Mark Resolved")
[frontend/js/staff.js: updateComplaintStatus(complaintId, newStatus)]
    │
    ▼ (HTTP PUT http://127.0.0.1:8000/api/staff/complaints/{complaint_id}/status)
[backend/routes/staff.py: update_complaint_status()]
    │
    ├── 1. Validates JWT and verifies staff/admin role (backend/routes/staff.py:42)
    ├── 2. Validates newStatus against allowed list: ['Pending', 'In Progress', 'Resolved']
    ├── 3. Opens SQLite connection via get_connection() (backend/database.py:25)
    ├── 4. Executes SQL:
    │      UPDATE complaints
    │      SET status = ?, updated_at = CURRENT_TIMESTAMP
    │      WHERE complaint_id = ?
    │      (backend/routes/staff.py:175-183)
    ├── 5. Commits SQLite transaction: connection.commit() (Line 185)
    └── 6. Closes SQLite connection in finally block (Line 195)
    │
    ▼ (HTTP 200 JSON Response: { message, complaint_id, status })
[Frontend updates UI badge and alerts staff of success]
    │
    ▼ (Subsequent student reload on student-dashboard.html or track-complaint.html)
[backend/routes/complaints.py: get_my_complaints()]
    │
    ▼ (Reads updated status from SQLite database/campuscare.db)
[Frontend renders updated status badge: "In Progress" or "Resolved"]
```

**PostgreSQL Involvement:** **0% (Never invoked).**

---

## 10. API Endpoint and Source-File Inventory

| Endpoint | Method | Purpose | Frontend Caller | Backend File & Function | Target Database |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/auth/register` | `POST` | User registration | `frontend/js/auth.js:22` | `backend/routes/auth.py:37` (`register`) | SQLite (`users`) |
| `/api/auth/login` | `POST` | User login & JWT issuance | `frontend/js/auth.js:78`, `admin-login.html:193` | `backend/routes/auth.py:99` (`login`) | SQLite (`users`) |
| `/api/complaints` | `POST` | Submit complaint | `frontend/js/complaints.js:168` | `backend/routes/complaints.py:57` (`create_complaint`) | SQLite + MongoDB |
| `/api/complaints` | `GET` | List student complaints | `frontend/js/complaints.js:265`, `dashboard.js:100`, `track-complaint.html:1304` | `backend/routes/complaints.py:179` (`get_my_complaints`) | SQLite (`complaints`) |
| `/api/complaints/{id}` | `GET` | Single complaint details | None | `backend/routes/complaints.py:256` (`get_complaint`) | SQLite (`complaints`) |
| `/api/staff/complaints` | `GET` | List all complaints for staff | `frontend/js/staff.js:119` | `backend/routes/staff.py:62` (`get_all_complaints`) | SQLite (`complaints`) |
| `/api/staff/complaints/{id}/status` | `PUT` | Update status (staff) | `frontend/js/staff.js:483` | `backend/routes/staff.py:135` (`update_complaint_status`) | SQLite (`complaints`) |
| `/api/admin/complaints` | `GET` | List all complaints for admin | `frontend/admin-dashboard.html:543` | `backend/routes/admin.py:48` (`get_all_complaints`) | SQLite (`complaints`) |
| `/api/admin/users` | `GET` | List all users for admin | `frontend/admin-dashboard.html:428` | `backend/routes/admin.py:108` (`get_all_users`) | SQLite (`users`) |
| `/api/admin/stats` | `GET` | Admin metrics & status counts | `frontend/admin-dashboard.html:353` | `backend/routes/admin.py:152` (`get_admin_stats`) | SQLite (`complaints`, `users`) |
| `/api/admin/complaints/{id}/status` | `PUT` | Update status (admin) | None directly bound | `backend/routes/admin.py:227` (`update_complaint_status`) | SQLite (`complaints`) |
| `/analytics/summary` | `GET` | Overall complaint statistics | `frontend/js/analytics.js:6` | `analytics_service/app.py:48` (`analytics_summary`) | SQLite (`complaints`, `users`) |
| `/analytics/categories` | `GET` | Complaint category counts | None | `analytics_service/app.py:118` (`analytics_categories`) | SQLite (`complaints`) |
| `/analytics/status` | `GET` | Complaint status distribution | None | `analytics_service/app.py:157` (`analytics_status`) | SQLite (`complaints`) |
| `/analytics/priorities` | `GET` | Complaint priority counts | None | `analytics_service/app.py:195` (`analytics_priorities`) | SQLite (`complaints`) |

---

## 11. Database Table and Schema Comparison

### SQLite (`database/campuscare.db`)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE complaints (
    complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    student_name TEXT NOT NULL,
    email TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending',
    assigned_staff TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### PostgreSQL (`pgvector_code`)
```sql
CREATE TABLE public.complaint_embeddings (
    id integer NOT NULL DEFAULT nextval('complaint_embeddings_id_seq'::regclass),
    complaint_id integer NOT NULL,
    description text NOT NULL,
    embedding public.vector,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
-- Note: 'complaints' and 'users' tables do NOT exist in PostgreSQL.
```

---

## 12. Transaction and Persistence Checks

1. **Transaction Lifecycle in SQLite:**
   - Both `create_complaint` (`routes/complaints.py:132`) and `update_complaint_status` (`routes/staff.py:185`) issue an explicit `connection.commit()`.
   - SQLite commits synchronously to disk (`database/campuscare.db`).
   - Clean connection termination: `connection.close()` is enforced in `finally` blocks across all handlers.
2. **Persistence After Server Restart:**
   - Read-only inspection confirmed historical records spanning multiple user sessions (e.g., complaints #1 through #10 created between Oct 8 and Oct 10, 2026).
   - Data persists across backend and browser restarts because SQLite writes directly to disk.
3. **PostgreSQL Transactions:**
   - `save_complaint_embedding` in `backend/services/vector_service.py:69` has a `connection.commit()`, but is never invoked.
   - Zero transactions occur against PostgreSQL during regular user actions.

---

## 13. Status-Value Consistency Findings

### Canonical Status Values
The backend and frontend adhere to three primary status values:
1. `Pending` (Initial status assigned on complaint creation)
2. `In Progress` (Assigned by staff)
3. `Resolved` (Assigned by staff or admin)

### Consistency Matrix
- **Database Default (SQLite):** `DEFAULT 'Pending'` (Line 95 of `backend/database.py`).
- **Creation Handler:** Enforces `status = 'Pending'` explicitly (`routes/complaints.py:125`).
- **MongoDB Audit Trail:** Records `status = 'Pending'` and `action = 'Submitted'` (`routes/complaints.py:143`).
- **Staff Status Validator:** Restricts to `['Pending', 'In Progress', 'Resolved']` (`routes/staff.py:141-145`).
- **Admin Status Validator:** Restricts to `['Pending', 'In Progress', 'Resolved']` (`routes/admin.py:232-236`).
- **Frontend Normalisation:**
  - `frontend/js/staff.js`: Handles lowercase comparisons (`pending`, `in progress`, `in_progress`, `resolved`).
  - `frontend/js/dashboard.js`: Filters case-insensitively using `.toLowerCase().trim() === "in progress"` and `"resolved"`.
  - `frontend/track-complaint.html`: Matches exact strings `"Pending"`, `"In Progress"`, `"Resolved"`.
- **PostgreSQL Status Storage:** None. PostgreSQL has no status column anywhere.

---

## 14. Test Results

| Check | Result | Evidence | Notes |
| :--- | :--- | :--- | :--- |
| **Frontend points to intended backend** | **PASS** | `api.js:1`, `complaints.js:1`, `staff.js:5`, `task-84.log` | Frontend consistently targets port `8000`. Uvicorn logs show successful 200 responses. |
| **Backend uses PostgreSQL** | **FAIL** | `database.py:1,18`, `routes/*.py` | Backend routes import `get_connection()` which connects to SQLite. No route connects to PostgreSQL. |
| **Active database identity verified** | **PASS** | Safe inspection of `database/campuscare.db` | Confirmed SQLite file with 10 complaints and 17 users. |
| **pgAdmin points to same database** | **FAIL** | PostgreSQL metadata query (`pgvector_code`) | pgAdmin inspects PostgreSQL (`pgvector_code`), which only contains `complaint_embeddings`. |
| **Complaint INSERT commits** | **UNVERIFIED** | Code review: `routes/complaints.py:132` | Controlled write test skipped in production per safety guidelines; existing SQLite rows confirm historical commit. |
| **Complaint SELECT reads the same table** | **PASS** | `routes/complaints.py:198-217` | Reads from SQLite `complaints` table using the same `get_connection()` factory. |
| **Status UPDATE commits** | **UNVERIFIED** | Code review: `routes/staff.py:185` | Controlled write test skipped in production per safety guidelines; verified via code inspection. |
| **Updated status persists after reload** | **PASS** | SQLite records contain 6 `Resolved`, 1 `In Progress`, 3 `Pending` | Multi-status records verified persisted on disk in `database/campuscare.db`. |
| **Dashboard uses backend data** | **PASS** | `dashboard.js:100`, `admin-dashboard.html:353` | Dashboards actively fetch data from `/api/complaints` and `/api/admin/stats`. |

---

## 15. Exact Evidence Inventory

1. **`backend/database.py` (Lines 1, 18, 25–33):**
   ```python
   import sqlite3
   DATABASE_PATH = DATABASE_DIR / "campuscare.db"
   def get_connection():
       connection = sqlite3.connect(DATABASE_PATH)
       connection.row_factory = sqlite3.Row
       return connection
   ```
2. **`backend/routes/complaints.py` (Lines 5, 100–133):**
   ```python
   from database import get_connection
   ...
   cursor.execute("""
       INSERT INTO complaints (...) VALUES (...)
   """, (...))
   complaint_id = cursor.lastrowid
   connection.commit()
   ```
3. **`backend/services/vector_service.py` (Lines 4, 23–34):**
   - The only file containing `import psycopg2` and connecting to `os.getenv("POSTGRES_DB")`.
   - Global repository search confirmed that `save_complaint_embedding` and `get_postgres_connection` are never imported or invoked by any route handler.
4. **PostgreSQL Read-Only Metadata Query Output:**
   - Server: `localhost:5432` (`::1`)
   - `current_database()`: `pgvector_code`
   - Relations: Only `public.complaint_embeddings` (2 rows)
   - Columns: `id`, `complaint_id`, `description`, `embedding`, `created_at`
5. **SQLite Read-Only Metadata Query Output:**
   - Location: `database/campuscare.db`
   - Relations: `complaints` (10 rows), `users` (17 rows)
   - Statuses in `complaints`: `Pending` (3), `In Progress` (1), `Resolved` (6)

---

## 16. Root-Cause Hypotheses Ranked by Evidence Strength

### Hypothesis 1: Dual-Database Architectural Split Left Incomplete (Confirmed — Highest Strength)
- **Evidence:** The application was originally prototyped or implemented with SQLite as its operational transactional database (`backend/database.py`). Later, PostgreSQL with `pgvector` was introduced solely for AI/vector search experiments (`backend/services/vector_service.py` and `embedding_service.py`), but:
  1. The core complaint data was never migrated from SQLite to PostgreSQL.
  2. The complaint creation route was never wired to save embeddings or records to PostgreSQL.
  3. Consequently, the user is inspecting PostgreSQL in pgAdmin expecting transactional complaint records, while the backend continues to transact solely against SQLite.

### Hypothesis 2: Incomplete Transition to PostgreSQL / pgAdmin Disconnect (Strong Secondary)
- **Evidence:** `.env` specifies `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB=pgvector_code`, `POSTGRES_USER`, and credentials, leading developers and administrators to believe the entire application runs on PostgreSQL. However, no database migration tool (such as Alembic or Flyway) or PostgreSQL complaint schema was ever implemented for the core application.

---

## 17. Missing Evidence and Limitations

- **No Dedicated Test Environment:** The project contains no automated test suite (`pytest`, `unittest`), mock database, or staging configuration. In strict accordance with the audit guidelines, live write tests (creating synthetic complaints or altering existing complaints) were not executed against the working SQLite database.
- **pgAdmin Session State:** Direct GUI session state in pgAdmin cannot be programmatically observed; however, direct programmatic connection to the exact PostgreSQL server and database configured in `.env` (`pgvector_code` on `localhost:5432`) provided complete ground-truth verification of what pgAdmin displays.

---

## 18. Recommended Minimal Corrective Actions (Non-Destructive Recommendations)

*Note: Per the audit instructions, no files or databases have been modified.*

If the intention is to use PostgreSQL as the primary system of record for CampusCare:

1. **Design and Apply PostgreSQL DDL for Core Tables:**
   - Create `users` and `complaints` tables in PostgreSQL matching the schema currently defined in `backend/database.py`.
2. **Refactor `backend/database.py` Connection Factory:**
   - Update `get_connection()` to establish a `psycopg2` or `asyncpg` connection pool to PostgreSQL instead of SQLite.
   - Adjust SQLite parameterized placeholders (`?`) in `backend/routes/*.py` to PostgreSQL placeholders (`%s`).
3. **Optional Data Migration:**
   - If historical records from `database/campuscare.db` (the 17 users and 10 complaints) are needed in pgAdmin, execute a one-time migration script to export SQLite records and insert them into PostgreSQL.
4. **Wire Vector Service to Complaint Creation (If AI Similarity is Desired):**
   - Call `save_complaint_embedding(complaint_id, description, embedding)` inside `backend/routes/complaints.py:create_complaint` after inserting the complaint.
5. **Alternative — Acknowledge SQLite as the Active Database:**
   - If SQLite was intended for development and PostgreSQL was only for pgvector, open `database/campuscare.db` using a SQLite GUI (such as DB Browser for SQLite or VS Code SQLite Viewer) instead of pgAdmin.
