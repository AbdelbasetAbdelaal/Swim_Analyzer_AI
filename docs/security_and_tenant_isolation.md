# Security & Multi-Tenant Isolation Architecture

## 1. Executive Summary
This document defines the security architecture and multi-tenant isolation guarantees implemented in **SwimAnalyzer AI**.

---

## 2. Core Security Invariants

### 2.1 Domain Model Ownership Invariants
- `AthleteProfile`: `coach_id: str` is **strictly required**. Unassigned or orphaned profiles are rejected at model construction.
- `AnalysisSession`: `account_id: str` is **strictly required**. Anonymous analysis sessions cannot be instantiated or persisted.

### 2.2 Database Authorization & Multi-Tenancy
- **Deny-by-Default Querying**: All session queries (`AnalysisHistoryService.get_all_sessions(principal)`) require an authenticated principal (`CoachProfile`).
- **Cross-Tenant Access Protection**: Requests attempting to query or modify resources belonging to another coach/account return empty sets or fail authorization without leaking existence.
- **Explicit Ownership Assignment**: When creating or saving sessions and athlete profiles, ownership is derived directly from the authenticated session context (`st.session_state.current_coach`), never from untrusted client parameters.

### 2.3 File System & Path Traversal Protections
- **Sanitization Utility (`utils.file_security.py`)**:
  - Filenames are sanitized via `os.path.basename` to eliminate relative path components (`../`, `..\`).
  - Target paths are resolved to absolute paths via `Path.resolve()`.
  - Directory boundary containment is validated using `Path.relative_to(target_dir)`, raising `ValueError` on any traversal attempt.
  - Exported files (JSON reports, metadata, timeline data, PDF reports) receive server-generated UUID names.

### 2.4 Credential Security & Password Hashing
- Hardcoded default passwords have been completely removed from production code and UI components.
- Passwords are encrypted using **Argon2id** (memory-hard, resistant to GPU/ASIC cracking) with per-user unique cryptographic salt.
- Initial administrative and coach bootstrap accounts are configured via environment variables (`SWIM_ANALYZER_BOOTSTRAP_*`) defined in `.env`.

### 2.5 Deterministic Database Session Lifecycle & WAL Mode
- SQLAlchemy database connections utilize deterministic context managers (`__enter__`, `__exit__`) and explicit `.close()` disposals to eliminate connection pooling leaks.
- SQLite is tuned with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) and `PRAGMA synchronous=NORMAL;` for high concurrency without database lockups.

---

## 3. Verification & Test Evidence

| Security Boundary Test | Target | Status |
| :--- | :--- | :--- |
| `tests/test_tenant_isolation.py` | Orphaned athlete deny-by-default, cross-tenant query attack protection | ✅ **PASSED** |
| `tests/test_models_regression.py` | Required domain model ownership fields (`coach_id`, `account_id`) | ✅ **PASSED** |
| `tests/test_dashboard_regression.py` | Principal propagation in UI / Dashboard session queries & N+1 fix | ✅ **PASSED** |
| `tests/test_auth_migration.py` | Argon2id verification and fallback prevention | ✅ **PASSED** |
| `utils/file_security.py` | Path traversal rejection and directory containment | ✅ **PASSED** |

