# TODO OpenIndex — suite post-commando (J4 -> J5)

## Priorités opérateur à traiter en tête

- [ ] **P-01 — Pré-estimation volumétrique avant exploration**
  - Revoir le protocole moteur pour obtenir une estimation la plus fidèle possible du volume total avant exploration.
  - Hypothèse rejetée en exploitation: l'approche `worker Docker éphémère + montage CIFS + du -sb` n'est pas viable dans son état actuel pour un budget opérateur raisonnable; elle ne doit plus être considérée comme cible par défaut.
  - Décision appliquée dans le code: les nouveaux runs partent directement en `queued`; le pilotage opérateur repose sur les métriques runtime et le journal réel.
  - Décision de schéma: les colonnes `estimated_total_size` et `estimate_*` sont retirées de `crawl_runs` sur la base de test; on repart sur une structure minimale cohérente avec le flux réel.
  - Dette documentaire: archiver l'historique du prototype `estimate-{hash}` dans une note dédiée si l'on veut conserver la trace d'exploitation, mais ne plus le laisser polluer le chemin nominal.
  - Nouveau cap retenu: privilégier un suivi précis des métriques et logs runtime pendant l'exploration, plutôt qu'une barre de progression fondée sur une pré-estimation volumétrique lente ou fragile.

- [ ] **P-02 — Indicateurs de progression lisibles et fiables**
  - Exploiter les retours actuels du moteur pour des indicateurs de progression fiables.
  - Présenter ces indicateurs sur une seule ligne, lisibles d'un coup d'oeil.
  - Réserver les queues au diagnostic secondaire.
  - Dette UI constatée en exploitation: la page agrège aujourd'hui des sources hétérogènes (`/api/stats`, `/api/crawls/overview`, `/api/crawler/runtime`) et peut afficher un état incohérent, par exemple un run actif avec `Runs récents` vide ou des KPI historiques non alignés avec le run courant.
  - À corriger: définir une hiérarchie de vérité par bloc d'interface, gérer explicitement les erreurs de refresh, et éviter d'afficher `Aucun run enregistré` tant qu'un état actif est connu par une autre source.
  - Avancement utile livré: l'UI permet désormais de modifier une configuration d'espace existante, y compris de remplacer le mot de passe sans recréer l'espace; le secret courant n'est pas réaffiché et reste conservé si le champ mot de passe est laissé vide.

- [x] **P-03 — Traitement asynchrone sans limite artificielle**
  - Supprimer les limites de taille des queues de traitement asynchrone.
  - Vérifier que le backlog de vérification d'intégrité n'est plus artificiellement plafonné.
  - Livré dans le crawler PostgreSQL; effet complet appliqué aux nouveaux runs après redéploiement du conteneur.

- [x] **P-04 — Statut moteur et commandes opérateur explicites**
  - Garder une barre de progression pour la quantité de données inventoriées.
  - Ajouter des gommettes de couleur pour l'état moteur: arrêté, estimation, exploration, erreur, terminé.
  - Basculer le bouton principal de `Lancer` vers `Arrêter` quand une exploration est en cours.
  - Livré via les commits `1a2407a` et `f8fe00c`.

- [x] **P-00 — Finalisation fiable des runs d'exploration**
  - Corriger la chaîne de fin de run pour qu'un crawl terminé ou timeouté écrive toujours un statut final explicite en base.
  - Ajouter un signal et une trace `run terminé` / `run en échec` côté moteur.
  - Empêcher qu'un run reste `running` en base sans activité réelle du moteur.
  - Livré via les commits `1a2407a` et `f8fe00c`.

- [x] **P-00b — Réconciliation des runs zombies**
  - Ajouter une logique défensive pour reclassifier les runs stale laissés `running` par le moteur.
  - Exposer un état opérateur clair quand le moteur n'émet plus mais que la base n'est pas cohérente.
  - Livré via les commits `1a2407a` et `f8fe00c`.
  - Dette mineure restante: un run arrêté peut encore rester bloqué en `cancelling` trop longtemps si le worker ne finalise pas proprement; ajouter une réconciliation tardive vers `cancelled`.

- [x] **P-00c — Fuseau horaire homogène et configurable**
  - Aligner les conteneurs Docker sur un fuseau horaire explicite.
  - Rendre le fuseau d'affichage configurable dans l'interface via l'engrenage.
  - Afficher les dates de build et d'exécution dans le fuseau choisi.
  - Livré via le commit `1a2407a`.
  - Dette mineure restante: le flux WebSocket API peut encore journaliser `Cannot call "send" once a close message has been sent.` quand un client se déconnecte; fiabiliser la purge des connexions fermées.

## Objectif

Passer d'une **readiness J4 documentée** à une **exécution J4 pilotée par preuves**, puis enclencher J5 (qualité & observabilité) avec critères de sortie mesurables.

---

## 1) Priorités immédiates (Semaine en cours)

- [x] **T-01 — Clôturer CMD-12 (checklist release commando) avec preuves**
  - Vérifier CI verte sur PostgreSQL (backend unique).
  - Migration de DB non requise : re-crawl complet prévu sur zone de test massivement modifiée avec PostgreSQL.
  - Vérifier bench comparatif publié avec PostgreSQL.
  - Vérifier rollback relu par un pair.
  - Mettre à jour `CHANGELOG.md` pour le lot de clôture.
  - Commit: `124140d`

- [x] **T-02 — Décision formelle Go/No-Go J4**
  - Appliquer les critères de `docs/phases/J4_MIGRATION.md`.
  - Décision rédigée le `2026-03-18` dans `docs/2026-03-18_j4_go-no-go.md`.
  - Décision retenue: `Go`.
  - Preuves: recrawl contrôlé, benchmark 3 runs stable, rollback drill validé, CI GitHub PostgreSQL verte sur PR `#41`.
  - Commit: `17f5806`

- [x] **T-03 — Figer la baseline technique J4**
  - Confirmer PostgreSQL comme backend de données unique dans la doc principale.
  - Aligner `README.md`, `README.stack.md`, `ROADMAP.md` et ce `TODO.md`.
  - Supprimer les ambiguïtés "actif vs legacy" dans les parcours opératoires.
  - État propagé: `README.md`, `README.stack.md`, `ROADMAP.md`, `TODO.md`.
  - Commit: `40c691b`

---

## 2) Exécution J4 (prochaines 2 semaines)

- [ ] **T-04a — Corriger le faux crawl complet PostgreSQL**
  - Le résultat J4 actif du `2026-03-18` est invalide: le crawler PostgreSQL ne descendait pas récursivement dans les sous-répertoires.
  - Finaliser le correctif de récursion dans `src/smb_crawler_postgresql.py`.
  - Rejouer un crawl complet sur `\\172.16.252.34\Public\SMIDEN` et invalider les artefacts précédents trop superficiels.
  - Produire un artefact final cohérent avec la volumétrie réelle du référentiel.

- [ ] **T-04 — Initialisation contrôlée J4 sur PostgreSQL en environnement de référence**
  - Initialiser PostgreSQL sur un dataset représentatif recrawlé.
  - Exécuter un recrawl complet sur environnement cible avec PostgreSQL (pas de migration SQLite).
  - Produire un rapport d'initialisation avec PostgreSQL (durée, volume, incidents, rollback readiness).

- [ ] **T-05 — Validation de performance post-bascule**
  - Rejouer le benchmark PostgreSQL sur endpoints critiques et comparer à la baseline historique SQLite.
  - Vérifier le respect des seuils P95 annoncés avec PostgreSQL.
  - Publier les résultats dans `docs/` avec conclusion explicite (OK / NOK) et intégration de PostgreSQL.

- [ ] **T-06 — Renforcement CI dual DB**
  - Rendre obligatoire le passage des jobs CI PostgreSQL avant merge.
  - Ajouter la collecte d'artefacts minimaux en cas d'échec (logs API/tests).
  - Documenter le chemin de diagnostic rapide en cas de pipeline rouge.

- [ ] **T-07 — Drill de rollback J4**
  - Simuler un incident post-migration PostgreSQL.
  - Exécuter le rollback complet avec chronométrage.
  - Capitaliser la procédure réelle dans `docs/operations/EXPLOITATION.md`.

---

## 3) Préparation J5 (qualité & observabilité)

- [ ] **T-08 — Définir les SLI/SLO opérationnels minimum**
  - Disponibilité API, latence P95, taux d'erreurs, temps de recovery.
  - Seuils d'alerte + responsables + fréquence de revue.

- [ ] **T-09 — Pack de tests critiques "release gate"**
  - API smoke critique avec PostgreSQL.
  - Non-régression frontend structurelle.
  - Vérification DB explain / requêtes clés.
  - Exécution via une commande unique documentée.

- [ ] **T-10 — Observabilité minimale exploitable**
  - Standardiser les logs applicatifs (format, niveau, corrélation).
  - Définir un dashboard santé + une vue incidents.
  - Définir la procédure d'escalade en cas de dérive.

- [ ] **T-14 — Revoir l'UI pour le pilotage des tests et crawls**
  - Repenser l'interface actuelle, jugée insuffisante pour le suivi opérationnel.
  - Transformer le tableau de bord en poste opérateur actif: espace courant, dernier lancement, état du crawl, KPI temps réel, progression et journal.
  - Implémenter un protocole de pré-estimation volumétrique avant exploration pour fiabiliser la progression, selon `docs/operations/CRAWL_PRE_ESTIMATION_PROTOCOL.md`.
  - Corriger les finitions demandées dans `docs/definition_ui.md`: nom distinctif d'espace, "non défini" si dernier lancement absent, zone version réduite, suppression du sous-titre inutile, unités en octets, bouton logs déplacé sous la progression et désactivé si le crawler est inactif.
  - Déjà livré le `2026-03-18`: vocabulaire exploration/explorateur, logs réels du worker, progression par volume, queues réelles, actions arrêter/supprimer sur les runs récents et garde-fou un seul run actif par espace.
  - Déporter les explications de conception ou limites techniques hors de l'interface vers `TODO.md` ou la documentation.
  - Rendre visibles les statuts en cours, succès, échecs, durée, artefacts et journaux utiles directement dans l'UI finale.
  - Supprimer les vues de démonstration ou décoratives qui ne servent pas l'exploitation réelle.
  - Prévoir un écran de suivi temps réel orienté exploitation plutôt qu'une simple consultation statique.
  - Rendre actifs les éléments de shell: cloche de notifications, engrenage de configuration et bouton "Piloter le crawl".
  - Implémenter l'ouverture de configuration en overlay latéral droite -> gauche pour: espaces crawler, gestion de la base, inscription utilisateurs, profil utilisateur.
  - Implémenter "Piloter le crawl" sous forme de lightbox permettant de lancer, forcer ou arrêter un crawl.

- [ ] **T-15 — Concevoir l'Explorateur de fichiers double panneau**
  - Définir le comportement cible type Explorateur Windows / Dolphin.
  - Prévoir navigation arborescente, sélection, transfert inter-panneaux et actions contextuelles.
  - Déterminer les endpoints API nécessaires pour une navigation hiérarchique et des opérations de déplacement/copie pilotées.
  - Prévoir le mode d'entrée dans le menu en cohérence avec les arbitrages de shell validés dans `docs/definition_ui.md`.

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
