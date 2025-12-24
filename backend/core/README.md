# Vidnag Core Systems

This directory contains core, always-on systems that are not plugins.

## Components

### Settings Manager (`settings.py`)

Manages three-tier configuration system with security levels:

- **APP**: High-risk settings (secrets, DB credentials)
- **ADMIN**: Medium-risk settings (operational config)
- **USER**: Low-risk settings (UI preferences)

**Usage:**
```python
from backend.core.settings import settings, SettingsLevel

# Get a setting
db_host = settings.get(SettingsLevel.APP, "database.host")
version = settings.get_version()

# Set admin setting (only ADMIN and USER levels)
settings.set(SettingsLevel.ADMIN, "videos.max_upload_size_mb", 1000, admin_user_id=1)

# Check plugin status
if settings.is_plugin_enabled("ratelimit"):
    # ...
```

**Features:**
- JSON schema validation
- File permission checking
- Critical plugin protection
- Automatic backups (admin.json)
- Hot-reload support

### Logging System (`logging.py`)

Structured logging with three separate log files:

- **admin.log**: Admin actions and changes
- **user.log**: User activity
- **app.log**: System events

**Usage:**
```python
from backend.core.logging import init_logger, get_logger

# Initialize (do once at app startup)
logger = init_logger(settings)

# Get logger instance
logger = get_logger()

# Admin logs
logger.log_admin_action("settings_change", admin_id=1, target="ratelimit.enabled", ip="192.168.1.1")
logger.log_admin_login(admin_id=1, username="admin", ip="192.168.1.1", success=True)

# User logs
logger.log_user_login(user_id=42, username="alice", ip="192.168.1.100", success=True)
logger.log_video_upload(user_id=42, filename="vacation.mp4", size=52428800, ip="192.168.1.100")

# Application logs
logger.log_startup(version="0.1.0", debug_mode=False)
logger.log_video_processing(video_id=123, job_type="transcode", status="completed")
logger.log_error(Exception("DB connection failed"), context="database")
```

**Features:**
- Daily log rotation
- Configurable retention (default 7 days)
- Sensitive field redaction (passwords, tokens, secrets)
- Browser debug streaming (opt-in via admin settings)
- Three separate log levels (admin, user, application)

**Browser Debug:**

Admins can enable real-time log streaming to browser consoles:

1. Enable in `settings/admin.json`:
```json
{
  "logging": {
    "browser_debug": {
      "enabled": true,
      "allowed_user_ids": [1, 2],  // Empty = all admins
      "log_levels": ["ERROR", "WARNING", "INFO"]
    }
  }
}
```

2. Use API endpoint (will be implemented):
```javascript
// Subscribe to logs
GET /api/admin/logs/stream?user_id=1

// Returns SSE stream of log messages
```

**Security:**
- Sensitive fields automatically redacted
- Browser debug requires admin permission
- Can restrict to specific user IDs
- Logs stored with proper permissions

### File Validation (Coming Next)

Will provide:
- MIME type verification
- File size checking
- Malware scanning
- Filename sanitization
- Content validation

## Integration

All core systems are initialized at application startup:

```python
from backend.core.settings import settings
from backend.core.logging import init_logger

# Initialize
logger = init_logger(settings)

# Use throughout app
logger.log_startup(settings.get_version(), settings.get(SettingsLevel.APP, "security.debug_mode"))
```
