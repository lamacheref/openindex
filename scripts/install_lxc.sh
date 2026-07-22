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
cp scripts/install_lxc_inner.sh /tmp/install_lxc_inner.sh
pct push "$CTID" /tmp/install_lxc_inner.sh /tmp/install_inner.sh 2>/dev/null
pct exec "$CTID" -- bash /tmp/install_inner.sh 2>&1 | sed 's/^/  /'
rm -f /tmp/install_lxc_inner.sh

msg_info "Services status"
systemctl status openindex-pocketbase openindex-api openindex-indexer-worker openindex-indexer-scheduler nginx --no-pager -l 2>&1 | grep -E '(●|Active:)' || true

msg_ok "OpenIndex deployment completed successfully!"
msg_info "Access the UI at: http://<LXC_IP>"
msg_info "PocketBase admin: http://<LXC_IP>/_/"
msg_info "  Email: admin@openindex.local"
msg_info "  Password: admin123"
msg_info "PostgreSQL password saved in: ${APP_HOME}/.env"

echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
