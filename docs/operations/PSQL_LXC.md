[⬅ Retour au DEPLOY_LXC](./DEPLOY_LXC.md)

# Interroger la base du LXC depuis le poste de dev — `scripts/psql_lxc.sh`

Le client `psql` n’est **pas forcément installé** sur le poste de développement.
Plutôt que d’installer `postgresql-client` localement (qui exigerait un accès réseau
au port 5432 du LXC + un `.env` en local), utilisez le **wrapper SSH**
`scripts/psql_lxc.sh`, qui exécute la requête **directement sur le serveur LXC**
(`192.168.110.6`) en réutilisant la **même clé SSH** que `scripts/deploy_lxc.sh`
(`~/.ssh/flamachere_pro_20260511`).

> ⚠️ Conservez un usage **lecture seule** (`SELECT`). Toute mutation
> (`UPDATE`, `DELETE`, `DROP`, `ALTER`) impose au préalable un `pg_dump`
> complet et l’approbation formelle (règle sécurité DB — AGENTS.md).

## Options

```bash
./scripts/psql_lxc.sh -c "SELECT count(*) FROM indexed_files_optimized;"
./scripts/psql_lxc.sh -f database/migrations/009_optimize_indexer_schema.sql   # exécute un .sql
echo "SELECT 1" | ./scripts/psql_lxc.sh                                         # via stdin
./scripts/psql_lxc.sh <<'SQL'                                                   # heredoc
  SELECT name, is_duplicate, is_garbage, size, hash_xxh64
  FROM indexed_files_optimized
  WHERE name ILIKE '%rib%'
  ORDER BY is_garbage NULLS LAST
  LIMIT 10;
SQL
```

## Variables d’environnement (facultatives)

| Variable | Défaut | Rôle |
|---|---|---|
| `PSQL_LXC_KEY`  | `~/.ssh/flamachere_pro_20160511` | clé SSH du LXC |
| `PSQL_LXC_HOST` | `192.168.110.6`                | IP / host du conteneur |
| `PSQL_LXC_USER` | `root`                         | user SSH du conteneur |

Exemple :

```bash
PSQL_LXC_HOST=192.168.110.7 ./scripts/psql_lxc.sh -c "SELECT version();"
```

## Comportement interne

1. un `ssh` lit `POSTGRES_USER / POSTGRES_DB / POSTGRES_PASSWORD /
   POSTGRES_HOST / POSTGRES_PORT` depuis `/srv/openindex/.env` **sur le LXC** ;
2. les variables `PG*` sont exportées localement (elles NE sont qu’informatives —
   la vraie exécution sql se fait via le second `ssh`) ;
3. la 2ᵉ connexion `ssh` lance `psql -X -q -v ON_ERROR_STOP=1 -h … -U … -d …`
   en transmettant les args (`-c`/`-f`/... ) echappés via `printf '%q'`, **ou**
   en laissant `psql` lire la requête depuis `stdin` (pipe / heredoc).

`ON_ERROR_STOP=1` fait en sorte que quiconque un problème de syntaxe voit le
process renvoyer un code d’erreur non-nul (`set -e`).

## FAQ

- **`bash: line 1: syntax error near unexpected token`** → la requête contient
  des caractères shell spéciaux (`(`, `)`, `$`) non protégés ; entourez la query
  de guillemets ou utilisez un heredoc.
- **`Aucune autorisation`** → la variable `PSQL_LXC_USER` est `root` par défaut et
  possède les droits psql par socket ; si vous êtes un autre user, exportez une
  connexion postgres valide dans le `.env` du LXC.
- **pas de `psql` local** → normal : le wrapper exécute psql **sur le LXC**
  (`postgresql-client` est installé via `scripts/install_lxc_inner.sh`).
