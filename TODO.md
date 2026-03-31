# TODO OpenIndex — suite post-commando (J4 -> J5)

## Objectif

Passer d'une **readiness J4 documentée** à une **exécution J4 pilotée par preuves**, puis enclencher J5 (qualité & observabilité) avec critères de sortie mesurables.

---

## 1) Priorités immédiates (Semaine en cours)

- [x] **T-01 — Clôturer CMD-12 (checklist release commando) avec preuves**
  - [x] Vérifier CI verte sur PostgreSQL (backend unique).
  - [x] Migration de DB non requise : re-crawl complet prévu sur zone de test massivement modifiée avec PostgreSQL.
  - [x] Vérifier bench comparatif publié avec PostgreSQL.
  - [x] Vérifier rollback relu par un pair.
  - [x] Mettre à jour `CHANGELOG.md` pour le lot de clôture.
  - [x] Commit: `124140d`

- [x] **T-02 — Décision formelle Go/No-Go J4**
  - [x] Appliquer les critères de `docs/phases/J4_MIGRATION.md`.
  - [x] Décision rédigée le `2026-03-18` dans `docs/2026-03-18_j4_go-no-go.md`.
  - [x] Décision retenue: `Go`.
  - [x] Preuves: recrawl contrôlé, benchmark 3 runs stable, rollback drill validé, CI GitHub PostgreSQL verte sur PR `#41`.
  - [x] Commit: `17f5806`

- [x] **T-03 — Figer la baseline technique J4**
  - [x] Confirmer PostgreSQL comme backend de données unique dans la doc principale.
  - [x] Aligner `README.md`, `README.stack.md`, `ROADMAP.md` et ce `TODO.md`.
  - [x] Supprimer les ambiguïtés "actif vs legacy" dans les parcours opératoires.
  - [x] État propagé: `README.md`, `README.stack.md`, `ROADMAP.md`, `TODO.md`.
  - [x] Commit: `40c691b`

---

## 2) Exécution J4 (priorités restantes)

- [x] **T-04 — Rétablir une preuve J4 exploitable sur PostgreSQL**
  - [x] Le `Go` J4 du `2026-03-18` reste inutilisable tant qu'un recrawl complet fiable n'a pas produit de nouvelle preuve versionnée.
  - [x] Capitaliser le crawl complet en cours sur `\\172.16.252.34\Public\SMIDEN` et vérifier sa finalisation sans erreur bloquante.
  - [x] Corrigé le `2026-03-19` côté code: les nouveaux runs PostgreSQL peuvent désormais ignorer les fichiers déjà crawlés au même chemin quand `size` et `last_modified` sont inchangés, ou quand `last_modified` n'est pas postérieur au dernier crawl `completed` de l'espace; commit `ae508db`, effet complet après redéploiement du crawler.
  - [x] Livré le `2026-03-19` via `docs/artifacts/j4_recrawl_live_snapshot_2026-03-19.json`: volumétrie réelle observée, découverte stabilisée, `0` erreur bloquante et rapport J4/Go-No-Go révisés.
  - [x] La completion totale du traitement d'intégrité n'est plus portée comme bloqueur J4; elle est transférée au cycle J5 avec nouveaux tests dédiés.

- [x] **T-05 — Validation de performance PostgreSQL sur base recrawlée**
  - [x] Rejouer le benchmark PostgreSQL sur endpoints critiques après le recrawl complet de référence.
  - [x] Vérifier le respect des seuils P95 annoncés avec PostgreSQL.
  - [x] Publier les résultats dans `docs/` avec conclusion explicite (OK / NOK) sur la base active PostgreSQL.
  - [x] Commande exécutée : `docker compose exec api python /app/scripts/benchmark_dual_db.py --base-url http://localhost:8000 --samples 30 --runs 3 --output /tmp/bench_postgresql_active_2026-03-26.json`
  - [x] Artefacts : `docs/artifacts/bench_postgresql_active_2026-03-26.json`, `docs/bench_postgresql_active_2026-03-26.md`
  - [x] Conclusion : P95 `/api/stats` ≈ 56 ms / `/api/files` ≈ 66 ms stable sur les trois runs ⇒ OK.

- [ ] **T-06 — Durcir la CI PostgreSQL de référence**
  - [x] Rendre obligatoire le passage des jobs CI PostgreSQL avant merge.
  - [x] Ajouter la collecte d'artefacts minimaux en cas d'échec (logs API/tests).
  - [x] Documenter le chemin de diagnostic rapide en cas de pipeline rouge.
  - [x] Workflow durci localement le `2026-03-26` : le job `api-tests-postgresql` échoue désormais si PostgreSQL n'est pas joignable ou si la connexion SQL échoue; la collecte d'artefacts `api-tests-postgresql-diagnostics-*` est systématique.
  - [x] Références : `scripts/run_release_gate.sh`, `docs/operations/CI_POSTGRESQL_GATE.md`, `.github/workflows/docker-stack.yml`.
  - [ ] Point d'application restant hors dépôt : déclarer `api-tests-postgresql` en `required status check` sur les branches protégées GitHub (`main`, `develop`).

- [x] **T-07 — Drill de rollback J4**
  - [x] Simuler un incident post-migration PostgreSQL.
  - [x] Exécuter le rollback complet avec chronométrage.
  - [x] Capitaliser la procédure réelle dans `docs/operations/EXPLOITATION.md`.
  - [x] Livré le `2026-03-18` via `docs/artifacts/j4_rollback_drill_2026-03-18.json`; pas de nouveau chantier J4 ouvert tant qu'un nouveau contexte de référence ne l'exige pas.

---

## 3) Préparation J5 (qualité & observabilité)

- [x] **T-08 — Définir les SLI/SLO opérationnels minimum**
  - [x] Disponibilité API, latence P95, taux d'erreurs, temps de recovery.
  - [x] Seuils d'alerte + responsables + fréquence de revue.
  - [x] Livré le `2026-03-26` via `docs/operations/J5_SLI_SLO.md`.
  - [x] Références de preuve : benchmark actif `docs/bench_postgresql_active_2026-03-26.md` et gate CI PostgreSQL `docs/operations/CI_POSTGRESQL_GATE.md`.

- [x] **T-09 — Pack de tests critiques "release gate"**
  - [x] API smoke critique avec PostgreSQL.
  - [x] Non-régression frontend structurelle.
  - [x] Vérification DB explain / requêtes clés.
  - [x] Exécution via une commande unique documentée.
  - [x] Livré le `2026-03-26` avec `scripts/run_release_gate.sh` et `docs/operations/J5_RELEASE_GATE.md`.
  - [x] Couverture pack: smoke API, DB explain, feature flag PostgreSQL et non-régression frontend structurelle.
  - [x] Intégration CI branchée sur `api-tests-postgresql`.

- [x] **T-10 — Observabilité minimale exploitable**
  - [x] Standardiser les logs applicatifs (format, niveau, corrélation).
  - [x] Définir un dashboard santé + une vue incidents.
  - [x] Définir la procédure d'escalade en cas de dérive.
  - [x] Livré le `2026-03-26` avec la vue opératoire `GET /api/operations/status` dans `src/api/main.py`.
  - [x] Logs API standardisés via `OPENINDEX_LOG_LEVEL` et format horodaté homogène.
  - [x] Références opératoires: `docs/operations/J5_OBSERVABILITY_BASELINE.md` et `docs/operations/EXPLOITATION.md`.

- [ ] **T-14 — Revoir l'UI pour le pilotage des tests et crawls**
  - [x] Vocabulaire exploration/explorateur aligné dans l'UI (livré le `2026-03-18`).
  - [x] Logs réels du worker dans l'UI (livré le `2026-03-18`).
  - [x] Progression basée sur le volume découvert/traité (livré le `2026-03-18`).
  - [x] Exposition des vraies files du worker (Dossiers, Fichiers, Somme de contrôle, Gros fichiers) (livré le `2026-03-18`).
  - [x] Actions arrêter/supprimer sur les runs récents (livré le `2026-03-18`).
  - [x] Garde-fou un seul run actif par espace (livré le `2026-03-18`).
  - [x] Transformer le tableau de bord en poste opérateur actif: espace courant, dernier lancement, état du crawl, KPI temps réel, progression et journal (livré le `2026-03-18`).
  - [x] ~~Implémenter le protocole de pré-estimation volumétrique avant exploration~~ — Annulé en raison de la charge serveur excessive. Le pilotage repose désormais sur les métriques runtime et le journal réel.
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
    - [x] Bouton "Piloter le crawl".
  - [x] Implémenter l'ouverture de configuration en overlay latéral droite -> gauche pour:
    - [x] Espaces crawler.
    - [x] Gestion de la base.
    - [ ] Inscription des utilisateurs (admin) — en attente d'authentification applicative.
    - [ ] Profil utilisateur — en attente d'authentification applicative.
  - [x] Implémenter "Piloter le crawl" sous forme de lightbox permettant de lancer, forcer ou arrêter un crawl.

- [x] **T-15 — Concevoir l'Explorateur de fichiers double panneau**
  - [x] Définir le comportement cible type Explorateur Windows / Dolphin.
  - [x] Prévoir navigation arborescente, sélection, transfert inter-panneaux et actions contextuelles.
  - [x] Déterminer les endpoints API nécessaires pour une navigation hiérarchique et des opérations de déplacement/copie pilotées.
  - [x] Prévoir le mode d'entrée dans le menu en cohérence avec les arbitrages de shell validés dans `docs/definition_ui.md`.
  - [x] Premier socle livré le `2026-03-30` dans `frontend/index.html` et `src/api/main.py` :
    - [x] Double panneau SMB indexé, panneau source lié à l'espace actif, panneau archivage lié à un second espace configuré.
    - [x] Navigation par répertoire, remontée au parent, sélection et rafraîchissement.
  - [x] Actions déjà disponibles :
    - [x] Archivage fichier par copie ou déplacement entre espaces configurés.
    - [x] Endpoint de lecture de fichier SMB.
    - [x] Lightbox PDF/images/vidéos et reconnaissance des formats bureautiques.
  - [x] Couverture technique déjà livrée :
    - [x] Endpoints `/api/explorer/items`, `/api/file-content` et `/api/archive/file`, plus tests API/structure frontend associés.
  - [x] Dette restante court terme :
    - [x] Rendu bureautique complet dans le lightbox — infrastructure deja en place dans l'API :
      - DOCX/DOC : `_preview_docx` (extraction XML paragraphs)
      - ODT : `_preview_odt` (extraction XML content)
      - PPTX/ODP : `_preview_pptx` / `_preview_odp` (slides texte)
      - XLSX/XLS : `_preview_xlsx` via openpyxl (tableaux HTML)
      - ODS : `_preview_ods` (tableaux HTML XML content)
      - Endpoint `/api/file-preview` expose le rendu HTML pour le lightbox frontend.
  - [x] Compléments livrés le `2026-03-30` :
    - [x] Vérification SHA-256 post-copie avant suppression source.
    - [x] Option de laisser un lien côté source.
    - [x] Mode overwrite piloté pour les conflits de destination.
  - [x] Dette restante moyen terme :
    - [x] Navigation SMB live hors index (endpoint `/api/explorer/live-items` ajouté le `2026-03-31`, PR #62).
    - [ ] Opérations de masse, menu contextuel type Explorateur Windows/Dolphin et meilleur traitement des erreurs SMB côté UI.
  - [x] PR fix/explorateur créée le `2026-03-31` avec version `0.4.1` (bump fix).

- [ ] **T-16 — Concevoir la page de traitements des artefacts**
  - [ ] Définir les catégories d'artefacts traitables: temporaires Office, doublons, fichiers système, archives obsolètes.
  - [ ] Prévoir KPI dédiés, liste filtrable, sélection multiple et actions de masse.
  - [ ] Déterminer les règles métiers entre suppression, ignorance et archivage.
  - [ ] Prévoir les actions unitaires et massives: supprimer, ignorer, archiver, sélectionner tout.

- [ ] **T-13 — Préparer la configuration multi-repository**
  - [ ] Définir le modèle de configuration pour plusieurs racines SMB.
  - [ ] Déterminer la stratégie d'identification par source/référentiel.
  - [ ] Adapter la doc opératoire pour éviter les recrawls monolithiques sur base active.

---

## 4) Dette documentaire à résorber

- [ ] **T-11 — Nettoyage docs historiques vs référence active**
  - [ ] Marquer explicitement les documents legacy.
  - [ ] Ajouter un index "où trouver la vérité" dans `docs/`.
  - [ ] Réduire les doublons roadmap/projet/todo.

- [ ] **T-12 — Gouvernance de preuve**
  - [ ] Chaque item clos doit pointer vers: commande exécutée, artefact, commit.
  - [ ] Remplacer tout marqueur implicite par une preuve vérifiable.

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

- [x] **P-05 — Dettes de stabilisation opérateur**
  - [x] Corrigé le `2026-03-19`: la lecture principale de progression s'appuie désormais sur le runtime réel du run actif; la dette résiduelle porte surtout sur les cas de refresh incohérent entre blocs.
  - [x] Corrigé le `2026-03-19`: le bloc `Runs récents` n'affiche plus `Aucun run enregistré` quand un état actif est connu par `monitoring`; un message de désynchronisation explicite prend le relais.
  - [x] Corrigé le `2026-03-19`: les runs bloqués trop longtemps en `cancelling` sont désormais réconciliés automatiquement vers `cancelled`.
  - [x] Corrigé le `2026-03-19`: les connexions WebSocket fermées sont purgées proprement avant les envois suivants, ce qui supprime le bruit `Cannot call "send" once a close message has been sent.`.
  - [x] Clôturé le `2026-03-19`: le prototype `estimate-{hash}` est abandonné explicitement; aucune archive dédiée supplémentaire n'est requise dans le chemin nominal.

- [x] **P-04 — Statut moteur et commandes opérateur explicites**
  - [x] Garder une barre de progression pour la quantité de données inventoriées.
  - [x] Ajouter des gommettes de couleur pour l'état moteur: arrêté, estimation, exploration, erreur, terminé.
  - [x] Basculer le bouton principal de `Lancer` vers `Arrêter` quand une exploration est en cours.
  - [x] Livré via les commits `1a2407a` et `f8fe00c`.

- [x] **P-03 — Traitement asynchrone sans limite artificielle**
  - [x] Supprimer les limites de taille des queues de traitement asynchrone.
  - [x] Vérifier que le backlog de vérification d'intégrité n'est plus artificiellement plafonné.
  - [x] Livré dans le crawler PostgreSQL; effet complet appliqué aux nouveaux runs après redéploiement du conteneur.

- [x] **P-02 — Indicateurs de progression lisibles et fiables**
  - [x] Exploiter les retours actuels du moteur pour des indicateurs de progression fiables.
  - [x] Présenter ces indicateurs sur une seule ligne, lisibles d'un coup d'oeil.
  - [x] Réserver les queues au diagnostic secondaire.
  - [x] Bug identifié le `2026-03-19`: l'API lisait un fichier fixe `smb_crawler_postgresql.log` alors que le crawler produit des logs par run `smb_crawler_postgresql_<run_id>.log`; conséquence directe: journal explorateur vide et indicateurs runtime à `0` malgré un run `running`.
  - [x] Clôturé le `2026-03-19`: le journal runtime réel et les indicateurs principaux de progression sont rétablis pour l'exploitation; les dettes résiduelles sont regroupées en `P-05`.
  - [x] Avancement utile livré: l'UI permet désormais de modifier une configuration d'espace existante, y compris de remplacer le mot de passe sans recréer l'espace; le secret courant n'est pas réaffiché et reste conservé si le champ mot de passe est laissé vide.

- [x] **P-01 — Pré-estimation volumétrique avant exploration**
  - [x] Revoir le protocole moteur pour obtenir une estimation la plus fidèle possible du volume total avant exploration.
  - [x] Hypothèse rejetée en exploitation: l'approche `worker Docker éphémère + montage CIFS + du -sb` n'est pas viable dans son état actuel pour un budget opérateur raisonnable; elle ne doit plus être considérée comme cible par défaut.
  - [x] Décision appliquée dans le code: les nouveaux runs partent directement en `queued`; le pilotage opérateur repose sur les métriques runtime et le journal réel.
  - [x] Décision de schéma: les colonnes `estimated_total_size` et `estimate_*` sont retirées de `crawl_runs` sur la base de test; on repart sur une structure minimale cohérente avec le flux réel.
  - [x] Dette documentaire: archiver l'historique du prototype `estimate-{hash}` dans une note dédiée si l'on veut conserver la trace d'exploitation, mais ne plus le laisser polluer le chemin nominal.
  - [x] Clôturé le `2026-03-19`: le pilotage runtime en production répond désormais au besoin opérateur; il n'y a plus de raison de poursuivre la pré-estimation volumétrique avant exploration.

- [x] **P-00c — Fuseau horaire homogène et configurable**
  - [x] Aligner les conteneurs Docker sur un fuseau horaire explicite.
  - [x] Rendre le fuseau d'affichage configurable dans l'interface via l'engrenage.
  - [x] Afficher les dates de build et d'exécution dans le fuseau choisi.
  - [x] Livré via le commit `1a2407a`.

- [x] **P-00b — Réconciliation des runs zombies**
  - [x] Ajouter une logique défensive pour reclassifier les runs stale laissés `running` par le moteur.
  - [x] Exposer un état opérateur clair quand le moteur n'émet plus mais que la base n'est pas cohérente.
  - [x] Livré via les commits `1a2407a` et `f8fe00c`.

- [x] **P-00 — Finalisation fiable des runs d'exploration**
  - [x] Corriger la chaîne de fin de run pour qu'un crawl terminé ou timeouté écrive toujours un statut final explicite en base.
  - [x] Ajouter un signal et une trace `run terminé` / `run en échec` côté moteur.
  - [x] Empêcher qu'un run reste `running` en base sans activité réelle du moteur.
  - [x] Livré via les commits `1a2407a` et `f8fe00c`.