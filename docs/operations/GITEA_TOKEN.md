[⬅ Retour au DEPLOY_LXC](./DEPLOY_LXC.md)

# Accès à l'API Gitea (issues / commentaires) — token local

Le token d'accès personnel Gitea (`gitea.smiden.eu`, compte `flamachere`) permet
d'utiliser l'API REST (créer/commenter des issues, lire les repos). Il est valable
**pour tous les projets hébergés sous Gitea**.

## Emplacement du token

```
~/.config/gitea/smiden.token
```

- Permissions : `600` (lecture/écriture par l'utilisateur uniquement).
- **Ne JAMAIS le committer**, ni l'afficher dans un log, ni le copier dans le repo.
- Droits restreints fournis par l'utilisateur (commentaires d'issues, lecture).

## Utilisation

Le token se lit depuis le fichier à chaque commande, sans être affiché :

```bash
curl -s -H "Authorization: token $(cat ~/.config/gitea/smiden.token)" \
  "https://gitea.smiden.eu/api/v1/repos/flamachere/OpenIndexV1/issues/3"
```

### Poster un commentaire sur une issue

```bash
cat > /tmp/comment.md <<'MD'
Mon commentaire en markdown…
MD
/usr/bin/python3 -c "import json,sys; print(json.dumps({'body': open('/tmp/comment.md').read()}))" \
  > /tmp/payload.json
curl -s -X POST \
  -H "Authorization: token $(cat ~/.config/gitea/smiden.token)" \
  -H "Content-Type: application/json" \
  -d @/tmp/payload.json \
  "https://gitea.smiden.eu/api/v1/repos/flamachere/OpenIndexV1/issues/3/comments"
```

### Endpoints utiles

| Action | Méthode / URL |
|---|---|
| Lire une issue | `GET /api/v1/repos/{owner}/{repo}/issues/{n}` |
| Lire les commentaires | `GET /api/v1/repos/{owner}/{repo}/issues/{n}/comments` |
| Poster un commentaire | `POST /api/v1/repos/{owner}/{repo}/issues/{n}/comments` |
| Lire les repos | `GET /api/v1/user/repos` |

`{repo}` se note `flamachere/OpenIndexV1` (le dépôt Gitea du projet).

## Récupérer un nouveau token

1. `https://gitea.smiden.eu` → login → **Settings → Applications → Generate New Token** ;
2. choisir le scope suffisant (ex. `write:issue`) ;
3. remplacer le contenu de `~/.config/gitea/smiden.token` puis `chmod 600` :
   ```bash
   printf '%s\n' '<nouveau_token>' > ~/.config/gitea/smiden.token && chmod 600 ~/.config/gitea/smiden.token
   ```

## Règles

- Toute mutation DB liée à un workflow d'issue reste soumise à la règle sécurité DB
  (dump + approbation préalable — AGENTS.md).
- Ne jamais écrire le token dans le code, les scripts du repo ni les issues.
