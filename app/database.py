import peewee as pw
import logging
from contextlib import contextmanager

logger = logging.getLogger("forex_service")

# Define the database. Using SQLite for simplicity.
# The database file will be created in the `app` directory.
db = pw.SqliteDatabase("forex_signals.db")

def initialize_db():
    """Connects to the database and creates tables if they don't exist."""
    try:
        db.connect()
        logger.info("Database connection established.")
        # Peewee's create_tables has a `safe=True` option to prevent
        # errors if the table already exists
        from models.model import SignalHistory # Import here to avoid circular dependency
        db.create_tables([SignalHistory], safe=True)
        logger.info("Database tables created or already exist.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    finally:
            db.close()
            logger.info("Database connection closed.")

@contextmanager
def db_context():
    """A context manager to handle database connection and disconnection."""
    try:
        db.connect(reuse_if_open=True)
        yield
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        if not db.is_closed():
            db.close()

def db_wrapper(func):
    def wrapper(*args, **kwargs): 
        with db_context():
            return func(*args, **kwargs)
    return wrapper
