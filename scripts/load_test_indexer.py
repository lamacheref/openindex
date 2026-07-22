#!/usr/bin/env python3
"""
Script de test de charge pour l'indexeur OpenIndex (protocole Phase A/B)
Génère une structure de fichiers de test et mesure les performances d'indexation
via l'API REST.

Prérequis :
  - Une crawl_config SMB pointant sur un partage accessible depuis le LXC
  - Le chemin de génération des fichiers doit correspondre au start_path de la config
  - Les services openindex-api et indexer-worker doivent tourner

Usage :
  python scripts/load_test_indexer.py --config <config_id> --path /mnt/share/test --files 10000

Auteur: Cline
Date: 22 juillet 2026
Version: 2.0 (Phase A/B)
"""

import os
import time
import random
import string
import subprocess
import psutil
import json
import argparse
from datetime import datetime
from pathlib import Path

class LoadTestIndexer:
    def __init__(self, base_path="/tmp/openindex_load_test", file_count=10000, max_depth=5):
        """
        Initialise le test de charge

        Args:
            base_path: Chemin de base pour la génération des fichiers
            file_count: Nombre total de fichiers à générer
            max_depth: Profondeur maximale des répertoires
        """
        self.base_path = Path(base_path)
        self.file_count = file_count
        self.max_depth = max_depth
        self.start_time = None
        self.end_time = None
        self.metrics = {
            'total_files': 0,
            'total_size_mb': 0,
            'indexing_time_seconds': 0,
            'cpu_usage_percent': 0,
            'memory_usage_mb': 0,
            'files_per_second': 0,
            'mb_per_second': 0
        }

    def generate_random_string(self, length=10):
        """Génère une chaîne aléatoire"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def create_test_structure(self):
        """Crée une structure de répertoires et fichiers de test"""
        print(f"Création de la structure de test avec {self.file_count} fichiers...")

        # Supprimer l'ancien dossier s'il existe
        if self.base_path.exists():
            subprocess.run(['rm', '-rf', str(self.base_path)], check=True)

        self.base_path.mkdir(parents=True, exist_ok=True)

        files_created = 0
        total_size = 0

        # Créer des répertoires et fichiers de manière récursive
        for i in range(self.file_count):
            # Déterminer la profondeur actuelle
            current_depth = random.randint(1, self.max_depth)
            path_parts = [self.generate_random_string(8) for _ in range(current_depth)]
            file_path = self.base_path.joinpath(*path_parts)

            # Créer les répertoires parents
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Créer le fichier avec du contenu aléatoire
            file_size = random.randint(1024, 10240)  # 1KB à 10KB
            content = self.generate_random_string(file_size)

            with open(file_path, 'w') as f:
                f.write(content)

            files_created += 1
            total_size += len(content.encode('utf-8'))

            # Afficher la progression
            if files_created % 1000 == 0:
                print(f"Fichiers créés: {files_created}/{self.file_count}")

        self.metrics['total_files'] = files_created
        self.metrics['total_size_mb'] = total_size / (1024 * 1024)

        print(f"Structure de test créée: {files_created} fichiers, {total_size/(1024*1024):.2f} MB")

    def monitor_system_resources(self):
        """Surveille l'utilisation des ressources système"""
        process = psutil.Process(os.getpid())
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_info = process.memory_info().rss / (1024 * 1024)  # MB

        return {
            'cpu_percent': cpu_percent,
            'memory_mb': memory_info
        }

    def run_indexing_job(self, config_id, api_url="http://localhost:8000"):
        """Lance un job d'indexation via l'API (protocole Phase A/B)"""
        print("Lancement du job d'indexation...")

        # Phase A/B accepte uniquement config_id
        payload = {"config_id": config_id}

        try:
            result = subprocess.run([
                'curl', '-X', 'POST',
                f'{api_url}/api/indexer/jobs',
                '-H', 'Content-Type: application/json',
                '-d', json.dumps(payload)
            ], capture_output=True, text=True, check=True)

            job_data = json.loads(result.stdout)
            job_id = job_data['id']
            print(f"Job créé avec succès: {job_id}")

            return job_id

        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de la création du job: {e.stderr}")
            return None

    def monitor_job_progress(self, job_id, api_url="http://localhost:8000"):
        """Surveille la progression du job via GET /api/indexer/jobs/{job_id}"""
        print(f"Surveillance du job {job_id}...")

        start_time = time.time()
        last_update = 0

        while True:
            try:
                result = subprocess.run([
                    'curl', '-s',
                    f'{api_url}/api/indexer/jobs/{job_id}'
                ], capture_output=True, text=True, check=True)

                job_data = json.loads(result.stdout)

                if job_data['status'] in ['completed', 'failed']:
                    elapsed = time.time() - start_time
                    print(f"Job terminé avec statut: {job_data['status']} ({elapsed:.2f}s)")
                    return job_data

                if time.time() - last_update > 5:
                    files_found = job_data.get('files_found', 0)
                    files_indexed = job_data.get('files_indexed', 0)
                    print(f"Progression: {files_indexed}/{files_found} fichiers indexés")
                    last_update = time.time()

                time.sleep(1)

            except subprocess.CalledProcessError as e:
                print(f"Erreur lors de la récupération du statut: {e.stderr}")
                return None

    def run_benchmark(self, config_id, api_url="http://localhost:8000"):
        """Exécute le benchmark complet"""
        print("Début du benchmark d'indexation...")
        self.start_time = time.time()

        # Créer la structure de test
        self.create_test_structure()

        # Lancer le job d'indexation
        job_id = self.run_indexing_job(config_id, api_url)
        if not job_id:
            print("Échec de la création du job d'indexation")
            return False

        # Surveiller la progression
        job_result = self.monitor_job_progress(job_id, api_url)
        if not job_result or job_result['status'] != 'completed':
            print("Le job d'indexation n'a pas abouti")
            return False

        self.end_time = time.time()

        # Calculer les métriques
        indexing_time = self.end_time - self.start_time
        self.metrics['indexing_time_seconds'] = indexing_time

        # Mesurer les ressources système
        resources = self.monitor_system_resources()
        self.metrics['cpu_usage_percent'] = resources['cpu_percent']
        self.metrics['memory_usage_mb'] = resources['memory_mb']

        # Calculer les performances
        if indexing_time > 0:
            self.metrics['files_per_second'] = self.metrics['total_files'] / indexing_time
            self.metrics['mb_per_second'] = self.metrics['total_size_mb'] / indexing_time

        return True

    def generate_report(self, output_file="benchmark_report.json"):
        """Génère un rapport de benchmark"""
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'test_type': 'indexer_load_test',
                'file_count': self.file_count,
                'max_depth': self.max_depth
            },
            'metrics': self.metrics,
            'system_info': {
                'cpu_cores': psutil.cpu_count(),
                'total_memory_gb': psutil.virtual_memory().total / (1024 ** 3)
            }
        }

        # Sauvegarder le rapport
        report_path = Path(output_file)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Rapport de benchmark sauvegardé: {report_path.absolute()}")

        # Afficher un résumé
        print("\n=== Résumé du Benchmark ===")
        print(f"Fichiers indexés: {self.metrics['total_files']}")
        print(f"Taille totale: {self.metrics['total_size_mb']:.2f} MB")
        print(f"Temps d'indexation: {self.metrics['indexing_time_seconds']:.2f} secondes")
        print(f"Vitesse: {self.metrics['files_per_second']:.2f} fichiers/seconde")
        print(f"Débit: {self.metrics['mb_per_second']:.2f} MB/seconde")
        print(f"Utilisation CPU: {self.metrics['cpu_usage_percent']:.1f}%")
        print(f"Utilisation mémoire: {self.metrics['memory_usage_mb']:.2f} MB")

        return report

def main():
    parser = argparse.ArgumentParser(description='Test de charge pour l\'indexeur OpenIndex')
    parser.add_argument('--files', type=int, default=10000, help='Nombre de fichiers à générer')
    parser.add_argument('--depth', type=int, default=5, help='Profondeur maximale des répertoires')
    parser.add_argument('--config', required=True, help='ID de la configuration SMB')
    parser.add_argument('--api-url', default='http://localhost:8000', help='URL de l\'API OpenIndex')
    parser.add_argument('--output', default='docs/benchmarks/indexer_load_test.json', help='Fichier de sortie du rapport')
    parser.add_argument('--path', default='/tmp/openindex_load_test',
                        help='Chemin où générer les fichiers de test (doit correspondre au start_path de la crawl_config)')

    args = parser.parse_args()

    load_test = LoadTestIndexer(
        base_path=args.path,
        file_count=args.files,
        max_depth=args.depth
    )

    # Exécuter le benchmark
    success = load_test.run_benchmark(args.config, args.api_url)

    if success:
        # Générer le rapport
        load_test.generate_report(args.output)
    else:
        print("Le benchmark a échoué")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())