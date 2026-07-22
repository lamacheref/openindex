#!/usr/bin/env bash
source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/build.func)
# Copyright (c) 2024-2026 OpenIndex Contributors
# License: MIT
# Source: https://github.com/lamacheref/OpenIndex

APP="OpenIndex"
var_tags="${var_tags:-indexing;smb;search}"
var_cpu="${var_cpu:-2}"
var_ram="${var_ram:-2048}"
var_disk="${var_disk:-16}"
var_os="${var_os:-ubuntu}"
var_version="${var_version:-24.04}"
var_arm64="${var_arm64:-yes}"
var_unprivileged="${var_unprivileged:-1}"

APP_USER="openindex"
APP_HOME="/srv/openindex"
POCKETBASE_VERSION="0.22.22"
POCKETBASE_URL="https://github.com/pocketbase/pocketbase/releases/download/v${POCKETBASE_VERSION}/pocketbase_${POCKETBASE_VERSION}_linux_amd64.zip"
POSTGRES_DB="${POSTGRES_DB:-openindex}"
POSTGRES_USER="${POSTGRES_USER:-openindex_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(openssl rand -base64 24)}"

header_info "$APP"
variables
color
catch_errors

function update_script() {
  header_info
  check_container_storage
  check_container_resources
  if [[ ! -d ${APP_HOME} ]]; then
    msg_error "No ${APP} Installation Found at ${APP_HOME}!"
    exit
  fi

  msg_info "Stopping OpenIndex services"
  systemctl stop openindex-api openindex-indexer-worker openindex-indexer-scheduler 2>/dev/null || true

  msg_info "Pulling latest code"
  cd ${APP_HOME}
  git fetch origin
  git reset --hard origin/Devel

  msg_info "Updating Python dependencies"
  ${APP_HOME}/.venv/bin/pip install --upgrade -r requirements/dev.txt xxhash

  msg_info "Rebuilding frontend"
  cd ${APP_HOME}
  npm install --omit=dev
  npm run build:frontend

  msg_info "Applying database migrations"
  cd ${APP_HOME}
  for f in database/migrations/*.sql; do
    echo "Running $f"
    PGPASSWORD=${POSTGRES_PASSWORD} psql -h localhost -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f "$f"
  done

  msg_info "Restarting services"
  systemctl start openindex-api openindex-indexer-worker openindex-indexer-scheduler

  msg_ok "${APP} updated successfully!"
  exit
}

# ──────────────────────────────────────────────────
# Installation
# ──────────────────────────────────────────────────
start
build_container 2>/dev/null
description

# Push and execute inner installer inside the container
msg_info "Installing OpenIndex inside container"
pct push "$CTID" /dev/stdin /tmp/install_inner.sh << 'INNERSCRIPT'
#!/usr/bin/env bash
APP_USER="openindex"
APP_HOME="/srv/openindex"
POCKETBASE_VERSION="0.22.22"
POCKETBASE_URL="https://github.com/pocketbase/pocketbase/releases/download/v${POCKETBASE_VERSION}/pocketbase_${POCKETBASE_VERSION}_linux_amd64.zip"
POSTGRES_DB="${POSTGRES_DB:-openindex}"
POSTGRES_USER="${POSTGRES_USER:-openindex_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(openssl rand -base64 24)}"

msg_info "Configuring container"
adduser --system --group --home ${APP_HOME} --no-create-home ${APP_USER}
mkdir -p ${APP_HOME}
chown ${APP_USER}:${APP_USER} ${APP_HOME}

msg_info "Installing system dependencies"
apt-get update
apt-get install -y \
  curl wget gnupg ca-certificates \
  gcc g++ libpq-dev \
  python3 python3-pip python3-venv \
  nodejs npm \
  nginx \
  postgresql postgresql-client \
  smbclient cifs-utils \
  unzip openssl
apt-get -y upgrade

msg_info "Setting up PostgreSQL"
systemctl enable postgresql
systemctl start postgresql

su - postgres -c "psql -c \"CREATE USER IF NOT EXISTS ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';\""
su - postgres -c "psql -c \"SELECT 'CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${POSTGRES_DB}')\gexec\""
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};\" 2>/dev/null || true"
su - postgres -c "psql -d ${POSTGRES_DB} -c \"GRANT ALL ON SCHEMA public TO ${POSTGRES_USER};\""

cat > /etc/postgresql/*/main/pg_hba.conf << PGEOL
local   all             all                                     peer
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
PGEOL

systemctl restart postgresql

cat > ${APP_HOME}/.env << ENVEOF
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
OPENINDEX_TIMEZONE=Europe/Paris
OPENINDEX_API_PORT=8000
POCKETBASE_URL=http://localhost:8090
INDEXER_POLL_INTERVAL=5
ENVEOF
chmod 600 ${APP_HOME}/.env
chown ${APP_USER}:${APP_USER} ${APP_HOME}/.env

msg_info "Deploying OpenIndex code"
cd /tmp
git clone --branch main --depth 1 https://github.com/lamacheref/OpenIndex.git openindex-src
cp -a /tmp/openindex-src/. ${APP_HOME}/
rm -rf /tmp/openindex-src

msg_info "Creating Python virtual environment"
python3 -m venv ${APP_HOME}/.venv
chown -R ${APP_USER}:${APP_USER} ${APP_HOME}

msg_info "Installing Python dependencies"
${APP_HOME}/.venv/bin/pip install --upgrade pip setuptools wheel
${APP_HOME}/.venv/bin/pip install -r ${APP_HOME}/requirements/dev.txt
${APP_HOME}/.venv/bin/pip install xxhash

msg_info "Building frontend"
npm --prefix ${APP_HOME} install --omit=dev
npm --prefix ${APP_HOME} run build:frontend

msg_info "Running database migrations"
cd ${APP_HOME}
for f in database/migrations/*.sql database/init.sql; do
  echo "  Running $f"
  PGPASSWORD=${POSTGRES_PASSWORD} psql -h localhost -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f "$f" > /dev/null 2>&1 || true
done

msg_info "Installing PocketBase"
cd /tmp
wget -q ${POCKETBASE_URL} -O pocketbase.zip
unzip -q pocketbase.zip -d /opt/pocketbase
rm pocketbase.zip
chown -R ${APP_USER}:${APP_USER} /opt/pocketbase
mkdir -p /opt/pocketbase/pb_data
chown ${APP_USER}:${APP_USER} /opt/pocketbase/pb_data

cat > /opt/pocketbase/pb_hooks/admin.pb.js << 'PBEOF'
onBeforeBootstrap((e) => {
  const superusers = e.dao?.findRecordsByFilter("_superusers", "admin = 'admin@openindex.local'") || [];
  if (superusers.length === 0) {
    const collection = e.dao?.findCollectionByNameOrId("_superusers");
    if (collection) {
      const record = new Record(collection, { admin: "admin@openindex.local" });
      record.setPassword("admin123");
      e.dao?.saveRecord(record);
    }
  }
});
PBEOF

msg_info "Configuring nginx for OpenIndex"
rm -f /etc/nginx/sites-enabled/default

cat > /etc/nginx/sites-available/openindex.conf << 'NGINXEOF'
server {
    listen 80;
    server_name _;
    root /srv/openindex/frontend;
    index index.html;

    access_log /var/log/nginx/openindex-access.log;
    error_log  /var/log/nginx/openindex-error.log;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/javascript application/json application/javascript image/svg+xml;

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 60s;
    }

    location /_/ {
        proxy_pass http://127.0.0.1:8090/_/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api/pocketbase/ {
        proxy_pass http://127.0.0.1:8090/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    error_page 404 /404.html;
    location = /404.html {
        internal;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/openindex.conf /etc/nginx/sites-enabled/openindex.conf
systemctl enable nginx

msg_info "Creating systemd services"

cat > /etc/systemd/system/openindex-api.service << 'APIEOF'
[Unit]
Description=OpenIndex FastAPI Backend
After=postgresql.service network.target
Requires=postgresql.service

[Service]
Type=simple
User=openindex
Group=openindex
WorkingDirectory=/srv/openindex
EnvironmentFile=/srv/openindex/.env
ExecStart=/srv/openindex/.venv/bin/uvicorn backend.src.api.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
APIEOF

cat > /etc/systemd/system/openindex-indexer-worker.service << 'IDXEOF'
[Unit]
Description=OpenIndex Indexer Worker
After=postgresql.service openindex-api.service network.target
Requires=postgresql.service

[Service]
Type=simple
User=openindex
Group=openindex
WorkingDirectory=/srv/openindex
EnvironmentFile=/srv/openindex/.env
ExecStart=/srv/openindex/.venv/bin/python -c "from backend.src.workers.indexer_worker import start_worker; import time; w = start_worker(); [time.sleep(1) for _ in iter(int, 1)]"
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
IDXEOF

cat > /etc/systemd/system/openindex-indexer-scheduler.service << 'SCHEOF'
[Unit]
Description=OpenIndex Indexer Scheduler
After=postgresql.service openindex-api.service network.target
Requires=postgresql.service

[Service]
Type=simple
User=openindex
Group=openindex
WorkingDirectory=/srv/openindex
EnvironmentFile=/srv/openindex/.env
ExecStart=/srv/openindex/.venv/bin/python -m backend.src.workers.indexer_scheduler
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SCHEOF

cat > /etc/systemd/system/openindex-pocketbase.service << 'PBEOF'
[Unit]
Description=OpenIndex PocketBase Auth Service
After=network.target

[Service]
Type=simple
User=openindex
Group=openindex
WorkingDirectory=/opt/pocketbase
ExecStart=/opt/pocketbase/pocketbase serve --dir /opt/pocketbase/pb_data --http 127.0.0.1:8090
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
PBEOF

msg_info "Enabling and starting services"
systemctl daemon-reload
systemctl enable openindex-pocketbase openindex-api openindex-indexer-worker openindex-indexer-scheduler

systemctl start openindex-pocketbase
sleep 3
systemctl start openindex-api
sleep 2
systemctl start openindex-indexer-worker openindex-indexer-scheduler
systemctl start nginx

msg_info "Setting up log rotation"
cat > /etc/logrotate.d/openindex << 'LOGEOF'
/srv/openindex/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}

/var/log/nginx/openindex-*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
LOGEOF

msg_info "Cleaning up"
apt-get autoremove -y
apt-get autoclean
INNERSCRIPT
pct exec "$CTID" -- bash -c "export POSTGRES_USER='${POSTGRES_USER}' POSTGRES_DB='${POSTGRES_DB}' POSTGRES_PASSWORD='${POSTGRES_PASSWORD}' POCKETBASE_URL='${POCKETBASE_URL}'; bash /tmp/install_inner.sh" 2>&1 | sed 's/^/  /'

msg_info "Services status"
systemctl status openindex-pocketbase openindex-api openindex-indexer-worker openindex-indexer-scheduler nginx --no-pager -l 2>&1 | grep -E '(●|Active:)' || true

msg_ok "OpenIndex deployment completed successfully!"
msg_info "Access the UI at: http://<LXC_IP>"
msg_info "PocketBase admin: http://<LXC_IP>/_/"
msg_info "  Email: admin@openindex.local"
msg_info "  Password: admin123"
msg_info "PostgreSQL password saved in: ${APP_HOME}/.env"

echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
