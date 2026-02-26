# Multi-stage Dockerfile pour OpenIndex
# Stage 1: Crawler avec PostgreSQL
FROM python:3.11-slim as crawler-stage

# Configuration du crawler
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier les sources du crawler
COPY src/ ./src/
COPY config/ ./config/
COPY database/ ./database/

# Créer les répertoires nécessaires
RUN mkdir -p logs

# Variables d'environnement par défaut
ENV PYTHONPATH=/app
ENV POSTGRES_HOST=localhost
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=openindex
ENV POSTGRES_USER=openindex_user
ENV POSTGRES_PASSWORD=openindex_secure_password

# Stage 2: Interface web avec Streamlit
FROM python:3.11-slim as ui-stage

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier les sources de l'interface
COPY src/web_interface_v2.py ./src/
COPY src/postgres_adapter.py ./src/
COPY src/config_manager.py ./src/
COPY src/logging_config.py ./src/
COPY config/ ./config/

# Variables d'environnement pour l'UI
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8502
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Stage 3: Image finale combinée
FROM python:3.11-slim as production

# Métadonnées
LABEL maintainer="OpenIndex Team"
LABEL description="OpenIndex - Crawler SMB avec interface web"
LABEL version="0.1.0"

# Installation des dépendances communes
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier les composants nécessaires
COPY --from=crawler-stage /app/src ./src/
COPY --from=crawler-stage /app/config ./config/
COPY --from=crawler-stage /app/database ./database/
COPY --from=ui-stage /app/src/web_interface_v2.py ./src/
COPY --from=ui-stage /app/src/postgres_adapter.py ./src/
COPY --from=ui-stage /app/src/config_manager.py ./src/
COPY --from=ui-stage /app/src/logging_config.py ./src/

# Créer les répertoires nécessaires
RUN mkdir -p logs archives

# Scripts de démarrage
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Ports exposés
EXPOSE 8502

# Point d'entrée
ENTRYPOINT ["/entrypoint.sh"]
CMD ["--mode", "production"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8502/_stcore/health || exit 1

# Volume pour les données
VOLUME ["/app/logs", "/app/archives", "/app/data"]
