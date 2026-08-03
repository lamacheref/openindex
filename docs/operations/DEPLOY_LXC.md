[⬅ Retour au README](../README.md)

# Déploiement LXC — OpenIndex

## Vue d'ensemble

Déploiement de la stack OpenIndex dans un conteneur **LXC Ubuntu 24.04 minimal** sur ProxmoxVE.

Deux modes :
- **Installation automatique** (recommandée) : `scripts/install_lxc.sh` depuis l'hôte Proxmox
- **Installation manuelle** : suivre les étapes ci-dessous

Composants installés :
- PostgreSQL 17 (base de données)
- PocketBase (authentification)
- FastAPI (backend API)
- Indexeur SMB (worker + scheduler)
- Nginx (frontend statique, port 80)
- LibreOffice (prévisualisation documents Office)

---

## 1. Installation automatique (recommandée)

Depuis l'hôte **ProxmoxVE** (`nyx`) :

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/lamacheref/OpenIndex/main/scripts/install_lxc.sh)"
```

Le script crée un conteneur Ubuntu 24.04 (2 CPU, 2 Go RAM, 16 Go disque) et installe toute la stack automatiquement.

Paramètres configurables (variables d'environnement) :
- `CTID` : ID du conteneur (défaut : prochain disponible)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` : accès PostgreSQL
- Voir `scripts/install_lxc.sh` pour la liste complète

---

## 2. Installation manuelle

### 2.1 Création du conteneur LXC

Sur l'hôte Proxmox (`nyx`) :

```
CTID=201
HOSTNAME=openindex

pveam download local ubuntu-24.04-standard_24.04-2_amd64.tar.zst

pct create $CTID \
  /var/lib/vz/template/cache/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname $HOSTNAME \
  --storage local-lvm \
  --rootfs 16 \
  --cores 2 \
  --memory 2048 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --features nesting=1

pct start $CTID
pct exec $CTID -- apt-get update && apt-get install -y openssh-server sudo curl
```

Récupérer l'IP :

```
pct exec $CTID -- ip addr show eth0 | grep 'inet '
```

### 2.2 Prérequis système (dans le conteneur)

```bash
ssh root@<LXC_IP>

apt-get update && apt-get upgrade -y
apt-get install -y python3 python3-pip python3-venv git curl gnupg \
  postgresql postgresql-client nginx smbclient xxd build-essential python3-dev \
  libreoffice-core-nogui libreoffice-writer-nogui libreoffice-calc-nogui libreoffice-impress-nogui
```

### 2.3 Configuration PostgreSQL

```bash
systemctl start postgresql
sudo -u postgres psql -c "CREATE USER openindex_user WITH PASSWORD 'openindex_secure_password';"
sudo -u postgres psql -c "CREATE DATABASE openindex OWNER openindex_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE openindex TO openindex_user;"
```

### 2.4 Déploiement du code

```bash
mkdir -p /srv/openindex
git clone https://github.com/lamacheref/OpenIndex.git /srv/openindex
cd /srv/openindex
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt xxhash
npm install && npm run build:frontend
```

### 2.5 Variables d'environnement

```bash
cat > /srv/openindex/.env << 'EOF'
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=openindex
POSTGRES_USER=openindex_user
POSTGRES_PASSWORD=openindex_secure_password
POCKETBASE_URL=http://localhost:8090
OPENINDEX_API_PORT=8000
OPENINDEX_TIMEZONE=Europe/Paris
INDEXER_POLL_INTERVAL=5
EOF
```

### 2.6 Services systemd

Copier les services depuis `scripts/install_lxc_inner.sh` ou les créer manuellement :
- `openindex-api.service` : uvicorn backend.src.api.main:app --port 8000
- `openindex-indexer-worker.service` : worker d'indexation
- `openindex-indexer-scheduler.service` : scheduler cron
- `openindex-pocketbase.service` : PocketBase auth

### 2.7 Nginx

Configurer nginx avec racine `/srv/openindex/frontend` pour servir le frontend statique (voir la conf dans `install_lxc_inner.sh`).

---

## 3. Accès

| Interface | URL |
|---|---|
| Frontend | `http://<LXC_IP>` |
| API (Swagger) | `http://<LXC_IP>/api/docs` |
| Indexer monitoring | `http://<LXC_IP>/indexer-monitoring.html` |
| Archive monitoring | `http://<LXC_IP>/archive-monitoring.html` |
| PocketBase admin | `http://<LXC_IP>/_/` |

---

## 4. Déploiement (mise à jour)

Utiliser `scripts/deploy_lxc.sh` depuis la machine de développement :

```bash
./scripts/deploy_lxc.sh
```

Ce script :
1. `git pull` sur le LXC
2. Met à jour les dépendances Python
3. Rebuild le frontend
4. Applique les migrations SQL
5. Redémarre les services

---

## 5. Interroger la base de données (dev -> LXC)

Le poste de dev ne possède pas forcément le client `psql` installé. Utilisez le
wrapper `scripts/psql_lxc.sh`, qui exécute la requête **sur le LXC via SSH**
(lecture seule recommandée) en réutilisant la clé SSH de `deploy_lxc.sh` :

```bash
./scripts/psql_lxc.sh -c "SELECT count(*) FROM indexed_files_optimized;"
echo "SELECT count(*) FROM indexed_files_optimized WHERE is_garbage;" | ./scripts/psql_lxc.sh
./scripts/psql_lxc.sh <<'SQL'
  SELECT name, is_duplicate, is_garbage, size, hash_xxh64
  FROM indexed_files_optimized
  WHERE name ILIKE '%rib%'
  ORDER BY is_garbage NULLS LAST
  LIMIT 10;
SQL
```

Variables d’environnement (facultatives) : `PSQL_LXC_KEY`, `PSQL_LXC_HOST`,
`PSQL_LXC_USER`.

> ⚠️ Conservez un usage **lecture seule** (`SELECT`). Toute mutation (`UPDATE`,
> `DELETE`, `DROP`) impose au préalable un `pg_dump` complet et l’approbation
> formelle (règle sécurité DB du AGENTS.md).

---

## 6. Recovery

### 5.1 Backup PostgreSQL

```bash
pg_dump -U openindex_user -d openindex > /srv/openindex/backups/openindex_$(date +%Y%m%d_%H%M%S).sql
```

### 5.2 Restore PostgreSQL

```bash
PGPASSWORD=$(grep POSTGRES_PASSWORD /srv/openindex/.env | cut -d= -f2) \
  psql -h localhost -U openindex_user -d openindex < backup_file.sql
```

### 5.3 Conteneur inaccessible

Depuis l'hôte Proxmox :

```bash
pct exec $CTID -- bash -c "systemctl restart postgresql openindex-api openindex-indexer-worker openindex-indexer-scheduler openindex-pocketbase nginx"
```

---

## 6. Organisation des fichiers

```
/srv/openindex/
├── .env                  # Variables d'environnement
├── backend/              # Code backend Python
│   └── src/
│       ├── api/          # FastAPI endpoints
│       └── workers/      # Indexeur, archive, scheduler
├── frontend/             # Assets frontend (index.html, etc.)
├── database/
│   ├── init.sql
│   └── migrations/
├── scripts/              # Outils de déploiement
├── tests/                # Tests
└── .venv/                # Environnement virtuel Python
```
