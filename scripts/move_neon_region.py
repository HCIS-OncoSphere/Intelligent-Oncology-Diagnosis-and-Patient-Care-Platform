"""Copy the shared database from the current Neon project to a new one (e.g. a closer region).

Usage, from the repo root, with the backend's virtualenv:
    1. Create the new Neon project and add its pooled connection string to backend/.env as
       NEW_DATABASE_URL=postgresql://...   (keep the existing DATABASE_URL line as it is)
    2. Ask the team to stop using the app until this finishes.
    3. backend\\.venv\\Scripts\\python.exe scripts\\move_neon_region.py

What it does: checks the new database is empty -> copies all rows out of the old one ->
builds the tables in the new one -> loads the rows -> compares row counts table by table ->
only if every count matches, switches backend/.env to the new database (the old URL is kept
as a comment). Nothing in the old database is changed, so a failed run can simply be retried.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

BACKEND = Path(__file__).resolve().parent.parent / "backend"
ENV_FILE = BACKEND / ".env"
BACKUP = BACKEND / "neon_backup.json"  # git-ignored: real patient data + password hashes
# Rows `migrate` creates by itself in every database; not copied, not compared.
EXCLUDE = ["contenttypes", "auth.Permission", "admin.LogEntry", "sessions"]
SKIP_COUNT = {"contenttypes.ContentType", "auth.Permission", "admin.LogEntry", "sessions.Session"}
COUNT_SNIPPET = (
    "import json; from django.apps import apps; "
    "print(json.dumps({m._meta.label: m._base_manager.count() for m in apps.get_models() "
    "if m._meta.managed and not m._meta.proxy}))"
)


def fail(msg):
    sys.exit(f"\nSTOPPED: {msg}")


def read_env():
    values = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def manage(url, *args, capture=False):
    env = {**os.environ, "DATABASE_URL": url, "PYTHONUTF8": "1"}  # UTF-8 keeps Arabic text intact
    env.pop("USE_SQLITE", None)
    r = subprocess.run([sys.executable, "-X", "utf8", "manage.py", *args], cwd=BACKEND, env=env,
                       capture_output=capture, text=True, encoding="utf-8")
    if r.returncode != 0:
        fail(f"`manage.py {' '.join(args[:1])}` failed" + (f":\n{r.stderr}" if capture else " (see the error above)."))
    return r.stdout if capture else None


def counts(url):
    out = manage(url, "shell", "-c", COUNT_SNIPPET, capture=True)
    data = json.loads(out.strip().splitlines()[-1])
    return {k: v for k, v in data.items() if k not in SKIP_COUNT}


def new_db_is_empty(url):
    import psycopg
    with psycopg.connect(url) as conn:
        n = conn.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'").fetchone()[0]
    return n == 0


def switch_env(old_url, new_url):
    lines = []
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        key = line.split("=", 1)[0].strip()
        if key == "DATABASE_URL":
            lines.append(f"# Old Neon project ({urlparse(old_url).hostname}), before the region move:")
            lines.append("# " + line)
            lines.append(f"DATABASE_URL={new_url}")
        elif key == "NEW_DATABASE_URL":
            continue
        else:
            lines.append(line)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if not ENV_FILE.exists():
        fail(f"{ENV_FILE} not found.")
    env = read_env()
    old, new = env.get("DATABASE_URL", ""), env.get("NEW_DATABASE_URL", "")
    if not old or not new:
        fail("backend/.env needs both DATABASE_URL (current database) and NEW_DATABASE_URL (new project).")
    old_host, new_host = urlparse(old).hostname, urlparse(new).hostname
    if old_host == new_host:
        fail("DATABASE_URL and NEW_DATABASE_URL point to the same server.")
    print(f"From: {old_host}\nTo:   {new_host}\n")

    print("1/5 Checking the new database is empty ...")
    if not new_db_is_empty(new):
        fail("the new database already has tables. Use a fresh Neon project (or drop its tables) and run again.")

    print("2/5 Copying all rows out of the old database ...")
    manage(old, "dumpdata", "--natural-foreign", "--natural-primary",
           *[a for e in EXCLUDE for a in ("-e", e)], "--indent", "2", "-o", str(BACKUP))
    before = counts(old)

    print("3/5 Building the tables in the new database ...")
    manage(new, "migrate", "--noinput")

    print("4/5 Loading the rows into the new database ...")
    manage(new, "loaddata", str(BACKUP))

    print("5/5 Comparing row counts ...")
    after = counts(new)
    bad = {k: (before.get(k, 0), after.get(k, 0)) for k in set(before) | set(after) if before.get(k, 0) != after.get(k, 0)}
    for k in sorted(before):
        if before[k]:
            print(f"   {before[k]:6} {k}")
    if bad:
        for k, (b, a) in sorted(bad.items()):
            print(f"   MISMATCH {k}: old={b} new={a}")
        fail("row counts differ, so backend/.env was NOT switched. The old database is untouched.")

    switch_env(old, new)
    print(f"\nDone: all {sum(before.values())} rows copied and backend/.env now uses {new_host}.")
    print("Next: restart runserver, log in to check, send the new DATABASE_URL to the team privately,")
    print(f"and delete {BACKUP.name} once you're sure (it contains real patient data).")


if __name__ == "__main__":
    main()
