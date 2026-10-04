import os

from sqlalchemy import String, create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


# ---------------------------------------------------------------------------
# 1. THE MODEL
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Base class for all models. It collects table definitions in
    Base.metadata, which SQLAlchemy uses to create the tables."""
    pass


class User(Base):
    """Each instance of this class represents one row in the `users` table."""

    __tablename__ = "users"

    # Auto-incrementing integer primary key.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # unique=True  -> the database rejects duplicate usernames
    # nullable=False -> the column is NOT NULL (Mapped[str] already implies
    #                   this, but being explicit helps beginners read it)
    # MySQL needs a length for VARCHAR columns, hence String(50).
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    def __repr__(self) -> str:
        # Makes print(user) readable while debugging.
        return f"User(id={self.id!r}, username={self.username!r}, email={self.email!r})"


# ---------------------------------------------------------------------------
# 2. ENGINE, TABLE CREATION, SESSION
# ---------------------------------------------------------------------------
def create_db_engine():
    """Build the Engine, which manages the connection pool to the database."""
    # Read the password from an environment variable instead of hard-coding
    # it in the source file (never commit passwords to version control).
    url = URL.create(
        drivername="mysql+mysqlconnector",   # dialect + driver
        username="root",
        password=os.environ.get("DB_PASSWORD", "yourpassword"),
        host="localhost",
        database="example_db",
    )
    # URL.create() safely escapes special characters in the password.
    # pool_pre_ping=True checks that a pooled connection is alive before use.
    return create_engine(url, echo=False, pool_pre_ping=True)


def create_user(session: Session, username: str, email: str) -> User | None:
    """Add a new user. Rolls back and returns None if something goes wrong."""
    if not username or not email:
        print("Username and email are required.")
        return None

    user = User(username=username, email=email)
    try:
        session.add(user)    # stage the new object (no SQL sent yet)
        session.commit()     # send INSERT and make it permanent
        print(f"User '{username}' created successfully.")
        return user
    except IntegrityError:
        # Raised when a UNIQUE or NOT NULL constraint is violated,
        # e.g. the username or email already exists.
        session.rollback()   # undo the failed transaction
        print(f"Error: username '{username}' or email '{email}' already exists.")
    except SQLAlchemyError as e:
        # Any other database-related problem.
        session.rollback()
        print(f"Database error while creating user: {e}")
    return None


def get_user_by_username(session: Session, username: str) -> User | None:
    """Find one user by username using the 2.0-style select() statement."""
    # Builds: SELECT ... FROM users WHERE users.username = ?
    # The value is sent as a bound parameter, never pasted into the SQL.
    stmt = select(User).where(User.username == username)
    try:
        # scalars() unwraps rows into User objects.
        # one_or_none() returns the User, or None if not found.
        # (Safe because username is unique, so at most one row matches.)
        return session.scalars(stmt).one_or_none()
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Database error while querying user: {e}")
        return None


def main():
    engine = create_db_engine()

    # Create the `users` table from the model if it doesn't exist yet.
    # Existing tables are left untouched.
    Base.metadata.create_all(engine)

    # The `with` block guarantees the session is closed (and its connection
    # returned to the pool) even if an exception occurs.
    with Session(engine) as session:
        create_user(session, "alice", "alice@example.com")

        user = get_user_by_username(session, "alice")
        if user:
            print("Found:", user)
        else:
            print("User not found.")


if __name__ == "__main__":
    main()
