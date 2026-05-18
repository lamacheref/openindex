# Guide d'Administration de l'Indexation

**Date de création :** 18 mai 2026
**Version :** 1.0
**Auteur :** Cline
**Dernière modification :** 18 mai 2026

---

## Table des Matières

1. [Introduction](#introduction)
2. [Configuration des Espaces SMB](#configuration-des-espaces-smb)
3. [Lancement Manuel d'une Indexation](#lancement-manuel-dune-indexation)
4. [Monitoring des Jobs](#monitoring-des-jobs)
5. [Résolution des Problèmes Courants](#résolution-des-problèmes-courants)
6. [Annexes](#annexes)

---

## Introduction

Ce guide décrit les procédures d'administration pour le système d'indexation OpenIndex. Il couvre la configuration, l'exécution et le monitoring des opérations d'indexation.

---

## Configuration des Espaces SMB

### Prérequis

- Accès à la base de données PostgreSQL
- Droits d'administration sur l'interface OpenIndex
- Informations de connexion SMB valides

### Procédure

1. **Accéder à l'interface d'administration**
   - Connectez-vous à l'interface OpenIndex
   - Naviguez vers la section "Configuration SMB"

2. **Ajouter un nouvel espace SMB**
   ```bash
   POST /api/smb/spaces
   {
     "name": "Nom de l'espace",
     "host": "adresse_du_serveur",
     "share": "nom_du_partage",
     "username": "utilisateur",
     "password": "mot_de_passe",
     "domain": "domaine"
   }
   ```

3. **Vérifier la configuration**
   - Utilisez l'endpoint de test de connexion :
   ```bash
   GET /api/smb/spaces/{id}/test
   ```

4. **Configurer les filtres d'artefacts**
   - Définissez les patterns de fichiers à exclure :
   ```bash
   POST /api/artefact-filters
   {
     "pattern": "*.tmp",
     "description": "Fichiers temporaires"
   }
   ```

---

## Lancement Manuel d'une Indexation

### Procédure Standard

1. **Créer un job d'indexation**
   ```bash
   POST /api/indexer/jobs
   {
     "config_id": "ID_de_la_configuration_SMB",
     "path": "/chemin/à/indexer",
     "recursive": true,
     "max_depth": 10
   }
   ```

2. **Vérifier le statut du job**
   ```bash
   GET /api/indexer/jobs/{job_id}
   ```

3. **Monitorer la progression**
   - Utilisez l'interface de monitoring ou l'endpoint :
   ```bash
   GET /api/indexer/jobs/{job_id}/progress
   ```

### Options Avancées

- **Indexation incrémentielle** : Ajoutez `"incremental": true` pour ne traiter que les fichiers modifiés
- **Priorité de queue** : Spécifiez `"queue_type": "fast"` ou `"slow"` selon la taille des fichiers
- **Planification différée** : Utilisez `"schedule_for": "2026-05-19T02:00:00"` pour un lancement ultérieur

---

## Monitoring des Jobs

### Tableau de Bord

1. **Accéder au dashboard d'indexation**
   - URL : `/indexer-monitoring.html`
   - Affiche les métriques en temps réel :
     - Jobs en cours
     - Fichiers traités
     - Vitesse d'indexation
     - Taux d'erreur

2. **Endpoints API de Monitoring**
   ```bash
   # Statistiques globales
   GET /api/indexer/stats

   # Liste des jobs
   GET /api/indexer/jobs

   # Détails d'un job spécifique
   GET /api/indexer/jobs/{job_id}

   # Performance en temps réel
   GET /api/indexer/performance
   ```

### Alertes

- Configurez des alertes pour :
  - Jobs échoués (`status: failed`)
  - Taux d'erreur > 5%
  - Durée d'indexation anormale

---

## Résolution des Problèmes Courants

### Problème : Connexion SMB échouée

**Symptômes :**
- Erreur "Connection refused"
- Timeout lors de la connexion

**Solutions :**
1. Vérifier les informations d'identification
2. Tester la connectivité réseau :
   ```bash
   smbclient -L //serveur/partage -U utilisateur
   ```
3. Vérifier que le service SMB est en cours d'exécution sur le serveur

### Problème : Fichiers verrouillés

**Symptômes :**
- Erreurs "Access denied"
- Fichiers marqués comme "locked"

**Solutions :**
1. Activer le mécanisme de réessai automatique :
   ```bash
   # Vérifier les fichiers en réessai
   GET /api/indexer/retries
   ```
2. Configurer le nombre maximal de tentatives (par défaut : 3)
3. Pour les fichiers critiques, augmenter le délai entre les tentatives

### Problème : Performances lentes

**Symptômes :**
- Vitesse d'indexation < 10 fichiers/seconde
- Utilisation CPU élevée

**Solutions :**
1. Vérifier les index de la base de données :
   ```bash
   # Optimiser les index
   POST /api/indexer/optimize
   ```
2. Activer le batch insert :
   ```bash
   # Configurer dans indexer_worker.py
   _batch_insert_enabled = True
   _batch_size = 100
   ```
3. Réduire la profondeur maximale de scan :
   ```bash
   "max_depth": 5
   ```

---

## Annexes

### Commandes Utiles

```bash
# Redémarrer le worker d'indexation
docker restart openindex_indexer

# Vérifier les logs
docker logs openindex_indexer

# Tester la connexion à la base de données
psql -h localhost -U openindex -d openindex

# Vérifier l'état de santé
GET /api/indexer/health
```

### Bonnes Pratiques

1. **Sauvegardes** : Effectuez des sauvegardes avant les opérations majeures
2. **Tests** : Validez toujours les configurations sur un environnement de test
3. **Monitoring** : Activez les alertes pour une détection précoce des problèmes
4. **Documentation** : Mettez à jour ce guide après chaque modification majeure

---

**Fin du document**