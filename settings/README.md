# Vidnag Settings Directory

This directory contains all configuration files for Vidnag.

## File Structure

```
settings/
├── app.json              # HIGH-RISK: Core app config (chmod 600)
├── admin.json            # MEDIUM-RISK: Admin settings (chmod 640)
├── user.json             # LOW-RISK: User preferences (chmod 644)
├── defaults/             # Default templates
│   ├── app.default.json
│   ├── admin.default.json
│   └── user.default.json
├── schema/               # JSON schemas for validation
│   ├── app.schema.json
│   ├── admin.schema.json
│   └── user.schema.json
└── backups/              # Automatic backups of admin.json
```

## Security Levels

### HIGH-RISK (app.json)
- Only editable via filesystem by system administrator
- Requires application restart to take effect
- Contains: secrets, database credentials, core security settings
- File permissions: `chmod 600` (rw-------)

### MEDIUM-RISK (admin.json)
- Editable via web admin interface
- Hot-reloads without restart (with safeguards)
- Contains: operational settings, feature flags, resource limits
- File permissions: `chmod 640` (rw-r-----)
- Automatically backed up on each change

### LOW-RISK (user.json)
- Defaults for all users (per-user overrides stored in database)
- Readable by all
- Contains: UI preferences, display settings
- File permissions: `chmod 644` (rw-r--r--)

## Initial Setup

1. Copy default files to create active configuration:
```bash
cp settings/defaults/app.default.json settings/app.json
cp settings/defaults/admin.default.json settings/admin.json
cp settings/defaults/user.default.json settings/user.json
```

2. Set proper permissions:
```bash
chmod 600 settings/app.json
chmod 640 settings/admin.json
chmod 644 settings/user.json
```

3. Edit `settings/app.json` and change:
   - `security.secret_key` to a secure random key (min 32 chars)
   - `database.password` to your PostgreSQL password
   - `security.allowed_hosts` to your domain(s)
   - `storage.base_path` and `storage.temp_path` to desired locations

## Generating Secure Secret Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Version

Current Vidnag version: 0.1.0
