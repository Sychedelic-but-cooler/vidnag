"""
Vidnag Main Application
FastAPI application with plugin system, logging, and database
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

# Core systems
from backend.core.settings import settings, SettingsLevel
from backend.core.logging import init_logger, get_logger
from backend.core.database import init_db, get_db
from backend.core.ip_extraction import IPExtractor, IPExtractionMiddleware

# Plugin system
from backend.plugins.manager import PluginManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger = get_logger()
    logger.log_startup(
        version=settings.get_version(),
        debug_mode=settings.get(SettingsLevel.APP, "security.debug_mode", False)
    )

    # Start plugins
    app.state.plugin_manager.startup_plugins()

    logger.app.info("Vidnag application started successfully")

    yield

    # Shutdown
    logger.app.info("Shutting down Vidnag...")

    # Shutdown download manager
    if hasattr(app.state, 'download_manager'):
        logger.app.info("Shutting down download manager...")
        app.state.download_manager.shutdown(wait=True, timeout=30.0)
        logger.app.info("Download manager shutdown complete")

    # Shutdown plugins
    app.state.plugin_manager.shutdown_plugins()

    # Dispose database connections
    db = get_db()
    db.dispose()

    logger.log_shutdown()


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application

    Returns:
        FastAPI: Configured application instance
    """

    # Initialize core systems
    logger = init_logger(settings)
    db = init_db(settings)

    logger.app.info(
        f"Initializing {settings.get_app_name()} v{settings.get_version()}"
    )

    # Create FastAPI app
    app = FastAPI(
        title=settings.get_app_name(),
        version=settings.get_version(),
        description="Video download, processing, and sharing platform",
        lifespan=lifespan
    )

    # === CORE IP EXTRACTION (Always Active) ===
    # This runs BEFORE all plugins
    logger.app.info("Setting up core IP extraction...")

    # Get proxy configuration (if proxy plugin is enabled)
    if settings.is_plugin_enabled("proxy"):
        proxy_config = settings.get_plugin_config("proxy")
        trusted_proxies = proxy_config.get('trusted_proxies', [])
        proxy_headers = proxy_config.get('headers', ['X-Forwarded-For', 'X-Real-IP'])
        logger.app.info(f"Using proxy configuration: {len(trusted_proxies)} trusted proxies")
    else:
        trusted_proxies = None
        proxy_headers = None
        logger.app.info("No proxy configuration - using direct connection IP")

    # Create IP extractor
    ip_extractor = IPExtractor(
        trusted_proxies=trusted_proxies,
        proxy_headers=proxy_headers
    )

    # Add IP extraction middleware (always active, runs first)
    app.add_middleware(IPExtractionMiddleware, extractor=ip_extractor)
    logger.app.info("Core IP extraction active")

    # === PLUGIN SYSTEM ===
    logger.app.info("Loading plugins...")

    # Create plugin manager
    plugin_manager = PluginManager(settings, logger)

    # Discover and load plugins
    plugin_manager.discover_plugins()

    # Initialize plugins (adds their middleware and routes)
    plugin_manager.initialize_plugins(app)

    # Store plugin manager in app state
    app.state.plugin_manager = plugin_manager

    logger.app.info(f"Loaded {len(plugin_manager.get_loaded_plugins())} plugins")

    # === DOWNLOAD SERVICE ===
    logger.app.info("Initializing download service...")

    from backend.workers.download_manager import DownloadManager
    from backend.services.video_download_service import VideoDownloadService

    download_manager = DownloadManager(settings, db, logger)
    download_service = VideoDownloadService(settings, db, download_manager, logger)

    app.state.download_manager = download_manager
    app.state.download_service = download_service

    logger.app.info("Download service initialized")

    # === API ROUTES ===
    # Include auth routes
    from backend.routes import auth
    app.include_router(auth.router)

    # Include video routes
    from backend.routes import videos
    app.include_router(videos.router)

    logger.app.info("API routes registered")

    # === STATIC FILES ===
    # Mount static files for frontend
    frontend_dir = Path(__file__).parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
        logger.app.info("Static files mounted")

    # === CORE ROUTES ===

    @app.get("/")
    async def root():
        """Root endpoint - serve login page"""
        login_page = Path(__file__).parent.parent / "frontend" / "login.html"
        if login_page.exists():
            return FileResponse(login_page)
        else:
            return {
                "app": settings.get_app_name(),
                "version": settings.get_version(),
                "status": "running"
            }

    @app.get("/app")
    async def main_app():
        """Main application page - requires authentication"""
        main_page = Path(__file__).parent.parent / "frontend" / "main.html"
        if main_page.exists():
            return FileResponse(main_page)
        else:
            return JSONResponse(
                status_code=404,
                content={"error": "Main application page not found"}
            )

    @app.get("/health")
    async def health(request: Request):
        """Health check endpoint"""
        from backend.core.ip_extraction import get_client_ip

        return {
            "status": "healthy",
            "version": settings.get_version(),
            "client_ip": get_client_ip(request),
            "plugins": plugin_manager.get_loaded_plugins()
        }

    @app.get("/api/info")
    async def info():
        """Application information"""
        return {
            "name": settings.get_app_name(),
            "version": settings.get_version(),
            "plugins": {
                name: {
                    "version": plugin.version,
                    "description": plugin.description
                }
                for name, plugin in plugin_manager.plugins.items()
            }
        }

    # === ERROR HANDLERS ===

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Handle 404 errors"""
        return JSONResponse(
            status_code=404,
            content={"error": "Not found", "path": request.url.path}
        )

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        """Handle 500 errors"""
        logger.log_error(exc, context="request_handler", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

    logger.app.info("Vidnag application configured successfully")

    return app


# Create application instance
app = create_app()


# === DEV/DEBUG ENDPOINTS ===

if settings.get(SettingsLevel.APP, "security.debug_mode", False):
    @app.get("/debug/pool-status")
    async def debug_pool_status():
        """Debug endpoint: Database connection pool status"""
        db = get_db()
        return db.get_pool_status()

    @app.get("/debug/plugins")
    async def debug_plugins():
        """Debug endpoint: Plugin information"""
        plugin_manager = app.state.plugin_manager
        return {
            "loaded": plugin_manager.get_loaded_plugins(),
            "load_order": plugin_manager.load_order,
            "details": {
                name: {
                    "name": plugin.name,
                    "version": plugin.version,
                    "description": plugin.description,
                    "enabled": plugin.enabled,
                    "priority": plugin.priority,
                    "dependencies": plugin.dependencies
                }
                for name, plugin in plugin_manager.plugins.items()
            }
        }
