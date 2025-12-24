#!/usr/bin/env python3
"""
Vidnag Development Server
Run the Vidnag application with uvicorn
"""

import sys
import uvicorn
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.core.settings import settings, SettingsLevel


def main():
    """Run the development server"""
    host = settings.get(SettingsLevel.APP, "server.host", "0.0.0.0")
    port = settings.get(SettingsLevel.APP, "server.port", 8000)
    reload = settings.get(SettingsLevel.APP, "server.reload", False)
    workers = settings.get(SettingsLevel.ADMIN, "server.workers", 1) if not reload else 1

    print("=" * 60)
    print(f"  Vidnag v{settings.get_version()}")
    print("=" * 60)
    print()
    print(f"  Server: http://{host}:{port}")
    print(f"  Docs:   http://{host}:{port}/docs")
    print(f"  Health: http://{host}:{port}/health")
    print()
    print(f"  Workers: {workers}")
    print(f"  Reload:  {reload}")
    print()
    print("=" * 60)
    print()

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level="info"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        sys.exit(0)
