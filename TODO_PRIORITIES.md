# TODO.md - Priorités Réorganisées

Ce fichier contient la liste des tâches à effectuer pour le projet OpenIndex, classées par ordre d'importance et organisées par phases.

## 🎯 Priorités Avant 19 Mars 2026 (Deadline DGS)

### 🔥 URGENT - Semaine 1-5 Mars 2026
- [ ] 🧪 **Tester le crawler amélioré** : Lancer crawl avec credentials admin (adminsmiden/Us52uK)
- [ ] 🚀 **Déployer crawler existant** : Mettre en production le crawler SMB fonctionnel
- [ ] 🗄️ **Migrer vers PostgreSQL** : Configurer base de données robuste avec scripts de migration
- [ ] 📊 **Lancer crawl complet** : Collecter données réelles depuis SMB (>2 To)
- [ ] 🔌 **Créer API FastAPI minimale** : Endpoints de lecture pour les données collectées
- [ ] ✅ **Valider données réelles** : Vérifier accessibilité et intégrité des données

### ⚡ HAUTE PRIORITÉ - Semaine 8-12 Mars 2026
- [ ] ⚛️ **Structure React + Material-UI** : Base de l'interface moderne
- [ ] 🌳 **Arborescence avec vraies données** : Composant tree utilisant données réelles
- [ ] 📈 **Dashboard avec métriques réelles** : Statistiques et visualisations
- [ ] 🔍 **Gestion des doublons réels** : Interface avec vrais fichiers doublons
- [ ] 📋 **Layout fixe avec onglets** : Structure VanillaJS, pas de personnalisation utilisateur
- [ ] 🎯 **Mode focus** : Panneau principal + volets latéraux repliables
- [ ] 🖥️ **Responsive desktop** : Priorité bureau (mobile/tablette plus tard)
- [ ] 📑 **Navigation par onglets** : Tableau bord, Fichiers, Doublons, Configuration, Export

### 📈 MOYENNE PRIORITÉ - Semaine 15-19 Mars 2026
- [ ] 🤖 **Intégrer service IA Ollama** : Configuration Docker et modèles
- [ ] 🧠 **Développer API IA** : Endpoints pour résumés et analyse
- [ ] 📄 **Résumés automatiques PDF/DOCX** : Traitement par lots en nuit
- [ ] 📊 **Extraction données Excel** : Analyse structurée des tableurs
- [ ] 🖼️ **Description images/vidéos** : Modèles LLaVA pour contenus visuels
- [ ] 🎨 **Design responsive final** : Adaptation mobile/tablette/desktop
- [ ] 🐳 **Dockerisation complète** : Frontend + Backend + Base de données + Service IA
- [ ] 🔄 **Tests d'intégration E2E** : Validation complète avec données réelles et IA
- [ ] 📚 **Documentation déploiement** : Guide d'installation et maintenance IA incluse
- [ ] 🚀 **Livraison production** : Version finale avec IA intégrée (deadline 19 mars)

---

## 📋 Fonctionnalités Avancées (Après 19 Mars 2026)

### 🔐 Authentification & Sécurité (Long terme)
- [ ] 🔐 **Intégration Keycloak** : Active Directory local + fédération possible (Pas ici / Cette partie est à long terme !)
- [ ] 🛡️ **Gestion rôles étendue** : Agents/Modérateur groupe, Modérateur DGS, Admin
- [ ] ⏰ **Session timeout 20mn** : Déconnexion automatique après inactivité
- [ ] 🌐 **Support multi-fédération** : Azure AD, Google Workspace extensibles

### 📧 Communication & Notifications
- [ ] 📧 **Email digest hebdomadaire** : Résumé post-crawl avec actions requises
- [ ] 🔔 **Notifications in-app** : Alertes temps réel pour actions critiques
- [ ] 🔗 **Webhooks one-click** : Boutons dans email pour archiver/refuser fichiers
- [ ] 🏖️ **Configuration vacances** : Périodes flexibles (2 sem. mars, 5 sem. été)
- [ ] ⚙️ **Workflow validation admin** : Gestion faux-positifs fichiers non-professionnels

### 💾 Backup & Archivage Intelligent
- [ ] 📅 **Archivage automatique 2 ans** : Fichiers >730 jours déplacés vers NAS
- [ ] 💾 **Gros fichiers >100MB** : Archivage automatique avec liens symboliques
- [ ] 🔗 **Liens symboliques transparents** : Accès utilisateur maintenu après archivage
- [ ] 🗄️ **Infrastructure hybride** : 2To cloud + 23To NAS/SAN locaux
- [ ] 📏 **Identification fichiers volumineux** : Alertes et suggestions d'archivage

### 🔄 Résilience & Monitoring
- [ ] 🔄 **Retry intelligent personnalisé** : Pattern 1,2,5,15,30,60,120min adapté VM
- [ ] 🖥️ **Détection serveur intelligent** : Validation BDD (2min timeout)
- [ ] ⏱️ **Adaptation reboot VM** : Temps 2-20min pour redémarrage
- [ ] 🔄 **Continuation scan automatique** : Poursuite si possible, erreur si impossible
- [ ] 👷 **Workers individuels** : Relance automatique workers en échec
- [ ] 📊 **Monitoring crawler temps réel** : État workers + métriques performance
- [ ] ⚡ **Alertes WebSocket** : Légèreté maximale sans surcharge
- [ ] 📝 **Historique externe** : Backup journalier sans rétention en base

### 🧹 Nettoyage & Optimisation
- [ ] 🧹 **Nettoyage fichiers Windows inutiles** : Thumbs.db, desktop.ini, .lnk automatiquement filtrés
- [ ] 📁 **Suppression dossiers vides** : Nettoyage automatique de l'arborescence
- [ ] 🔍 **Détection fichiers corrompus** : Analyse par extension et taille anormale
- [ ] 🗑️ **Fichiers temporaires Office** : Identification automatique ~$*.tmp, ~$*.docx
- [ ] ⚠️ **Fichiers non-professionnels** : IA locale pour détecter contenus inappropriés
- [ ] 👤 **Traçabilité propriétaires** : Intégration SMB owner pour gestion utilisateur
- [ ] ⏱️ **Timeouts configurables** : Adaptation horaire pour ne pas surcharger serveur
- [ ] 🚀 **Queue prioritaire gros fichiers** : Traitement séparé >100MB vs <100MB

---

## 📊 Résumé des Priorités

| Priorité | Tâches | Deadline | Statut |
|----------|--------|----------|--------|
| 🔥 URGENT | 6 tâches critiques | 5 mars 2026 | À faire |
| ⚡ HAUTE | 8 tâches frontend | 12 mars 2026 | Planifié |
| 📈 MOYENNE | 10 tâches IA/production | 19 mars 2026 | Planifié |
| 📋 AVANCÉ | 35+ tâches | Après mars 2026 | Planifié |

**Total avant 19 mars : 24 tâches prioritaires**  
**Total après 19 mars : 35+ tâches avancées**

---

## 🏆 Tâches Terminées

| Date       | Commit    | Description                                                                 | Statut |
|------------|-----------|-----------------------------------------------------------------------------|--------|
| 2026-02-25 | `65531ad` | Intégration IA locale Ollama et optimisations avancées                       | ✅     |
| 2026-02-25 | `72608f6` | Système de communication utilisateur avancé                                  | ✅     |
| 2026-02-25 | `484ebda` | Intégration Active Directory et gestion utilisateurs avancée                 | ✅     |
| 2026-02-25 | `a66820a` | Système backup automatique et archivage intelligent                         | ✅     |
| 2026-02-25 | `bd72aa8` | Système retry et résilience avancé pour VMs                                 | ✅     |
| 2026-02-25 | `0f16e11` | Interface utilisateur React : layout fixe avec mode focus                   | ✅     |
| 2026-02-25 | `5bf925b` | Authentification SSO Keycloak et rôles étendus                              | ✅     |
| 2026-02-25 | `d6b7c8c` | Monitoring crawler avancé : WebSocket + historique externe                    | ✅     |
| 2026-02-25 | `e7bbc0a` | Finaliser le crawler SMB récursif complet                                   | ✅     |

---

## 📝 Instructions

1. **Priorité absolue** : Focus sur les 24 tâches avant 19 mars 2026
2. **Validation continue** : Tester chaque étape avant de passer à la suivante
3. **Documentation** : Mettre à jour le rapport après chaque jalon majeur
