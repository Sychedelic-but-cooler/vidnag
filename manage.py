#!/usr/bin/env python3
"""
Vidnag Database Management CLI
Handles database migrations, initialization, and maintenance
"""

import sys
import subprocess
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.core.settings import settings
from backend.core.database import init_db, get_db
from backend.core.logging import init_logger, get_logger


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def run_alembic_command(args: list) -> int:
    """Run an Alembic command"""
    cmd = ["alembic"] + args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def init_database():
    """Initialize database system"""
    print_header("Initializing Database")

    # Initialize logger
    logger = init_logger(settings)
    logger.log_startup(settings.get_version(), False)

    # Initialize database
    db = init_db(settings)
    logger.app.info("Database connection established")

    return db, logger


def cmd_init():
    """Initialize a new database (first time setup)"""
    print_header("First-Time Database Setup")

    db, logger = init_database()

    print("1. Creating initial migration...")
    result = run_alembic_command(["revision", "--autogenerate", "-m", "Initial migration"])
    if result != 0:
        print("❌ Failed to create initial migration")
        return 1

    print("\n2. Applying migration...")
    result = run_alembic_command(["upgrade", "head"])
    if result != 0:
        print("❌ Failed to apply migration")
        return 1

    logger.app.info("Database initialized successfully")
    print("\n✅ Database initialized successfully!")
    return 0


def cmd_migrate(message: str = None):
    """
    Auto-detect model changes and create a new migration

    This will:
    1. Compare current models to database schema
    2. Generate migration file if changes detected
    3. Report what changed
    """
    print_header("Detecting Schema Changes")

    db, logger = init_database()

    if not message:
        message = input("Migration message (or press Enter for auto): ").strip()
        if not message:
            message = "Auto-detected schema changes"

    print(f"Creating migration: {message}")
    result = run_alembic_command(["revision", "--autogenerate", "-m", message])

    if result == 0:
        logger.app.info(f"Migration created: {message}")
        print("\n✅ Migration created successfully!")
        print("\nNext steps:")
        print("  1. Review the migration file in alembic/versions/")
        print("  2. Run: python manage.py upgrade")
    else:
        logger.app.error("Failed to create migration")
        print("\n❌ Failed to create migration")

    return result


def cmd_upgrade(revision: str = "head"):
    """
    Apply pending migrations

    Args:
        revision: Target revision (default: head = latest)
    """
    print_header(f"Applying Migrations (target: {revision})")

    db, logger = init_database()

    print("Current database state:")
    run_alembic_command(["current"])

    print(f"\nUpgrading to {revision}...")
    result = run_alembic_command(["upgrade", revision])

    if result == 0:
        logger.app.info(f"Database upgraded to {revision}")
        print("\n✅ Database upgraded successfully!")

        print("\nNew database state:")
        run_alembic_command(["current"])
    else:
        logger.app.error("Failed to upgrade database")
        print("\n❌ Failed to upgrade database")

    return result


def cmd_downgrade(revision: str):
    """
    Rollback migrations

    Args:
        revision: Target revision (e.g., -1 for one down, base for all down)
    """
    print_header(f"Rolling Back to {revision}")

    db, logger = init_database()

    print("⚠️  WARNING: This will modify your database schema!")
    confirm = input("Are you sure? (yes/no): ").strip().lower()

    if confirm != "yes":
        print("Cancelled.")
        return 0

    result = run_alembic_command(["downgrade", revision])

    if result == 0:
        logger.app.warning(f"Database downgraded to {revision}")
        print("\n✅ Database downgraded successfully!")
    else:
        logger.app.error("Failed to downgrade database")
        print("\n❌ Failed to downgrade database")

    return result


def cmd_current():
    """Show current migration revision"""
    print_header("Current Database State")
    return run_alembic_command(["current", "-v"])


def cmd_history():
    """Show migration history"""
    print_header("Migration History")
    return run_alembic_command(["history", "-v"])


def cmd_check():
    """Check for pending migrations"""
    print_header("Checking for Pending Migrations")

    db, logger = init_database()

    print("Current state:")
    run_alembic_command(["current"])

    print("\nComparing with models...")
    # This will show what would be generated
    result = run_alembic_command(["revision", "--autogenerate", "-m", "Check", "--sql"])

    return result


def cmd_status():
    """Show database and connection status"""
    print_header("Database Status")

    try:
        db, logger = init_database()

        print("✅ Database connection: OK")
        print(f"   Version: {settings.get_version()}")
        print(f"   Database: {settings.get('APP', 'database.name')}")
        print(f"   Host: {settings.get('APP', 'database.host')}")

        # Show pool status
        pool_status = db.get_pool_status()
        print(f"\n📊 Connection Pool:")
        print(f"   Size: {pool_status['size']}")
        print(f"   In use: {pool_status['checked_out']}")
        print(f"   Available: {pool_status['checked_in']}")
        print(f"   Overflow: {pool_status['overflow']}")

        # Show current migration
        print(f"\n📋 Migrations:")
        run_alembic_command(["current", "-v"])

        return 0

    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        return 1


def print_help():
    """Print help message"""
    print("""
Vidnag Database Management

Usage: python manage.py <command> [options]

Commands:

  init              First-time database setup (creates and applies initial migration)
  migrate [msg]     Auto-detect model changes and create migration
  upgrade [rev]     Apply pending migrations (default: all)
  downgrade <rev>   Rollback to a specific revision
  current           Show current migration revision
  history           Show migration history
  check             Check for pending migrations without applying
  status            Show database and connection status

Examples:

  # First time setup
  python manage.py init

  # After changing models
  python manage.py migrate "Added user preferences table"
  python manage.py upgrade

  # Check status
  python manage.py status
  python manage.py current

  # Rollback one migration
  python manage.py downgrade -1

  # Rollback all migrations
  python manage.py downgrade base

Auto-Migration:
  This system automatically detects:
  - New tables and columns
  - Removed tables and columns
  - Modified column types
  - Changed indexes
  - Altered constraints

  Simply:
  1. Edit models in backend/models.py
  2. Run: python manage.py migrate
  3. Review the generated migration in alembic/versions/
  4. Run: python manage.py upgrade
""")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print_help()
        return 1

    command = sys.argv[1].lower()

    try:
        if command == "init":
            return cmd_init()

        elif command == "migrate":
            message = sys.argv[2] if len(sys.argv) > 2 else None
            return cmd_migrate(message)

        elif command == "upgrade":
            revision = sys.argv[2] if len(sys.argv) > 2 else "head"
            return cmd_upgrade(revision)

        elif command == "downgrade":
            if len(sys.argv) < 3:
                print("Error: downgrade requires a revision argument")
                print("Examples: -1 (one down), base (all down)")
                return 1
            return cmd_downgrade(sys.argv[2])

        elif command == "current":
            return cmd_current()

        elif command == "history":
            return cmd_history()

        elif command == "check":
            return cmd_check()

        elif command == "status":
            return cmd_status()

        elif command in ["help", "-h", "--help"]:
            print_help()
            return 0

        else:
            print(f"Unknown command: {command}")
            print_help()
            return 1

    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        return 130

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
