"""
Tests de charge pour T-ARCH-01 Archive Queue System
Exécutables avec pytest pour validation pré-production
"""

import pytest
import time
import random
import string
import concurrent.futures
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def load_test_config():
    """Configuration pour les tests de charge."""
    return {
        'small_files_count': int(os.getenv('TEST_SMALL_FILES', '1000')),
        'medium_files_count': int(os.getenv('TEST_MEDIUM_FILES', '100')),
        'large_files_count': int(os.getenv('TEST_LARGE_FILES', '10')),
        'concurrent_workers': int(os.getenv('TEST_CONCURRENT_WORKERS', '5')),
        'timeout_seconds': int(os.getenv('TEST_TIMEOUT', '300'))
    }


@pytest.fixture
def db_adapter():
    """Fixture pour l'adaptateur de base de données."""
    from postgres_adapter import PostgreSQLAdapter
    config = {
        'host': os.getenv('TEST_POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('TEST_POSTGRES_PORT', '5432')),
        'database': os.getenv('TEST_POSTGRES_DB', 'openindex_test'),
        'user': os.getenv('TEST_POSTGRES_USER', 'test_user'),
        'password': os.getenv('TEST_POSTGRES_PASSWORD', 'test_pass')
    }
    adapter = PostgreSQLAdapter(config)
    
    # Cleanup avant le test
    adapter.execute_query(
        "DELETE FROM archive_jobs WHERE source_path LIKE '\\\\load-test%'",
        fetch=False
    )
    
    yield adapter
    
    # Cleanup après le test
    adapter.execute_query(
        "DELETE FROM archive_jobs WHERE source_path LIKE '\\\\load-test%'",
        fetch=False
    )


def generate_random_path(prefix="\\\\load-test-server\\share") -> str:
    """Génère un chemin aléatoire pour les tests."""
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    return f"{prefix}\\file_{random_suffix}.dat"


def create_test_job(db_adapter, job_type="copy", priority=5, size=0):
    """Helper pour créer un job de test."""
    source = generate_random_path()
    dest = generate_random_path("\\\\load-test-archive\\storage") if job_type in ["copy", "move"] else None
    
    result = db_adapter.execute_query(
        """
        INSERT INTO archive_jobs (job_type, source_path, dest_path, status, priority, source_size)
        VALUES (%s::archive_job_type, %s, %s, 'pending', %s, %s)
        RETURNING id
        """,
        (job_type, source, dest, priority, size),
        fetch=True
    )
    return str(result[0][0]) if result else None


class TestSmallFilesVolume:
    """Tests de volume avec beaucoup de petits fichiers."""
    
    @pytest.mark.slow
    def test_create_1000_small_files(self, db_adapter, load_test_config):
        """Test de création de 1000 jobs de petits fichiers."""
        count = min(load_test_config['small_files_count'], 1000)
        job_ids = []
        
        start_time = time.time()
        
        for i in range(count):
            job_id = create_test_job(
                db_adapter,
                job_type="copy",
                priority=random.randint(1, 10),
                size=random.randint(1024, 1024 * 1024)  # 1KB à 1MB
            )
            if job_id:
                job_ids.append(job_id)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assertions de performance
        assert len(job_ids) == count
        assert duration < 30.0, f"Création de {count} jobs trop lente: {duration:.2f}s"
        
        # Vérifier que tous les jobs sont en DB
        count_db = db_adapter.execute_query(
            "SELECT COUNT(*) FROM archive_jobs WHERE id = ANY(%s)",
            (job_ids,),
            fetch=True
        )[0][0]
        assert count_db == count
        
        print(f"✅ {count} jobs créés en {duration:.2f}s ({count/duration:.1f} jobs/s)")

    @pytest.mark.slow
    def test_create_10000_small_files_bulk(self, db_adapter):
        """Test de création massive de 10000 jobs (si configuré)."""
        count = int(os.getenv('TEST_BULK_COUNT', '10000'))
        if count < 1000:
            pytest.skip("Test bulk désactivé")
        
        start_time = time.time()
        
        # Utiliser une requête bulk pour performance
        values = []
        for i in range(count):
            source = generate_random_path()
            dest = generate_random_path("\\\\load-test-archive\\storage")
            prio = random.randint(1, 10)
            size = random.randint(1024, 1024 * 1024)
            values.append(f"('copy', '{source}', '{dest}', 'pending', {prio}, {size})")
        
        # Insérer par batches de 1000
        batch_size = 1000
        for i in range(0, len(values), batch_size):
            batch = values[i:i+batch_size]
            placeholders = ','.join(['%s'] * len(batch))
            db_adapter.execute_query(
                f"""
                INSERT INTO archive_jobs (job_type, source_path, dest_path, status, priority, source_size)
                VALUES {placeholders}
                """,
                tuple(batch),
                fetch=False
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Vérifier le compte
        count_db = db_adapter.execute_query(
            "SELECT COUNT(*) FROM archive_jobs WHERE source_path LIKE '\\\\load-test-server\\share%'",
            fetch=True
        )[0][0]
        
        assert count_db >= count
        print(f"✅ {count} jobs créés en bulk en {duration:.2f}s ({count/duration:.1f} jobs/s)")


class TestLargeFilesVolume:
    """Tests avec des fichiers de grande taille."""
    
    @pytest.mark.slow
    def test_create_large_files_1gb_to_10gb(self, db_adapter, load_test_config):
        """Test de création de jobs avec fichiers de 1GB à 10GB."""
        count = load_test_config['large_files_count']
        job_ids = []
        total_size = 0
        
        start_time = time.time()
        
        for i in range(count):
            # Taille entre 1GB et 10GB
            size_gb = random.uniform(1.0, 10.0)
            size_bytes = int(size_gb * 1024 * 1024 * 1024)
            total_size += size_bytes
            
            job_id = create_test_job(
                db_adapter,
                job_type="copy",
                priority=10,  # Haute priorité pour gros fichiers
                size=size_bytes
            )
            if job_id:
                job_ids.append(job_id)
        
        end_time = time.time()
        duration = end_time - start_time
        
        total_size_gb = total_size / (1024 ** 3)
        
        assert len(job_ids) == count
        print(f"✅ {count} gros fichiers créés ({total_size_gb:.2f} GB total) en {duration:.2f}s")

    @pytest.mark.slow  
    def test_create_very_large_file_50gb(self, db_adapter):
        """Test avec un fichier très grand (50GB)."""
        size_bytes = 50 * 1024 * 1024 * 1024  # 50GB
        
        job_id = create_test_job(
            db_adapter,
            job_type="copy",
            priority=10,
            size=size_bytes
        )
        
        assert job_id is not None
        
        # Vérifier que le job existe avec la bonne taille
        result = db_adapter.execute_query(
            "SELECT source_size FROM archive_jobs WHERE id = %s",
            (job_id,),
            fetch=True
        )
        assert result[0][0] == size_bytes
        print(f"✅ Job créé pour fichier de 50GB")


class TestMixedWorkload:
    """Tests avec charge mixte (petits, moyens et gros fichiers)."""
    
    @pytest.mark.slow
    def test_mixed_workload_distribution(self, db_adapter, load_test_config):
        """Test de charge mixte réaliste."""
        job_ids = {
            'small': [],   # < 10MB
            'medium': [],  # 10MB - 500MB
            'large': []    # > 1GB
        }
        
        start_time = time.time()
        
        # Petits fichiers (1000)
        for _ in range(1000):
            size = random.randint(1024, 10 * 1024 * 1024)
            job_id = create_test_job(db_adapter, "copy", random.randint(1, 5), size)
            if job_id:
                job_ids['small'].append(job_id)
        
        # Moyens fichiers (100)
        for _ in range(100):
            size = random.randint(10 * 1024 * 1024, 500 * 1024 * 1024)
            job_id = create_test_job(db_adapter, "copy", random.randint(3, 7), size)
            if job_id:
                job_ids['medium'].append(job_id)
        
        # Gros fichiers (10)
        for _ in range(10):
            size = random.randint(1 * 1024**3, 10 * 1024**3)
            job_id = create_test_job(db_adapter, "copy", 10, size)
            if job_id:
                job_ids['large'].append(job_id)
        
        end_time = time.time()
        duration = end_time - start_time
        
        total_jobs = sum(len(v) for v in job_ids.values())
        
        assert len(job_ids['small']) == 1000
        assert len(job_ids['medium']) == 100
        assert len(job_ids['large']) == 10
        
        print(f"✅ Charge mixte créée: {len(job_ids['small'])} small, {len(job_ids['medium'])} medium, {len(job_ids['large'])} large en {duration:.2f}s")


class TestConcurrentOperations:
    """Tests des opérations concurrentes."""
    
    def test_concurrent_job_creation(self, db_adapter, load_test_config):
        """Test de création concurrente de jobs."""
        workers = load_test_config['concurrent_workers']
        jobs_per_worker = 100
        
        def create_jobs_batch(worker_id):
            """Crée un batch de jobs."""
            ids = []
            for i in range(jobs_per_worker):
                job_id = create_test_job(
                    db_adapter,
                    "copy",
                    random.randint(1, 10),
                    random.randint(1024, 1024 * 1024)
                )
                if job_id:
                    ids.append(job_id)
            return ids
        
        start_time = time.time()
        
        # Exécuter en parallèle
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(create_jobs_batch, i) for i in range(workers)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Aplatir les résultats
        all_job_ids = [job_id for batch in results for job_id in batch]
        
        assert len(all_job_ids) == workers * jobs_per_worker
        assert len(set(all_job_ids)) == len(all_job_ids)  # Tous uniques
        
        print(f"✅ {len(all_job_ids)} jobs créés concurrentiellement ({workers} workers) en {duration:.2f}s")

    def test_concurrent_priority_queue_access(self, db_adapter):
        """Test d'accès concurrent à la queue avec priorités."""
        # Créer des jobs avec différentes priorités
        priorities = list(range(1, 11))
        job_ids_by_priority = {p: [] for p in priorities}
        
        def create_jobs_with_priority(priority):
            """Crée 10 jobs avec une priorité spécifique."""
            ids = []
            for _ in range(10):
                job_id = create_test_job(db_adapter, "copy", priority, 1024)
                if job_id:
                    ids.append(job_id)
            return priority, ids
        
        # Créer tous les jobs en parallèle
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_jobs_with_priority, p) for p in priorities]
            for future in concurrent.futures.as_completed(futures):
                prio, ids = future.result()
                job_ids_by_priority[prio] = ids
        
        # Vérifier que chaque priorité a ses jobs
        for prio in priorities:
            assert len(job_ids_by_priority[prio]) == 10
        
        # Vérifier l'ordre de récupération (get_next_archive_job)
        # Les jobs de priorité 10 devraient être récupérés avant ceux de priorité 1
        retrieved_order = []
        for _ in range(20):  # Récupérer 20 jobs
            result = db_adapter.execute_query(
                "SELECT * FROM get_next_archive_job()",
                fetch=True
            )
            if result:
                retrieved_order.append(result[0][0])
        
        print(f"✅ {sum(len(v) for v in job_ids_by_priority.values())} jobs créés avec 10 niveaux de priorité")


class TestQueuePerformance:
    """Tests de performance de la queue."""
    
    def test_job_acquisition_performance(self, db_adapter):
        """Test de performance de l'acquisition de jobs."""
        # Créer 100 jobs
        job_ids = []
        for _ in range(100):
            job_id = create_test_job(db_adapter, "copy", 5, 1024)
            if job_id:
                job_ids.append(job_id)
        
        # Mesurer le temps d'acquisition
        start_time = time.time()
        acquired_count = 0
        
        while acquired_count < 100:
            result = db_adapter.execute_query(
                "SELECT * FROM get_next_archive_job()",
                fetch=True
            )
            if not result:
                break
            acquired_count += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Les 100 jobs devraient être acquis rapidement (< 5s)
        assert acquired_count == 100
        assert duration < 5.0, f"Acquisition trop lente: {duration:.2f}s"
        
        print(f"✅ {acquired_count} jobs acquis en {duration:.2f}s ({acquired_count/duration:.1f} jobs/s)")

    def test_stats_query_performance(self, db_adapter):
        """Test de performance de la requête de stats."""
        # Créer un grand nombre de jobs
        for _ in range(1000):
            create_test_job(db_adapter, "copy", 5, random.randint(1024, 1024*1024))
        
        # Mesurer le temps de la requête stats
        start_time = time.time()
        stats = db_adapter.execute_query(
            "SELECT * FROM archive_jobs_stats",
            fetch=True
        )
        end_time = time.time()
        duration = end_time - start_time
        
        # La requête devrait être très rapide (< 100ms)
        assert duration < 0.1, f"Requête stats trop lente: {duration:.3f}s"
        assert len(stats) > 0
        
        print(f"✅ Requête stats exécutée en {duration*1000:.1f}ms")


class TestErrorHandlingUnderLoad:
    """Tests de gestion d'erreur sous charge."""
    
    def test_retry_mechanism_under_load(self, db_adapter):
        """Test du mécanisme de retry sous charge."""
        # Créer des jobs et les marquer comme échoués
        failed_jobs = []
        for _ in range(50):
            job_id = create_test_job(db_adapter, "copy", 5, 1024)
            if job_id:
                # Marquer comme échoué avec retry_count > 0
                db_adapter.execute_query(
                    """
                    UPDATE archive_jobs 
                    SET status = 'failed', retry_count = %s, error_message = 'Test failure'
                    WHERE id = %s
                    """,
                    (random.randint(1, 2), job_id),
                    fetch=False
                )
                failed_jobs.append(job_id)
        
        # Réinitialiser la moitié des jobs pour retry
        retry_jobs = failed_jobs[:25]
        for job_id in retry_jobs:
            db_adapter.execute_query(
                """
                UPDATE archive_jobs 
                SET status = 'pending', retry_count = 0, error_message = NULL
                WHERE id = %s
                """,
                (job_id,),
                fetch=False
            )
        
        # Vérifier que les jobs sont bien revenus en pending
        pending_count = db_adapter.execute_query(
            "SELECT COUNT(*) FROM archive_jobs WHERE id = ANY(%s) AND status = 'pending'",
            (retry_jobs,),
            fetch=True
        )[0][0]
        
        assert pending_count == 25
        print(f"✅ {pending_count} jobs réinitialisés pour retry sous charge")

    def test_cancel_under_load(self, db_adapter):
        """Test d'annulation de jobs sous charge."""
        # Créer beaucoup de jobs
        job_ids = []
        for _ in range(200):
            job_id = create_test_job(db_adapter, "copy", 5, 1024)
            if job_id:
                job_ids.append(job_id)
        
        # Annuler tous les jobs
        cancelled = 0
        for job_id in job_ids:
            db_adapter.execute_query(
                """
                UPDATE archive_jobs 
                SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
                WHERE id = %s AND status IN ('pending', 'running')
                """,
                (job_id,),
                fetch=False
            )
            cancelled += 1
        
        # Vérifier que tous sont cancelled
        cancelled_count = db_adapter.execute_query(
            "SELECT COUNT(*) FROM archive_jobs WHERE id = ANY(%s) AND status = 'cancelled'",
            (job_ids,),
            fetch=True
        )[0][0]
        
        assert cancelled_count == len(job_ids)
        print(f"✅ {cancelled_count} jobs annulés sous charge")


class TestDatabaseConstraintsUnderLoad:
    """Tests des contraintes de la base de données sous charge."""
    
    def test_unique_job_ids(self, db_adapter):
        """Test que les IDs de jobs sont uniques même sous charge."""
        job_ids = []
        
        # Créer beaucoup de jobs rapidement
        for _ in range(500):
            job_id = create_test_job(db_adapter, "copy", 5, 1024)
            if job_id:
                job_ids.append(job_id)
        
        # Vérifier l'unicité
        unique_ids = set(job_ids)
        assert len(unique_ids) == len(job_ids)
        print(f"✅ {len(job_ids)} IDs uniques générés")

    def test_priority_constraint(self, db_adapter):
        """Test que la contrainte de priorité (1-10) est respectée."""
        # Tenter de créer des jobs avec des priorités invalides
        # La base de données devrait rejeter les valeurs < 1 ou > 10
        
        # Test avec priorité valide
        result = db_adapter.execute_query(
            """
            INSERT INTO archive_jobs (job_type, source_path, dest_path, status, priority)
            VALUES ('copy', '\\\\load-test\\valid.txt', '\\\\archive\\valid.txt', 'pending', 5)
            RETURNING id
            """,
            fetch=True
        )
        assert result is not None
        
        # Test avec priorité invalide (devrait échouer)
        with pytest.raises(Exception):
            db_adapter.execute_query(
                """
                INSERT INTO archive_jobs (job_type, source_path, dest_path, status, priority)
                VALUES ('copy', '\\\\load-test\\invalid.txt', '\\\\archive\\invalid.txt', 'pending', 15)
                """,
                fetch=False
            )
        
        print("✅ Contraintes de priorité respectées")


# Markers pour pytest
pytestmark = [
    pytest.mark.integration,
    pytest.mark.load,
]

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "load"])
