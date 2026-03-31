# TODO OpenIndex — suite post-commando (J4 -> J5)

## Objectif

Passer d'une **readiness J4 documentée** à une **exécution J4 pilotée par preuves**, puis enclencher J5 (qualité & observabilité) avec critères de sortie mesurables.

---

## 1) Priorités immédiates (Semaine en cours)

- [X] **T-01 — Clôturer CMD-12 (checklist release commando) avec preuves**

  - Vérifier CI verte sur PostgreSQL (backend unique).
  - Migration de DB non requise : re-crawl complet prévu sur zone de test massivement modifiée avec PostgreSQL.
  - Vérifier bench comparatif publié avec PostgreSQL.
  - Vérifier rollback relu par un pair.
  - Mettre à jour `CHANGELOG.md` pour le lot de clôture.
  - Commit: `124140d`
- [X] **T-02 — Décision formelle Go/No-Go J4**

  - Appliquer les critères de `docs/phases/J4_MIGRATION.md`.
  - Décision rédigée le `2026-03-18` dans `docs/2026-03-18_j4_go-no-go.md`.
  - Décision retenue: `Go`.
  - Preuves: recrawl contrôlé, benchmark 3 runs stable, rollback drill validé, CI GitHub PostgreSQL verte sur PR `#41`.
  - Commit: `17f5806`
- [X] **T-03 — Figer la baseline technique J4**

  - Confirmer PostgreSQL comme backend de données unique dans la doc principale.
  - Aligner `README.md`, `README.stack.md`, `ROADMAP.md` et ce `TODO.md`.
  - Supprimer les ambiguïtés "actif vs legacy" dans les parcours opératoires.
  - État propagé: `README.md`, `README.stack.md`, `ROADMAP.md`, `TODO.md`.
  - Commit: `40c691b`

---

## 2) Exécution J4 (priorités restantes)

- [X] **T-04 — Rétablir une preuve J4 exploitable sur PostgreSQL**

  - Le `Go` J4 du `2026-03-18` reste inutilisable tant qu'un recrawl complet fiable n'a pas produit de nouvelle preuve versionnée.
  - Capitaliser le crawl complet en cours sur `\\172.16.252.34\Public\SMIDEN` et vérifier sa finalisation sans erreur bloquante.
  - Corrigé le `2026-03-19` côté code: les nouveaux runs PostgreSQL peuvent désormais ignorer les fichiers déjà crawlés au même chemin quand `size` et `last_modified` sont inchangés, ou quand `last_modified` n'est pas postérieur au dernier crawl `completed` de l'espace; commit `ae508db`, effet complet après redéploiement du crawler.
  - Livré le `2026-03-19` via `docs/artifacts/j4_recrawl_live_snapshot_2026-03-19.json`: volumétrie réelle observée, découverte stabilisée, `0` erreur bloquante et rapport J4/Go-No-Go révisés.
  - La completion totale du traitement d'intégrité n'est plus portée comme bloqueur J4; elle est transférée au cycle J5 avec nouveaux tests dédiés.
- [X] **T-05 — Validation de performance PostgreSQL sur base recrawlée**

  - Rejouer le benchmark PostgreSQL sur endpoints critiques après le recrawl complet de référence.
  - Vérifier le respect des seuils P95 annoncés avec PostgreSQL.
  - Publier les résultats dans `docs/` avec conclusion explicite (OK / NOK) sur la base active PostgreSQL.
  - Commande exécutée : `docker compose exec api python /app/scripts/benchmark_dual_db.py --base-url http://localhost:8000 --samples 30 --runs 3 --output /tmp/bench_postgresql_active_2026-03-26.json`
  - Artefacts : `docs/artifacts/bench_postgresql_active_2026-03-26.json`, `docs/bench_postgresql_active_2026-03-26.md`
  - Conclusion : P95 `/api/stats` ≈ 56 ms / `/api/files` ≈ 66 ms stable sur les trois runs ⇒ OK.
- [ ] **T-06 — Durcir la CI PostgreSQL de référence**

  - Rendre obligatoire le passage des jobs CI PostgreSQL avant merge.
  - Ajouter la collecte d'artefacts minimaux en cas d'échec (logs API/tests).
  - Documenter le chemin de diagnostic rapide en cas de pipeline rouge.
  - Workflow durci localement le `2026-03-26` : le job `api-tests-postgresql` échoue désormais si PostgreSQL n'est pas joignable ou si la connexion SQL échoue; la collecte d'artefacts `api-tests-postgresql-diagnostics-*` est systématique.
  - Références : `scripts/run_release_gate.sh`, `docs/operations/CI_POSTGRESQL_GATE.md`, `.github/workflows/docker-stack.yml`.
  - Point d'application restant hors dépôt : déclarer `api-tests-postgresql` en `required status check` sur les branches protégées GitHub (`main`, `develop`).
- [X] **T-07 — Drill de rollback J4**

  - Simuler un incident post-migration PostgreSQL.
  - Exécuter le rollback complet avec chronométrage.
  - Capitaliser la procédure réelle dans `docs/operations/EXPLOITATION.md`.
  - Livré le `2026-03-18` via `docs/artifacts/j4_rollback_drill_2026-03-18.json`; pas de nouveau chantier J4 ouvert tant qu'un nouveau contexte de référence ne l'exige pas.

---

## 3) Préparation J5 (qualité & observabilité)

- [X] **T-08 — Définir les SLI/SLO opérationnels minimum**

  - Disponibilité API, latence P95, taux d'erreurs, temps de recovery.
  - Seuils d'alerte + responsables + fréquence de revue.
  - Livré le `2026-03-26` via `docs/operations/J5_SLI_SLO.md`.
  - Références de preuve : benchmark actif `docs/bench_postgresql_active_2026-03-26.md` et gate CI PostgreSQL `docs/operations/CI_POSTGRESQL_GATE.md`.
- [X] **T-09 — Pack de tests critiques "release gate"**

  - API smoke critique avec PostgreSQL.
  - Non-régression frontend structurelle.
  - Vérification DB explain / requêtes clés.
  - Exécution via une commande unique documentée.
  - Livré le `2026-03-26` avec `scripts/run_release_gate.sh` et `docs/operations/J5_RELEASE_GATE.md`.
  - Couverture pack: smoke API, DB explain, feature flag PostgreSQL et non-régression frontend structurelle.
  - Intégration CI branchée sur `api-tests-postgresql`.
- [X] **T-10 — Observabilité minimale exploitable**

  - Standardiser les logs applicatifs (format, niveau, corrélation).
  - Définir un dashboard santé + une vue incidents.
  - Définir la procédure d'escalade en cas de dérive.
  - Livré le `2026-03-26` avec la vue opératoire `GET /api/operations/status` dans `src/api/main.py`.
  - Logs API standardisés via `OPENINDEX_LOG_LEVEL` et format horodaté homogène.
  - Références opératoires: `docs/operations/J5_OBSERVABILITY_BASELINE.md` et `docs/operations/EXPLOITATION.md`.
- [ ] **T-14 — Revoir l'UI pour le pilotage des tests et crawls**

  - [X] Vocabulaire exploration/explorateur aligné dans l'UI (livré le `2026-03-18`).
  - [X] Logs réels du worker dans l'UI (livré le `2026-03-18`).
  - [X] Progression basée sur le volume découvert/traité (livré le `2026-03-18`).
  - [X] Exposition des vraies files du worker (Dossiers, Fichiers, Somme de contrôle, Gros fichiers) (livré le `2026-03-18`).
  - [X] Actions arrêter/supprimer sur les runs récents (livré le `2026-03-18`).
  - [X] Garde-fou un seul run actif par espace (livré le `2026-03-18`).
  - [X] Transformer le tableau de bord en poste opérateur actif: espace courant, dernier lancement, état du crawl, KPI temps réel, progression et journal (livré le `2026-03-18`).
  - >  ~~Implémenter le protocole de pré-estimation volumétrique avant exploration~~
    > Annulé en raison de la charge serveur excessive. Le pilotage repose désormais sur les métriques runtime et le journal réel.
  - [x] Corriger les finitions demandées dans `docs/definition_ui.md`:
    - [x] Nom distinctif d'espace.
    - [x] "Non défini" si dernier lancement absent.
    - [x] Zone version réduite.
    - [x] Suppression du sous-titre inutile.
    - [x] Unités en octets (et non kelvins).
    - [x] Bouton logs déplacé sous la progression et désactivé si le crawler est inactif.
  - [x] Déporter les explications de conception ou limites techniques hors de l'interface vers `TODO.md` ou la documentation.
  - [x] Rendre visibles les statuts en cours, succès, échecs, durée, artefacts et journaux utiles directement dans l'UI finale.
  - [x] Supprimer les vues de démonstration ou décoratives qui ne servent pas l'exploitation réelle.
  - [x] Prévoir un écran de suivi temps réel orienté exploitation plutôt qu'une simple consultation statique.
  - [x] Rendre actifs les éléments de shell:
    - [x] Cloche de notifications.
    - [x] Engrenage de configuration.
    - [X] Bouton "Piloter le crawl".
  - [x] Implémenter l'ouverture de configuration en overlay latéral droite -> gauche pour:
    - [x] Espaces crawler.
    - [x] Gestion de la base.
    - [ ] Inscription des utilisateurs (admin) — en attente d'authentification applicative.
    - [ ] Profil utilisateur — en attente d'authentification applicative.
  - [x] Implémenter "Piloter le crawl" sous forme de lightbox permettant de lancer, forcer ou arrêter un crawl.
- [X] **T-15 — Concevoir l'Explorateur de fichiers double panneau**

  - Définir le comportement cible type Explorateur Windows / Dolphin.
  - Prévoir navigation arborescente, sélection, transfert inter-panneaux et actions contextuelles.
  - Déterminer les endpoints API nécessaires pour une navigation hiérarchique et des opérations de déplacement/copie pilotées.
  - Prévoir le mode d'entrée dans le menu en cohérence avec les arbitrages de shell validés dans `docs/definition_ui.md`.
  - Premier socle livré le `2026-03-30` dans `frontend/index.html` et `src/api/main.py` :
    double panneau SMB indexé, panneau source lié à l'espace actif, panneau archivage lié à un second espace configuré, navigation par répertoire, remontée au parent, sélection et rafraîchissement.
  - Actions déjà disponibles :
    archivage fichier par copie ou déplacement entre espaces configurés, endpoint de lecture de fichier SMB, lightbox PDF/images/vidéos et reconnaissance des formats bureautiques.
  - Couverture technique déjà livrée :
    endpoints `/api/explorer/items`, `/api/file-content` et `/api/archive/file`, plus tests API/structure frontend associés.
  - Dette restante court terme :
    rendu bureautique complet (Word / Excel / PowerPoint / LibreOffice) dans le lightbox.
  - Compléments livrés le `2026-03-30` :
    vérification SHA-256 post-copie avant suppression source, option de laisser un lien côté source et mode overwrite piloté pour les conflits de destination.
  - Dette restante moyen terme :
    navigation SMB live hors index, opérations de masse, menu contextuel type Explorateur Windows/Dolphin et meilleur traitement des erreurs SMB côté UI.
  - PR fix/explorateur créée le `2026-03-31` avec version `0.4.1` (bump fix).
- [ ] **T-16 — Concevoir la page de traitements des artefacts**

  - Définir les catégories d'artefacts traitables: temporaires Office, doublons, fichiers système, archives obsolètes.
  - Prévoir KPI dédiés, liste filtrable, sélection multiple et actions de masse.
  - Déterminer les règles métiers entre suppression, ignorance et archivage.
  - Prévoir les actions unitaires et massives: supprimer, ignorer, archiver, sélectionner tout.
- [ ] **T-13 — Préparer la configuration multi-repository**

  - Définir le modèle de configuration pour plusieurs racines SMB.
  - Déterminer la stratégie d'identification par source/référentiel.
  - Adapter la doc opératoire pour éviter les recrawls monolithiques sur base active.

---

## 4) Dette documentaire à résorber

- [ ] **T-11 — Nettoyage docs historiques vs référence active**

  - Marquer explicitement les documents legacy.
  - Ajouter un index "où trouver la vérité" dans `docs/`.
  - Réduire les doublons roadmap/projet/todo.
- [ ] **T-12 — Gouvernance de preuve**

  - Chaque item clos doit pointer vers: commande exécutée, artefact, commit.
  - Remplacer tout marqueur implicite par une preuve vérifiable.

---

## Définition de terminé (DoD) pour chaque tâche

- [ ] Une preuve d'exécution est versionnée (log, JSON, capture, rapport).
- [ ] Les impacts doc sont propagés aux fichiers de référence.
- [ ] Un risque principal et son plan de mitigation sont notés.
- [ ] La tâche est traçable dans l'historique Git (commit clair).

---

## Notes de pilotage

- Priorisation: **fiabilité > migration > confort**.
- Pas de nouvelle feature produit tant que T-01 à T-07 ne sont pas clôturées.
- Revue hebdo obligatoire des KPI (pipeline, flakiness, perf, recovery).

---

## Annexe — Priorités opérateur clôturées

- [X] **P-05 — Dettes de stabilisation opérateur**

  - Corrigé le `2026-03-19`: la lecture principale de progression s'appuie désormais sur le runtime réel du run actif; la dette résiduelle porte surtout sur les cas de refresh incohérent entre blocs.
  - Corrigé le `2026-03-19`: le bloc `Runs récents` n'affiche plus `Aucun run enregistré` quand un état actif est connu par `monitoring`; un message de désynchronisation explicite prend le relais.
  - Corrigé le `2026-03-19`: les runs bloqués trop longtemps en `cancelling` sont désormais réconciliés automatiquement vers `cancelled`.
  - Corrigé le `2026-03-19`: les connexions WebSocket fermées sont purgées proprement avant les envois suivants, ce qui supprime le bruit `Cannot call "send" once a close message has been sent.`.
  - Clôturé le `2026-03-19`: le prototype `estimate-{hash}` est abandonné explicitement; aucune archive dédiée supplémentaire n'est requise dans le chemin nominal.
- [X] **P-04 — Statut moteur et commandes opérateur explicites**

  - Garder une barre de progression pour la quantité de données inventoriées.
  - Ajouter des gommettes de couleur pour l'état moteur: arrêté, estimation, exploration, erreur, terminé.
  - Basculer le bouton principal de `Lancer` vers `Arrêter` quand une exploration est en cours.
  - Livré via les commits `1a2407a` et `f8fe00c`.
- [X] **P-03 — Traitement asynchrone sans limite artificielle**

  - Supprimer les limites de taille des queues de traitement asynchrone.
  - Vérifier que le backlog de vérification d'intégrité n'est plus artificiellement plafonné.
  - Livré dans le crawler PostgreSQL; effet complet appliqué aux nouveaux runs après redéploiement du conteneur.
- [X] **P-02 — Indicateurs de progression lisibles et fiables**

  - Exploiter les retours actuels du moteur pour des indicateurs de progression fiables.
  - Présenter ces indicateurs sur une seule ligne, lisibles d'un coup d'oeil.
  - Réserver les queues au diagnostic secondaire.
  - Bug identifié le `2026-03-19`: l'API lisait un fichier fixe `smb_crawler_postgresql.log` alors que le crawler produit des logs par run `smb_crawler_postgresql_<run_id>.log`; conséquence directe: journal explorateur vide et indicateurs runtime à `0` malgré un run `running`.
  - Clôturé le `2026-03-19`: le journal runtime réel et les indicateurs principaux de progression sont rétablis pour l'exploitation; les dettes résiduelles sont regroupées en `P-05`.
  - Avancement utile livré: l'UI permet désormais de modifier une configuration d'espace existante, y compris de remplacer le mot de passe sans recréer l'espace; le secret courant n'est pas réaffiché et reste conservé si le champ mot de passe est laissé vide.
- [X] **P-01 — Pré-estimation volumétrique avant exploration**

  - Revoir le protocole moteur pour obtenir une estimation la plus fidèle possible du volume total avant exploration.
  - Hypothèse rejetée en exploitation: l'approche `worker Docker éphémère + montage CIFS + du -sb` n'est pas viable dans son état actuel pour un budget opérateur raisonnable; elle ne doit plus être considérée comme cible par défaut.
  - Décision appliquée dans le code: les nouveaux runs partent directement en `queued`; le pilotage opérateur repose sur les métriques runtime et le journal réel.
  - Décision de schéma: les colonnes `estimated_total_size` et `estimate_*` sont retirées de `crawl_runs` sur la base de test; on repart sur une structure minimale cohérente avec le flux réel.
  - Dette documentaire: archiver l'historique du prototype `estimate-{hash}` dans une note dédiée si l'on veut conserver la trace d'exploitation, mais ne plus le laisser polluer le chemin nominal.
  - Clôturé le `2026-03-19`: le pilotage runtime en production répond désormais au besoin opérateur; il n'y a plus de raison de poursuivre la pré-estimation volumétrique avant exploration.
- [X] **P-00c — Fuseau horaire homogène et configurable**

  - Aligner les conteneurs Docker sur un fuseau horaire explicite.
  - Rendre le fuseau d'affichage configurable dans l'interface via l'engrenage.
  - Afficher les dates de build et d'exécution dans le fuseau choisi.
  - Livré via le commit `1a2407a`.
- [X] **P-00b — Réconciliation des runs zombies**

  - Ajouter une logique défensive pour reclassifier les runs stale laissés `running` par le moteur.
  - Exposer un état opérateur clair quand le moteur n'émet plus mais que la base n'est pas cohérente.
  - Livré via les commits `1a2407a` et `f8fe00c`.
- [X] **P-00 — Finalisation fiable des runs d'exploration**

  - Corriger la chaîne de fin de run pour qu'un crawl terminé ou timeouté écrive toujours un statut final explicite en base.
  - Ajouter un signal et une trace `run terminé` / `run en échec` côté moteur.
  - Empêcher qu'un run reste `running` en base sans activité réelle du moteur.
  - Livré via les commits `1a2407a` et `f8fe00c`.
