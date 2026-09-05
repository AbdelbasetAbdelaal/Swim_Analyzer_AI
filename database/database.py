import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# Ensure the data directory exists
os.makedirs("data", exist_ok=True)

SQLALCHEMY_DATABASE_URL = "sqlite:///data/swim_analyzer.db"

# connect_args={"check_same_thread": False} is needed only for SQLite.
# If migrating to Postgres, remove connect_args.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable SQLite WAL mode and synchronous=NORMAL for robust concurrency."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()
    except Exception:
        pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """Initializes tables and performs schema migrations if needed."""
    from database.models import Base
    Base.metadata.create_all(bind=engine)
    
    # Lightweight SQLite schema migration for coach_id column in athletes table
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("PRAGMA table_info(athletes)"))
            columns = [row[1] for row in result.fetchall()]
            if "coach_id" not in columns:
                conn.execute(text("ALTER TABLE athletes ADD COLUMN coach_id VARCHAR"))
                conn.commit()
            coach_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(coaches)")).fetchall()]
            if "role" not in coach_columns:
                conn.execute(text("ALTER TABLE coaches ADD COLUMN role VARCHAR DEFAULT 'coach'"))
                conn.commit()
                conn.execute(text("UPDATE coaches SET role = 'coach' WHERE role IS NULL"))
                conn.commit()
            # Safely identify orphaned athletes but do not automatically assign ownership
            orphaned_athletes = conn.execute(text("SELECT COUNT(*) FROM athletes WHERE coach_id IS NULL")).fetchone()[0]
            if orphaned_athletes > 0:
                import logging
                logging.getLogger(__name__).warning(f"Found {orphaned_athletes} orphaned athletes with NULL coach_id. Manual admin migration required.")
            # Migration for account_id column in analysis_sessions table
            res_sess = conn.execute(text("PRAGMA table_info(analysis_sessions)"))
            sess_cols = [row[1] for row in res_sess.fetchall()]
            if "account_id" not in sess_cols:
                conn.execute(text("ALTER TABLE analysis_sessions ADD COLUMN account_id VARCHAR"))
                conn.commit()
            if "benchmark_summary_json" not in sess_cols:
                conn.execute(text("ALTER TABLE analysis_sessions ADD COLUMN benchmark_summary_json TEXT"))
                conn.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Database migration failed: {e}")
        raise e

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
