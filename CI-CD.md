# Configuration Gitea CI/CD pour OpenIndex
# Automatisation du build, test et déploiement des images Docker

## 🔄 **Pipeline CI/CD**

### 🏗️ **Stages**
1. **build** : Compilation des images Docker
2. **test** : Tests des images
3. **deploy** : Push dans le registre
4. **cleanup** : Nettoyage des anciennes images

### 📦 **Images construites**
- `openindex-crawler` : Service crawler Python
- `openindex-web` : Interface web Streamlit
- `openindex-stack` : Stack complète (optionnel)

## 🚀 **Déploiement automatisé**

### Branches et environnements
- **`develop`** → Staging automatique
- **`main`** → Production automatique  
- **`release/*`** → Production avec tags

### Tags
- **`latest`** : Dernier commit de main/develop
- **`vX.Y.Z`** : Releases officielles

## 📋 **Variables requises**

Dans les paramètres de votre projet Gitea :

### 🔐 **Registre Docker**
```bash
CI_REGISTRY=git.example.com:5000/openindex
CI_REGISTRY_USER=deploy_token
CI_REGISTRY_PASSWORD=glpat-xxxxxxxxxxxxxxxxxxxxxxx
```

### 🔧 **Configuration CI/CD**
```bash
# Activer les variables CI/CD
Settings → Repository → Settings → Actions → Variables
```

## 📊 **Monitoring et notifications**

### ✅ **Tests automatisés**
- Connexion PostgreSQL pour chaque image
- Healthcheck de l'interface web
- Validation des dépendances

### 📧 **Déploiement conditionnel**
- Tests requis avant le déploiement
- Validation des branches
- Tags automatiques pour les releases

## 🛠️ **Utilisation locale**

### Tests locaux
```bash
# Lancer les tests localement
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Build manuel
```bash
# Build manuel des images
docker build -f Dockerfile.crawler -t openindex-crawler:dev .
docker build -f Dockerfile.web -t openindex-web:dev .
```

## 📝 **Workflow de développement**

1. **Développer** sur la branche `develop`
2. **Commit** et push → Build + Test automatiques
3. **Merge** dans `main` → Déploiement production
4. **Tag** pour les releases → Tags versionnés

## 🔄 **Intégration continue**

### Triggers automatiques
- Push sur `develop` → Staging
- Push sur `main` → Production
- Création de tags → Release

### Sécurité
- Tokens d'accès limités
- Variables protégées
- Isolation des environnements

## 📈 **Performance**

### Optimisations
- Cache Docker multi-stage
- Parallélisation des builds
- Tests rapides en headless
- Nettoyage automatique

### Monitoring
- Durées des builds
- Taux de succès
- Taille des images

Cette configuration CI/CD assure une livraison continue et fiable pour OpenIndex !
