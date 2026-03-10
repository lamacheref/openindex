# Option commando — plan d'accélération (2 semaines)

## Objectif

Livrer une avancée visible et exploitable en **10 jours ouvrés** en sécurisant le socle J3 (SQLite), puis en préparant la bascule J4 (PostgreSQL) sans effet tunnel.

## Cadre d'exécution

- **Durée** : 2 semaines, 5 jours/semaine.
- **Rythme** : daily 15 min, revue technique mi-semaine, démo + rétro chaque vendredi.
- **Principe** : pas de nouvelle feature non critique tant que la reproductibilité tests + runbook exploitation ne sont pas validés.
- **Règle de priorisation** : fiabilité > migration > confort développeur.

## Équipe recommandée

- 1 lead technique (arbitrage + cohérence architecture).
- 1 dev API/data (FastAPI + adaptateurs DB).
- 1 dev qualité/intégration (tests + CI + doc d'exploitation).
- 1 contributeur transverse (frontend léger + outillage + bugfix).

## Backlog commando (ticketisé)

### Semaine 1 — Stabilisation exécutable J3

| ID | Ticket | Priorité | Estimation | Dépendances | Critère d'acceptation |
|---|---|---|---|---|---|
| CMD-01 | Standardiser l'environnement de test (requirements/dev + script unique) | P0 | M | - | Un contributeur neuf exécute les tests avec une seule commande |
| CMD-02 | Fiabiliser les tests API critiques (`/health`, `/api/stats`, `/api/files`, `/api/db-explain`) | P0 | M | CMD-01 | Les tests passent en local et en CI sans flakiness sur 5 runs |
| CMD-03 | Ajouter un test de non-régression frontend sur les vues clés | P0 | S | CMD-01 | Le test détecte au moins une régression structurelle de navigation |
| CMD-04 | Rédiger le runbook incident SQLite (DB absente/corrompue) | P0 | S | - | Procédure testée une fois, avec temps de recovery mesuré |
| CMD-05 | Clarifier CI de référence (J3) et statut du legacy | P1 | S | - | Documentation unique de pipeline + conventions de merge explicites |
| CMD-06 | Ajouter section "limitations connues" | P1 | S | - | README contient limites, impacts et contournements |

### Semaine 2 — Readiness J4 sans big bang

| ID | Ticket | Priorité | Estimation | Dépendances | Critère d'acceptation |
|---|---|---|---|---|---|
| CMD-07 | Définir critères go/no-go J3 -> J4 | P0 | S | CMD-05 | Critères mesurables validés en revue (perf, rollback, migration) |
| CMD-08 | Introduire adaptateur PostgreSQL en mode parallèle (feature flag) | P0 | L | CMD-02 | API fonctionnelle SQLite et PostgreSQL sans rupture de contrat |
| CMD-09 | Écrire migration J3 -> J4 (dry-run) | P0 | M | CMD-08 | Script dry-run exécutable + journal de migration + rollback |
| CMD-10 | Ajouter bench comparatif SQLite vs PostgreSQL sur endpoints critiques | P1 | M | CMD-08 | Rapport comparatif P95 publié et historisé |
| CMD-11 | Étendre CI pour couvrir mode SQLite + PostgreSQL | P1 | M | CMD-08 | Pipeline exécute 2 matrices DB avec statut clair |
| CMD-12 | Préparer checklist de release commando | P1 | S | CMD-04, CMD-07 | Aucune release sans checklist complète |

## Plan journalier (10 jours)

### Semaine 1

- **J1** : cadrage, découpage tickets, mise en place CMD-01.
- **J2** : finaliser CMD-01 + démarrer CMD-02.
- **J3** : finir CMD-02 + implémenter CMD-03.
- **J4** : CMD-04 + validation incident simulé.
- **J5** : CMD-05/CMD-06 + démo de stabilité J3.

### Semaine 2

- **J6** : cadrage go/no-go (CMD-07) + design adaptateur (CMD-08).
- **J7** : implémentation CMD-08 (branche de migration).
- **J8** : CMD-09 (dry-run migration) + début CMD-11.
- **J9** : CMD-10 (bench) + finalisation CMD-11.
- **J10** : CMD-12 + revue finale + décision de passage J4.

## Gouvernance commando

## Rituels

- **Daily commando** (15 min): blocages, risques, arbitrages immédiats.
- **Point qualité** (20 min/jour): état tests, dette ouverte, incidents.
- **Comité go/no-go** (fin S2): décision documentée avec métriques.

## Règles opérationnelles

- PR petites (<300 lignes modifiées si possible).
- Toute PR doit inclure preuve de test ou justification explicite.
- Aucun ticket P1 ouvert si un P0 est bloqué.
- Tout incident rencontré en sprint produit une action préventive versionnée.

## Tableau de pilotage (KPI)

- Taux de succès pipeline (objectif >= 95% sur la semaine).
- Temps moyen de réparation test cassé (objectif < 4h).
- Nombre de tests flakies (objectif = 0 en fin S1).
- P95 `/api/files` et `/api/stats` avant/après (objectif: stable ou en baisse).
- Temps de recovery SQLite (objectif: procédure validée < 30 min).

## Registre des risques + mitigation

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Dérive périmètre (ajout de features non critiques) | Élevée | Élevé | Feature freeze partiel + validation lead technique |
| Blocage dépendances environnement | Moyen | Élevé | Script bootstrap unique + image dev reproductible |
| Migration PostgreSQL incomplète | Moyen | Élevé | Dual-mode temporaire + dry-run obligatoire + rollback |
| CI instable | Moyen | Moyen | Réduction des jobs non essentiels + priorisation jobs critiques |
| Manque de visibilité décisionnelle | Faible | Élevé | KPI quotidiens + comité go/no-go formel |

## Livrables attendus fin option commando

1. Environnement de validation reproductible pour l'équipe.
2. Pack de tests critiques J3 fiable.
3. Runbook exploitation SQLite utilisable en incident.
4. Critères de bascule J4 validés.
5. Adaptateur PostgreSQL parallèle + dry-run migration.
6. Rapport de performance comparatif.
7. Checklist de release prête à l'usage.

## Modèle de suivi quotidien (copier-coller)

```markdown
### Point commando — JJ/MM
- Tickets clos:
- Tickets en cours:
- Blocages:
- Risques nouveaux:
- KPI du jour (pipeline, flakiness, perf):
- Décisions prises:
- Plan J+1:
```
