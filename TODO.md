# TODO OpenIndex — Plan d'action

---

## Fonctionnalités à ajouter

### 1. Authentification sur le gestionnaire d'indexation
- Ajouter un écran de login/mot de passe sur `indexer-monitoring.html`
- Protéger l'accès à la page (actuellement accessible sans auth)
- Utiliser le même système que la console principale (auth.js / PocketBase)

### 2. PKI par zone configurée (credentials distincts par source SMB)
- Chaque source SMB (SMIDEN, SEPM, etc.) a ses propres identifiants de connexion
- Déjà supporté par le modèle (`connection_username`, `connection_password`, `connection_domain`)
- Vérifier que le formulaire d'ajout de source dans `indexer-monitoring.html` permet de configurer ces credentials
- Vérifier que le worker utilise bien les credentials de la config associée (déjà fait dans `_get_smb_config`)
- Ajouter un indicateur visuel dans la page Sources montrant si une source a des credentials configurés

### 3. Pilotage de l'exploration centralisé dans l'indexeur
- Le crawl control (start/stop/pause) se fait uniquement depuis `indexer-monitoring.html`
- La console principale (`index.html`) ne montre plus les contrôles de crawl (supprimé)
- Ajouter éventuellement un indicateur d'état dans le sidebar de la console principale

### 4. Amélioration UI/UX
- Harmoniser `archive-monitoring.html` avec le même design que `indexer-monitoring.html`
- Ajouter un thème sombre optionnel
- Améliorer les performances du chargement des artefacts (pagination, cache)

---

## Correctifs en cours

### Espaces SMB multi-sources (résolu)
- ✅ Ajout de `remote_path` dans la table `smb_spaces`
- ✅ Nouvelle contrainte `UNIQUE (host, share, remote_path)`
- ✅ Deux sources avec même host/share mais remote_path différent ont chacune leur espace
- ✅ `_resolve_space_id` met à jour avec `remote_path`

### Refonte interface console (résolu)
- ✅ Nouveau design identique à `indexer-monitoring.html`
- ✅ 4 vues : Dashboard, Explorateur, Artefacts, Recherche
- ✅ API frontend corrigées pour correspondre au backend
