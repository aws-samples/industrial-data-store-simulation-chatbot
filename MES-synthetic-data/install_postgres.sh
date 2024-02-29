#!/bin/bash

# Update your system's repository index
sudo dnf update -y

# Install jq for json processing
sudo dnf install jq -y 

# Install PostgreSQL client and server
sudo dnf install postgresql15 postgresql15-server -y

# Initialize the database
sudo postgresql-setup --initdb

# Start and enable PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Wait a moment for PostgreSQL to fully start
sleep 5

# Setup database and user
DB_USER=$(jq -r '.user' postgres_creds.json)
DB_PASS=$(jq -r '.pwd' postgres_creds.json)
DB_NAME=$(jq -r '.db_name' postgres_creds.json)

# Create a PostgreSQL role named "$DB_USER" with "$DB_PASS" as the password
# and then create a database "$DB_NAME" owned by "$DB_USER"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME WITH OWNER $DB_USER;"

# Modify pg_hba.conf to allow password authentication
PG_HBA_CONF_PATH="/var/lib/pgsql/data/pg_hba.conf"
sudo sed -i "s/host\s*all\s*all\s*127.0.0.1\/32\s*ident/host all all 127.0.0.1\/32 md5/" $PG_HBA_CONF_PATH # username/password (md5) for local connections

# Reload the PostgreSQL service to apply pg_hba.conf changes
sudo systemctl reload postgresql

echo "PostgreSQL installation and configuration completed."
