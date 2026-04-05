#!/bin/bash

# Change to the directory where this script is located
# This way we don't expose the real path
cd "$(dirname "$0")" || exit 1

# Load variables from the .env.docker file
if [ -f .env.docker ]; then
    # The export command makes variables available to the script
    export $(grep -v '^#' .env.docker | xargs)
else
    echo "Error: File .env.docker not found!"
    exit 1
fi

# Create backup file name with current date and time
BACKUP_FILE="backups/backup_$(date +%Y%m%d_%H%M%S).sql.gz"

# Create a database dump and compress it with gzip
# Variables are taken from .env.docker file
docker compose --env-file .env.docker exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$BACKUP_FILE"

# Delete old backup files (older than 7 days)
find backups/ -type f -name "backup_*.sql.gz" -mtime +7 -delete
