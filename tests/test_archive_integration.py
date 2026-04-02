"""
Tests d'intégration fonctionnels pour T-ARCH-01
Test des scénarios complets de bout en bout
"""

import pytest
import time
import subprocess
import requests
import json
from datetime import datetime
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestEndToEndArchiveWorkflow:
    """Tests d'intégration end-to-end pour le workflow d'archivage."""

    @pytest.fixture(scope="class")
    def api_base_url(self):
        """URL de base de l'API (à adapter selon l'environnement de test)."""
        return os.getenv("TEST_API_URL", "http://localhost:8000")

    @pytest.fixture(scope="class")
    def db_connection(self):
        """Connexion à la base de test."""
        from postgres_adapter import PostgreSQLAdapter
        config = {
            'host': os.getenv('TEST_POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('TEST_POSTGRES_PORT', '5432')),
            'database': os.getenv('TEST_POSTGRES_DB', 'openindex_test'),
            'user': os.getenv('TEST_POSTGRES_USER', 'test_user'),
            'password': os.getenv('TEST_POSTGRES_PASSWORD', 'test_pass')
        }
        adapter = PostgreSQLAdapter(config)
        return adapter

    def test_e2e_create_and_retrieve_job(self, api_base_url, db_connection):
        """Test E2E : Créer un job et le récupérer."""
        # Créer un job
        create_response = requests.post(
            f"{api_base_url}/api/archive/queue",
            json={
                "job_type": "copy",
                "source_path": "\\\\test-server\\share\\test-file.txt",
                "dest_path": "\\\\archive-server\\storage\\test-file.txt",
                "priority": 7
            }
        )
        
        assert create_response.status_code == 200
        job_data = create_response.json()
        job_id = job_data["id"]
        assert job_data["status"] == "pending"
        assert job_data["priority"] == 7
        
        # Récupérer le job
        get_response = requests.get(f"{api_base_url}/api/archive/queue/{job_id}")
        assert get_response.status_code == 200
        
        retrieved_job = get_response.json()
        assert retrieved_job["id"] == job_id
        assert retrieved_job["source_path"] == "\\\\test-server\\share\\test-file.txt"
        
        # Nettoyage
        db_connection.execute_query(
            "DELETE FROM archive_jobs WHERE id = %s",
            (job_id,),
            fetch=False
        )

    def test_e2e_list_jobs_with_pagination(self, api_base_url, db_connection):
        """Test E2E : Créer plusieurs jobs et les lister avec pagination."""
        job_ids = []
        
        # Créer 5 jobs
        for i in range(5):
            response = requests.post(
                f"{api_base_url}/api/archive/queue",
                json={
                    "job_type": "copy",
                    "source_path": f"\\\\server\\share\\file{i}.txt",
                    "dest_path": f"\\\\archive\\storage\\file{i}.txt",
                    "priority": 5
                }
            )
            assert response.status_code == 200
            job_ids.append(response.json()["id"])
        
        # Test pagination limit=2
        list_response = requests.get(f"{api_base_url}/api/archive/queue?limit=2")
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data["jobs"]) == 2
        assert data["total"] >= 5
        
        # Test pagination offset=2
        list_response = requests.get(f"{api_base_url}/api/archive/queue?limit=2&offset=2")
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data["jobs"]) == 2
        
        # Nettoyage
        for job_id in job_ids:
            db_connection.execute_query(
                "DELETE FROM archive_jobs WHERE id = %s",
                (job_id,),
                fetch=False
            )

    def test_e2e_cancel_job(self, api_base_url, db_connection):
        """Test E2E : Créer et annuler un job."""
        # Créer un job
        create_response = requests.post(
            f"{api_base_url}/api/archive/queue",
            json={
                "job_type": "delete",
                "source_path": "\\\\server\\share\\temp.txt",
                "priority": 3
            }
        )
        job_id = create_response.json()["id"]
        
        # Annuler le job
        cancel_response = requests.delete(f"{api_base_url}/api/archive/queue/{job_id}")
        assert cancel_response.status_code == 200
        assert cancel_response.json()["success"] is True
        
        # Vérifier que le statut est cancelled
        get_response = requests.get(f"{api_base_url}/api/archive/queue/{job_id}")
        assert get_response.json()["status"] == "cancelled"
        
        # Nettoyage
        db_connection.execute_query(
            "DELETE FROM archive_jobs WHERE id = %s",
            (job_id,),
            fetch=False
        )

    def test_e2e_retry_failed_job(self, api_base_url, db_connection):
        """Test E2E : Simuler un job échoué et le réessayer."""
        # Créer un job
        create_response = requests.post(
            f"{api_base_url}/api/archive/queue",
            json={
                "job_type": "copy",
                "source_path": "\\\\server\\share\\retry-test.txt",
                "dest_path": "\\\\archive\\storage\\retry-test.txt",
                "priority": 5
            }
        )
        job_id = create_response.json()["id"]
        
        # Simuler un échec en mettant à jour directement en DB
        db_connection.execute_query(
            """
            UPDATE archive_jobs 
            SET status = 'failed', 
                error_message = 'Test failure',
                retry_count = 1
            WHERE id = %s
            """,
            (job_id,),
            fetch=False
        )
        
        # Retry le job
        retry_response = requests.post(f"{api_base_url}/api/archive/queue/{job_id}/retry")
        assert retry_response.status_code == 200
        assert retry_response.json()["success"] is True
        
        # Vérifier que le job est revenu en pending
        get_response = requests.get(f"{api_base_url}/api/archive/queue/{job_id}")
        job_data = get_response.json()
        assert job_data["status"] == "pending"
        assert job_data["retry_count"] == 0
        
        # Nettoyage
        db_connection.execute_query(
            "DELETE FROM archive_jobs WHERE id = %s",
            (job_id,),
            fetch=False
        )

    def test_e2e_job_priority_ordering(self, api_base_url, db_connection):
        """Test E2E : Vérifier que les jobs sont traités par ordre de priorité."""
        # Créer des jobs avec différentes priorités
        priorities = [3, 8, 2, 10, 5]
        job_ids = []
        
        for priority in priorities:
            response = requests.post(
                f"{api_base_url}/api/archive/queue",
                json={
                    "job_type": "copy",
                    "source_path": f"\\\\server\\share\\prio{priority}.txt",
                    "dest_path": f"\\\\archive\\storage\\prio{priority}.txt",
                    "priority": priority
                }
            )
            job_ids.append(response.json()["id"])
        
        # Lister les jobs triés par priorité descendante
        list_response = requests.get(f"{api_base_url}/api/archive/queue?sort=priority&order=desc")
        assert list_response.status_code == 200
        jobs = list_response.json()["jobs"]
        
        # Vérifier l'ordre (du plus haut au plus bas)
        priorities_returned = [job["priority"] for job in jobs[:5]]
        assert priorities_returned == sorted(priorities, reverse=True)
        
        # Nettoyage
        for job_id in job_ids:
            db_connection.execute_query(
                "DELETE FROM archive_jobs WHERE id = %s",
                (job_id,),
                fetch=False
            )

    def test_e2e_filter_jobs_by_status(self, api_base_url, db_connection):
        """Test E2E : Filtrer les jobs par statut."""
        # Créer des jobs
        job_ids = []
        for i in range(3):
            response = requests.post(
                f"{api_base_url}/api/archive/queue",
                json={
                    "job_type": "copy",
                    "source_path": f"\\\\server\\share\\file{i}.txt",
                    "dest_path": f"\\\\archive\\storage\\file{i}.txt",
                    "priority": 5
                }
            )
            job_ids.append(response.json()["id"])
        
        # Marquer un job comme completed
        db_connection.execute_query(
            "UPDATE archive_jobs SET status = 'completed' WHERE id = %s",
            (job_ids[0],),
            fetch=False
        )
        
        # Filtrer par status=pending
        list_response = requests.get(f"{api_base_url}/api/archive/queue?status=pending")
        assert list_response.status_code == 200
        data = list_response.json()
        
        # Tous les jobs non-completed doivent être pending
        for job in data["jobs"]:
            if job["id"] in job_ids:
                assert job["status"] == "pending"
        
        # Nettoyage
        for job_id in job_ids:
            db_connection.execute_query(
                "DELETE FROM archive_jobs WHERE id = %s",
                (job_id,),
                fetch=False
            )


class TestDatabaseOperations:
    """Tests des opérations de base de données pour la queue d'archivage."""

    @pytest.fixture
    def db_adapter(self):
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
        yield adapter
        # Cleanup après les tests
        adapter.execute_query(
            "DELETE FROM archive_jobs WHERE source_path LIKE '\\\\test-%'",
            fetch=False
        )

    def test_database_atomic_job_acquisition(self, db_adapter):
        """Test que l'acquisition de job est atomique (SKIP LOCKED)."""
        # Créer un job
        result = db_adapter.execute_query(
            """
            INSERT INTO archive_jobs (job_type, source_path, dest_path, status, priority)
            VALUES ('copy', '\\\\test-server\\share\\atomic.txt', '\\\\test-archive\\storage\\atomic.txt', 'pending', 5)
            RETURNING id
            """,
            fetch=True
        )
        job_id = result[0][0]
        
        # Utiliser get_next_archive_job (fonction SQL)
        acquired = db_adapter.execute_query(
            "SELECT * FROM get_next_archive_job()",
            fetch=True
        )
        
        # Vérifier que le job a été acquis
        assert acquired is not None
        assert len(acquired) > 0
        
        # Vérifier que le statut est maintenant 'running'
        status_result = db_adapter.execute_query(
            "SELECT status::text FROM archive_jobs WHERE id = %s",
            (job_id,),
            fetch=True
        )
        assert status_result[0][0] == "running"

    def test_database_job_status_transition(self, db_adapter):
        """Test des transitions de statut valides."""
        # Créer un job
        result = db_adapter.execute_query(
            """
            INSERT INTO archive_jobs (job_type, source_path, dest_path, status, priority)
            VALUES ('copy', '\\\\test-server\\share\\transition.txt', '\\\\test-archive\\storage\\transition.txt', 'pending', 5)
            RETURNING id
            """,
            fetch=True
        )
        job_id = result[0][0]
        
        # pending -> running
        db_adapter.execute_query(
            "UPDATE archive_jobs SET status = 'running', started_at = CURRENT_TIMESTAMP WHERE id = %s",
            (job_id,),
            fetch=False
        )
        
        # running -> completed
        db_adapter.execute_query(
            """
            UPDATE archive_jobs 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP, bytes_transferred = 1024
            WHERE id = %s
            """,
            (job_id,),
            fetch=False
        )
        
        # Vérifier le statut final
        final_status = db_adapter.execute_query(
            "SELECT status::text, bytes_transferred FROM archive_jobs WHERE id = %s",
            (job_id,),
            fetch=True
        )
        assert final_status[0][0] == "completed"
        assert final_status[0][1] == 1024

    def test_database_retry_count_increment(self, db_adapter):
        """Test de l'incrémentation du compteur de retry."""
        # Créer un job
        result = db_adapter.execute_query(
            """
            INSERT INTO archive_jobs (job_type, source_path, dest_path, status, priority, retry_count, max_retries)
            VALUES ('copy', '\\\\test-server\\share\\retry.txt', '\\\\test-archive\\storage\\retry.txt', 'failed', 5, 0, 3)
            RETURNING id
            """,
            fetch=True
        )
        job_id = result[0][0]
        
        # Incrémenter retry_count
        for i in range(3):
            db_adapter.execute_query(
                """
                UPDATE archive_jobs 
                SET retry_count = retry_count + 1,
                    status = CASE WHEN retry_count + 1 >= max_retries THEN 'failed' ELSE 'pending' END
                WHERE id = %s
                RETURNING retry_count, max_retries
                """,
                (job_id,),
                fetch=True
            )
        
        # Vérifier que retry_count = 3 et status = failed
        final = db_adapter.execute_query(
            "SELECT retry_count, status::text FROM archive_jobs WHERE id = %s",
            (job_id,),
            fetch=True
        )
        assert final[0][0] == 3
        assert final[0][1] == "failed"

    def test_database_archive_jobs_stats_view(self, db_adapter):
        """Test de la vue archive_jobs_stats."""
        # Créer plusieurs jobs avec différents statuts
        statuses = ['pending', 'pending', 'running', 'completed', 'completed', 'failed']
        for i, status in enumerate(statuses):
            db_adapter.execute_query(
                """
                INSERT INTO archive_jobs (job_type, source_path, dest_path, status, priority, bytes_transferred)
                VALUES ('copy', %s, %s, %s, 5, %s)
                """,
                (f'\\\\test-server\\share\\stats{i}.txt', f'\\\\test-archive\\storage\\stats{i}.txt', 
                 status, 1024 if status == 'completed' else 0),
                fetch=False
            )
        
        # Récupérer les stats
        stats = db_adapter.execute_query(
            "SELECT * FROM archive_jobs_stats ORDER BY status",
            fetch=True
        )
        
        # Convertir en dictionnaire pour faciliter les assertions
        stats_dict = {row[0]: {"count": row[1], "total_bytes": row[2]} for row in stats}
        
        assert stats_dict.get("pending", {}).get("count") == 2
        assert stats_dict.get("running", {}).get("count") == 1
        assert stats_dict.get("completed", {}).get("count") == 2
        assert stats_dict.get("failed", {}).get("count") == 1


class TestConcurrentOperations:
    """Tests des opérations concurrentes."""

    def test_concurrent_job_creation(self, api_base_url, db_connection):
        """Test de création concurrente de jobs."""
        import concurrent.futures
        
        def create_job(i):
            return requests.post(
                f"{api_base_url}/api/archive/queue",
                json={
                    "job_type": "copy",
                    "source_path": f"\\\\server\\share\\concurrent{i}.txt",
                    "dest_path": f"\\\\archive\\storage\\concurrent{i}.txt",
                    "priority": 5
                }
            )
        
        # Créer 10 jobs en parallèle
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_job, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Tous les jobs doivent avoir été créés avec succès
        job_ids = []
        for response in results:
            assert response.status_code == 200
            job_ids.append(response.json()["id"])
        
        # Vérifier que 10 jobs distincts ont été créés
        assert len(set(job_ids)) == 10
        
        # Nettoyage
        for job_id in job_ids:
            db_connection.execute_query(
                "DELETE FROM archive_jobs WHERE id = %s",
                (job_id,),
                fetch=False
            )


class TestErrorScenarios:
    """Tests des scénarios d'erreur."""

    def test_create_job_invalid_json(self, api_base_url):
        """Test d'erreur avec JSON invalide."""
        response = requests.post(
            f"{api_base_url}/api/archive/queue",
            data="invalid json {",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_create_job_missing_required_fields(self, api_base_url):
        """Test d'erreur avec champs requis manquants."""
        response = requests.post(
            f"{api_base_url}/api/archive/queue",
            json={
                # source_path manquant
                "job_type": "copy",
                "dest_path": "\\\\archive\\storage\\file.txt"
            }
        )
        assert response.status_code == 422

    def test_get_nonexistent_job(self, api_base_url):
        """Test récupération d'un job inexistant."""
        response = requests.get(f"{api_base_url}/api/archive/queue/nonexistent-job-id-12345")
        assert response.status_code == 404

    def test_cancel_nonexistent_job(self, api_base_url):
        """Test annulation d'un job inexistant."""
        response = requests.delete(f"{api_base_url}/api/archive/queue/nonexistent-job-id-12345")
        assert response.status_code == 404

    def test_retry_nonexistent_job(self, api_base_url):
        """Test retry d'un job inexistant."""
        response = requests.post(f"{api_base_url}/api/archive/queue/nonexistent-job-id-12345/retry")
        assert response.status_code == 404

    def test_invalid_job_type(self, api_base_url):
        """Test avec type de job invalide."""
        response = requests.post(
            f"{api_base_url}/api/archive/queue",
            json={
                "job_type": "invalid_type",
                "source_path": "\\\\server\\share\\file.txt",
                "dest_path": "\\\\archive\\storage\\file.txt"
            }
        )
        assert response.status_code == 422

    def test_invalid_uuid_format(self, api_base_url):
        """Test avec format d'ID invalide."""
        response = requests.get(f"{api_base_url}/api/archive/queue/not-a-valid-uuid")
        # Selon l'implémentation, peut retourner 404 ou 400
        assert response.status_code in [400, 404, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
