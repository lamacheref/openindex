[⬅ Retour au README](../README.md)

# Déploiement LXC — OpenIndex

## Vue d'ensemble

Déploiement de la stack OpenIndex dans un conteneur **LXC Ubuntu 24.04 minimal** sur ProxmoxVE.

Composants installés :
- PostgreSQL 17 (base de données)
- PocketBase (authentification)
- FastAPI (backend API)
- Indexeur SMB (worker + scheduler)
- Nginx (frontend statique, port 80)

---

## 1. Création du conteneur LXC

Sur l'hôte Proxmox (`nyx`), créer un conteneur Ubuntu 24.04 minimal :

```
CTID=201  # ou autre ID libre
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

Noter l'IP, elle sera utilisée pour la suite.

---

## 2. Installation des services

Se connecter en SSH :

```bash
ssh root@<LXC_IP>
```

### 2.1 Prérequis système

```bash
apt-get update && apt-get upgrade -y
apt-get install -y python3 python3-pip python3-venv git curl gnupg \
  postgresql-16 postgresql-client nginx smbclient xxd build-essential python3-dev
```

### 2.2 Configuration PostgreSQL

```bash
systemctl start postgresql
sudo -u postgres psql -c "CREATE USER openindex_user WITH PASSWORD 'openindex_secure_password';"
sudo -u postgres psql -c "CREATE DATABASE openindex OWNER openindex_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE openindex TO openindex_user;"
```

Appliquer le schéma :

```bash
# init.sql + toutes les migrations
PGPASSWORD=openindex_secure_password psql -h localhost -U openindex_user -d openindex -f /srv/openindex/database/init.sql
for f in /srv/openindex/database/migrations/*.sql; do
  echo "Running $f"
  PGPASSWORD=openindex_secure_password psql -h localhost -U openindex_user -d openindex -f "$f"
done
```

### 2.3 Déploiement du code

```bash
mkdir -p /srv/openindex
git clone https://github.com/lamacheref/OpenIndex.git /srv/openindex
cd /srv/openindex
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt xxhash
```

### 2.4 PocketBase

```bash
cd /srv/openindex
LATEST=$(curl -s https://api.github.com/repos/pocketbase/pocketbase/releases/latest | grep tag_name | cut -d'"' -f4)
curl -sL -o pocketbase.zip "https://github.com/pocketbase/pocketbase/releases/download/${LATEST}/pocketbase_${LATEST}_linux_amd64.zip"
unzip -o pocketbase.zip
rm pocketbase.zip
chmod +x pocketbase
```

### 2.5 Frontend

```bash
cd /srv/openindex
npm install && npm run build:frontend
cp -r frontend/dist/* /var/www/html/
```

### 2.6 Variables d'environnement

```bash
cat > /srv/openindex/.env << 'EOF'
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=openindex
POSTGRES_USER=openindex_user
POSTGRES_PASSWORD=openindex_secure_password
POCKETBASE_URL=http://localhost:8090
OPENINDEX_API_PORT=8000
EOF
```

---

## 3. Démarrage

```bash
systemctl start postgresql
/srv/openindex/pocketbase serve --http=0.0.0.0:8090 --dir=/srv/openindex/pb_data &
```

---

## 4. Accès

| Interface | URL |
|---|---|
| Frontend | `http://<LXC_IP>` |
| API (Swagger) | `http://<LXC_IP>/api/docs` |
| PocketBase admin | `http://<LXC_IP>/_/` |

---

## 5. Arrêt

```bash
# Stopper les services manuellement
pkill -f uvicorn
pkill -f indexer_worker
pkill -f pocketbase

# Ou stopper le conteneur
pct stop $CTID
```

---

## 6. Mise à jour

```bash
cd /srv/openindex
git pull origin main
source .venv/bin/activate
pip install --upgrade -r requirements/dev.txt xxhash
npm install && npm run build:frontend
for f in database/migrations/*.sql; do
  PGPASSWORD=openindex_secure_password psql -h localhost -U openindex_user -d openindex -f "$f"
done
# Redémarrer les services
```

---

## 7. Recovery

### 7.1 Backup PostgreSQL

```bash
pg_dump -U openindex_user -d openindex > /srv/openindex/backups/openindex_$(date +%Y%m%d_%H%M%S).sql
```

### 7.2 Restore PostgreSQL

```bash
PGPASSWORD=openindex_secure_password psql -h localhost -U openindex_user -d openindex < backup_file.sql
```

### 7.3 Conteneur inaccessible

Si le LXC ne répond plus, depuis l'hôte Proxmox :

```bash
pct exec $CTID -- bash -c "systemctl restart postgresql"
pct exec $CTID -- bash -c "cd /srv/openindex && source .venv/bin/activate && nohup uvicorn backend.src.api.main:app --host 0.0.0.0 --port 8000 &"
```

---

## 8. Organisation des fichiers

```
/srv/openindex/
├── .env                  # Variables d'environnement
├── OpenIndex/            # Code source (déployé)
│   ├── backend/src/
│   ├── frontend/
│   ├── database/
│   │   ├── init.sql
│   │   └── migrations/
│   ├── scripts/
│   └── tests/
├── pb_data/              # Données PocketBase
└── pocketbase            # Binaire PocketBase
```
