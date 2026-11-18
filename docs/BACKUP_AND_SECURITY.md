# Backup and sensitive-data protection plan (Phase 2)

## Backup
- `scripts/backup.sh` runs `pg_dump`, compresses the result and deletes backups older than 14 days.
- Schedule it daily with cron (`0 2 * * *`). Copy the backup folder to a second location (another disk or cloud bucket).
- Restore test: `gunzip -c backup.sql.gz | psql -h HOST -U USER oncosphere`. Run it on a test database once per sprint.

## Sensitive data
| Risk | Control in the code |
|---|---|
| Stolen passwords | Django hashes passwords (PBKDF2); only hashes are stored |
| Unauthorized access | JWT login, role-based permissions (Admin / Clinical Staff / Patient); patients only see their own data |
| Tampering and accountability | `AuditLog` records every successful write with user, path and IP (admin-only view) |
| Secrets in code | `SECRET_KEY` and DB credentials come from environment variables |
| Transport | Run behind HTTPS in production (reverse proxy), set `DEBUG=0` |
| Database access | Create a dedicated DB user with rights on the `oncosphere` database only |
| Test data | Only synthetic data is seeded (`python manage.py seed`) |
