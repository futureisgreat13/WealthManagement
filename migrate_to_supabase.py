#!/usr/bin/env python3
"""One-time migration script: Upload local user data to Supabase.

Usage:
    python3 migrate_to_supabase.py

Requires SUPABASE_URL and SUPABASE_KEY environment variables, or
reads from .streamlit/secrets.toml.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
USERS_DIR = DATA_DIR / "users"


def get_supabase_client():
    """Create Supabase client from env vars or secrets.toml."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        # Try reading from secrets.toml
        secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
        if secrets_path.exists():
            import tomllib
            with open(secrets_path, "rb") as f:
                secrets = tomllib.load(f)
            sb = secrets.get("supabase", {})
            url = url or sb.get("url")
            key = key or sb.get("key")

    if not url or not key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_KEY env vars, or add [supabase] to .streamlit/secrets.toml")
        sys.exit(1)

    from supabase import create_client
    return create_client(url, key)


def migrate_user(client, user_dir: Path):
    """Upload all JSON files for a single user to Supabase."""
    email = user_dir.name
    files = sorted(user_dir.glob("*.json"))
    skipped = 0
    uploaded = 0

    for json_file in files:
        if json_file.name.startswith("_"):
            skipped += 1
            continue

        try:
            with open(json_file) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  SKIP {json_file.name}: {e}")
            skipped += 1
            continue

        try:
            client.table("user_data").upsert({
                "user_email": email,
                "file_name": json_file.name,
                "data": data,
                "updated_at": datetime.now().isoformat(),
            }, on_conflict="user_email,file_name").execute()
            uploaded += 1
            print(f"  ✅ {json_file.name}")
        except Exception as e:
            print(f"  ❌ {json_file.name}: {e}")

    return uploaded, skipped


def main():
    client = get_supabase_client()
    print(f"Connected to Supabase\n")

    if not USERS_DIR.exists():
        print(f"No users directory found at {USERS_DIR}")
        sys.exit(1)

    user_dirs = sorted([d for d in USERS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")])
    print(f"Found {len(user_dirs)} user(s) to migrate:\n")

    total_uploaded = 0
    for user_dir in user_dirs:
        email = user_dir.name
        files = list(user_dir.glob("*.json"))
        print(f"📧 {email} ({len(files)} files)")
        uploaded, skipped = migrate_user(client, user_dir)
        total_uploaded += uploaded
        print(f"  Uploaded: {uploaded}, Skipped: {skipped}\n")

    print(f"✅ Migration complete! {total_uploaded} files uploaded to Supabase.")


if __name__ == "__main__":
    main()
