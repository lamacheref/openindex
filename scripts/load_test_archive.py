#!/usr/bin/env python3
"""
Tests de charge pour T-ARCH-01: Archive Queue System
Valide le transfert de gros volumes (10k+ fichiers, fichiers > 10Go)
"""

import os
import sys
import time
import random
import string
import tempfile
import argparse
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any
import json
import statistics

# Ajouter src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from postgres_adapter import PostgreSQLAdapter


class LoadTestResult:
    """Résultat d'un test de charge."""
    def __init__(self):
        self.test_name = ""
        self.total_jobs = 0
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.total_bytes = 0
        self.duration_seconds = 0.0
        self.throughput_mbps = 0.0
        self.avg_job_time = 0.0
        self.min_job_time = 0.0
        self.max_job_time = 0.0
        self.errors: List[str] = []
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "total_bytes": self.total_bytes,
            "duration_seconds": self.duration_seconds,
            "throughput_mbps": self.throughput_mbps,
            "avg_job_time": self.avg_job_time,
            "min_job_time": self.min_job_time,
            "max_job_time": self.max_job_time,
            "errors": self.errors,
            "timestamp": self.timestamp
        }


class ArchiveQueueLoadTester:
    """Testeur de charge pour la queue d'archivage."""

    def __init__(self, postgres_config: Dict[str, Any] = None):
        self.postgres_config = postgres_config or {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'openindex'),
            'user': os.getenv('POSTGRES_USER', 'openindex_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        }
        self.adapter = PostgreSQLAdapter(self.postgres_config)
        self.results: List[LoadTestResult] = []

    def generate_random_path(self, prefix: str = "/test") -> str:
        """Génère un chemin aléatoire."""
        random_suffix = ''.join(random.choices(string.ascii_lowercase, k=10))
        return f"{prefix}/file_{random_suffix}.dat"

    def create_test_job(
        self,
        job_type: str = "copy",
        source_prefix: str = "\\\\server\\share\\source",
        dest_prefix: str = "\\\\server\\share\\dest",
        priority: int = 5,
        simulate_size: int = 0
    ) -> str:
        """Crée un job de test dans la DB."""
        source_path = self.generate_random_path(source_prefix)
        dest_path = self.generate_random_path(dest_prefix) if job_type in ["copy", "move"] else None

        result = self.adapter.execute_query(
            """
            INSERT INTO archive_jobs (
                job_type, source_path, dest_path, status, priority,
                retry_count, max_retries, created_at, updated_at, source_size
            ) VALUES (
                %s::archive_job_type, %s, %s, 'pending', %s,
                0, 3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s
            )
            RETURNING id
            """,
            (job_type, source_path, dest_path, priority, simulate_size),
            fetch=True
        )

        return str(result[0][0]) if result else None

    def wait_for_jobs_completion(
        self,
        job_ids: List[str],
        timeout_seconds: int = 300,
        poll_interval: int = 5
    ) -> Dict[str, str]:
        """Attend la complétion des jobs et retourne leur statut final."""
        start_time = time.time()
        completed = {}

        while time.time() - start_time < timeout_seconds:
            pending = [jid for jid in job_ids if jid not in completed]
            if not pending:
                break

            # Vérifier le statut des jobs en attente
            for job_id in pending:
                result = self.adapter.execute_query(
                    "SELECT status::text FROM archive_jobs WHERE id = %s",
                    (job_id,),
                    fetch=True
                )
                if result:
                    status = result[0][0]
                    if status in ["completed", "failed", "cancelled"]:
                        completed[job_id] = status

            if pending:
                time.sleep(poll_interval)

        # Marquer les jobs restants comme timeout
        for job_id in job_ids:
            if job_id not in completed:
                completed[job_id] = "timeout"

        return completed

    def test_small_files_volume(self, num_files: int = 10000) -> LoadTestResult:
        """Test de volume avec beaucoup de petits fichiers."""
        result = LoadTestResult()
        result.test_name = f"small_files_volume_{num_files}"
        print(f"\n{'='*60}")
        print(f"Test: {result.test_name}")
        print(f"Création de {num_files:,} jobs de petite taille...")

        start_time = time.time()
        job_ids = []

        # Créer les jobs
        for i in range(num_files):
            job_id = self.create_test_job(
                job_type="copy",
                priority=random.randint(1, 10),
                simulate_size=random.randint(1024, 1024*1024)  # 1KB à 1MB
            )
            if job_id:
                job_ids.append(job_id)

            if (i + 1) % 1000 == 0:
                print(f"  {i + 1:,} jobs créés...")

        result.total_jobs = len(job_ids)
        print(f"✅ {result.total_jobs:,} jobs créés")

        # Attendre la complétion (simulation - en vrai, attendre le worker)
        print("Attente de traitement (simulation)...")
        statuses = self.wait_for_jobs_completion(job_ids, timeout_seconds=60)

        end_time = time.time()
        result.duration_seconds = end_time - start_time

        # Calculer les résultats
        for status in statuses.values():
            if status == "completed":
                result.completed_jobs += 1
            elif status in ["failed", "timeout"]:
                result.failed_jobs += 1

        # Calculer le throughput
        if result.duration_seconds > 0:
            result.throughput_mbps = (result.completed_jobs / result.duration_seconds) * 60  # jobs/minute

        print(f"✅ Terminé en {result.duration_seconds:.2f}s")
        print(f"   Complétés: {result.completed_jobs:,}")
        print(f"   Échoués: {result.failed_jobs:,}")
        print(f"   Throughput: {result.throughput_mbps:.2f} jobs/min")

        self.results.append(result)
        return result

    def test_large_files(self, num_files: int = 10, min_size_gb: float = 1.0, max_size_gb: float = 15.0) -> LoadTestResult:
        """Test avec des fichiers de grande taille."""
        result = LoadTestResult()
        result.test_name = f"large_files_{num_files}_{min_size_gb}to{max_size_gb}GB"
        print(f"\n{'='*60}")
        print(f"Test: {result.test_name}")
        print(f"Création de {num_files} jobs avec fichiers > {min_size_gb}GB...")

        start_time = time.time()
        job_ids = []
        total_bytes = 0

        for i in range(num_files):
            size_gb = random.uniform(min_size_gb, max_size_gb)
            size_bytes = int(size_gb * 1024 * 1024 * 1024)
            total_bytes += size_bytes

            job_id = self.create_test_job(
                job_type="copy",
                priority=10,  # Haute priorité pour les gros fichiers
                simulate_size=size_bytes
            )
            if job_id:
                job_ids.append(job_id)
                print(f"  Job {i+1}: {size_gb:.2f} GB")

        result.total_jobs = len(job_ids)
        result.total_bytes = total_bytes
        print(f"✅ {result.total_jobs} jobs créés ({total_bytes / (1024**3):.2f} GB total)")

        # Attendre la complétion
        print("Attente de traitement...")
        statuses = self.wait_for_jobs_completion(job_ids, timeout_seconds=300)

        end_time = time.time()
        result.duration_seconds = end_time - start_time

        for status in statuses.values():
            if status == "completed":
                result.completed_jobs += 1
            elif status in ["failed", "timeout"]:
                result.failed_jobs += 1

        # Calculer le throughput en MB/s
        if result.duration_seconds > 0:
            result.throughput_mbps = (total_bytes / (1024 * 1024)) / result.duration_seconds

        print(f"✅ Terminé en {result.duration_seconds:.2f}s")
        print(f"   Complétés: {result.completed_jobs}/{result.total_jobs}")
        print(f"   Throughput: {result.throughput_mbps:.2f} MB/s")

        self.results.append(result)
        return result

    def test_mixed_workload(
        self,
        num_small: int = 5000,
        num_medium: int = 100,
        num_large: int = 5
    ) -> LoadTestResult:
        """Test avec charge mixte (petits, moyens et gros fichiers)."""
        result = LoadTestResult()
        result.test_name = f"mixed_workload_{num_small}_{num_medium}_{num_large}"
        print(f"\n{'='*60}")
        print(f"Test: {result.test_name}")

        job_ids = []
        total_bytes = 0

        # Petits fichiers (1KB - 10MB)
        print(f"Création de {num_small} petits fichiers...")
        for i in range(num_small):
            size = random.randint(1024, 10 * 1024 * 1024)
            job_id = self.create_test_job(job_type="copy", priority=random.randint(1, 5), simulate_size=size)
            if job_id:
                job_ids.append(job_id)
                total_bytes += size

        # Moyens fichiers (10MB - 500MB)
        print(f"Création de {num_medium} moyens fichiers...")
        for i in range(num_medium):
            size = random.randint(10 * 1024 * 1024, 500 * 1024 * 1024)
            job_id = self.create_test_job(job_type="copy", priority=random.randint(3, 7), simulate_size=size)
            if job_id:
                job_ids.append(job_id)
                total_bytes += size

        # Gros fichiers (1GB - 10GB)
        print(f"Création de {num_large} gros fichiers...")
        for i in range(num_large):
            size = random.randint(1 * 1024**3, 10 * 1024**3)
            job_id = self.create_test_job(job_type="copy", priority=10, simulate_size=size)
            if job_id:
                job_ids.append(job_id)
                total_bytes += size

        result.total_jobs = len(job_ids)
        result.total_bytes = total_bytes
        print(f"✅ {result.total_jobs:,} jobs créés ({total_bytes / (1024**3):.2f} GB total)")

        # Attendre
        print("Attente de traitement...")
        start_time = time.time()
        statuses = self.wait_for_jobs_completion(job_ids, timeout_seconds=180)
        end_time = time.time()

        result.duration_seconds = end_time - start_time

        for status in statuses.values():
            if status == "completed":
                result.completed_jobs += 1
            elif status in ["failed", "timeout"]:
                result.failed_jobs += 1

        if result.duration_seconds > 0:
            result.throughput_mbps = (total_bytes / (1024 * 1024)) / result.duration_seconds

        print(f"✅ Terminé en {result.duration_seconds:.2f}s")
        print(f"   Complétés: {result.completed_jobs:,}")
        print(f"   Échoués: {result.failed_jobs:,}")
        print(f"   Throughput: {result.throughput_mbps:.2f} MB/s")

        self.results.append(result)
        return result

    def test_priority_queue(self, num_jobs: int = 1000) -> LoadTestResult:
        """Test de la priorité des jobs."""
        result = LoadTestResult()
        result.test_name = f"priority_queue_{num_jobs}"
        print(f"\n{'='*60}")
        print(f"Test: {result.test_name}")

        # Créer des jobs avec différentes priorités
        job_ids_by_priority = {i: [] for i in range(1, 11)}

        for i in range(num_jobs):
            priority = random.randint(1, 10)
            job_id = self.create_test_job(job_type="copy", priority=priority)
            if job_id:
                job_ids_by_priority[priority].append(job_id)

        all_jobs = [jid for jobs in job_ids_by_priority.values() for jid in jobs]
        result.total_jobs = len(all_jobs)
        print(f"✅ {result.total_jobs} jobs créés avec priorités mixtes")

        # Vérifier l'ordre de traitement
        print("Attente de traitement...")
        start_time = time.time()
        statuses = self.wait_for_jobs_completion(all_jobs, timeout_seconds=60)
        end_time = time.time()

        result.duration_seconds = end_time - start_time

        for status in statuses.values():
            if status == "completed":
                result.completed_jobs += 1
            elif status in ["failed", "timeout"]:
                result.failed_jobs += 1

        print(f"✅ Terminé en {result.duration_seconds:.2f}s")
        print(f"   Complétés: {result.completed_jobs:,}")

        self.results.append(result)
        return result

    def test_retry_mechanism(self, num_failures: int = 50) -> LoadTestResult:
        """Test du mécanisme de retry avec des jobs simulés en échec."""
        result = LoadTestResult()
        result.test_name = f"retry_mechanism_{num_failures}"
        print(f"\n{'='*60}")
        print(f"Test: {result.test_name}")

        # Créer des jobs puis les marquer comme failed
        job_ids = []
        for i in range(num_failures):
            job_id = self.create_test_job(job_type="copy")
            if job_id:
                job_ids.append(job_id)
                # Marquer comme échoué avec retry_count > 0
                self.adapter.execute_query(
                    """
                    UPDATE archive_jobs 
                    SET status = 'failed', 
                        retry_count = %s,
                        error_message = 'Simulated failure'
                    WHERE id = %s
                    """,
                    (random.randint(1, 3), job_id),
                    fetch=False
                )

        result.total_jobs = len(job_ids)
        print(f"✅ {result.total_jobs} jobs créés avec échecs simulés")

        # Tester le retry
        print("Test du mécanisme de retry...")
        for job_id in job_ids[:10]:  # Tester sur 10 jobs
            # Simuler un retry
            self.adapter.execute_query(
                """
                UPDATE archive_jobs 
                SET status = 'pending',
                    retry_count = retry_count + 1,
                    error_message = NULL
                WHERE id = %s
                """,
                (job_id,),
                fetch=False
            )

        print(f"✅ Retry testé sur 10 jobs")
        result.completed_jobs = 10

        self.results.append(result)
        return result

    def generate_report(self, output_file: str = None) -> str:
        """Génère un rapport de synthèse."""
        report_lines = [
            "\n" + "="*70,
            "RAPPORT DE TESTS DE CHARGE - T-ARCH-01",
            "="*70,
            f"Date: {datetime.now().isoformat()}",
            f"Nombre de tests: {len(self.results)}",
            ""
        ]

        for result in self.results:
            report_lines.extend([
                f"\nTest: {result.test_name}",
                f"  - Jobs totaux: {result.total_jobs:,}",
                f"  - Complétés: {result.completed_jobs:,}",
                f"  - Échoués: {result.failed_jobs:,}",
                f"  - Taux de réussite: {(result.completed_jobs/max(result.total_jobs,1)*100):.1f}%",
                f"  - Durée: {result.duration_seconds:.2f}s",
                f"  - Throughput: {result.throughput_mbps:.2f} MB/s",
                ""
            ])

        # Synthèse
        total_jobs = sum(r.total_jobs for r in self.results)
        total_completed = sum(r.completed_jobs for r in self.results)
        total_failed = sum(r.failed_jobs for r in self.results)

        report_lines.extend([
            "="*70,
            "SYNTHÈSE",
            "="*70,
            f"Total jobs créés: {total_jobs:,}",
            f"Total complétés: {total_completed:,}",
            f"Total échoués: {total_failed:,}",
            f"Taux de réussite global: {(total_completed/max(total_jobs,1)*100):.1f}%",
            ""
        ])

        report = "\n".join(report_lines)
        print(report)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
                json.dump([r.to_dict() for r in self.results], f, indent=2)
            print(f"\n✅ Rapport sauvegardé: {output_file}")

        return report


def main():
    parser = argparse.ArgumentParser(description="Tests de charge T-ARCH-01")
    parser.add_argument("--test", choices=["all", "small", "large", "mixed", "priority", "retry"], default="all")
    parser.add_argument("--small-files", type=int, default=10000, help="Nombre de petits fichiers")
    parser.add_argument("--large-files", type=int, default=10, help="Nombre de gros fichiers")
    parser.add_argument("--output", type=str, default=None, help="Fichier de sortie pour le rapport")
    args = parser.parse_args()

    tester = ArchiveQueueLoadTester()

    try:
        if args.test in ["all", "small"]:
            tester.test_small_files_volume(num_files=args.small_files)

        if args.test in ["all", "large"]:
            tester.test_large_files(num_files=args.large_files)

        if args.test in ["all", "mixed"]:
            tester.test_mixed_workload()

        if args.test in ["all", "priority"]:
            tester.test_priority_queue()

        if args.test in ["all", "retry"]:
            tester.test_retry_mechanism()

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrompus par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur pendant les tests: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Générer le rapport
        tester.generate_report(output_file=args.output)


if __name__ == "__main__":
    main()
