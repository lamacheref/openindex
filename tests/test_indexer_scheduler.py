"""
Tests unitaires pour le Scheduler d'indexation (T-INDEX-01)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Ajout du chemin pour les imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.src.workers.indexer_scheduler import (
    IndexerScheduler,
    IndexerScheduleConfig,
    get_scheduler,
    start_scheduler,
    stop_scheduler
)


class TestIndexerScheduleConfig:
    """Tests du modèle IndexerScheduleConfig."""

    def test_schedule_config_creation(self):
        """Vérifie la création d'une config de schedule."""
        now = datetime.now(timezone.utc)
        config = IndexerScheduleConfig(
            id="schedule-1",
            name="Indexation nocturne",
            description="Tous les jours à 22h",
            cron_expression="0 22 * * *",
            timezone="Europe/Paris",
            is_active=True,
            config_id="config-1",
            priority=5,
            next_run_at=now,
            last_run_at=None,
            run_count=0
        )
        assert config.id == "schedule-1"
        assert config.name == "Indexation nocturne"
        assert config.cron_expression == "0 22 * * *"
        assert config.is_active is True
        assert config.run_count == 0


class TestIndexerScheduler:
    """Tests du scheduler d'indexation."""

    @pytest.fixture
    def scheduler(self):
        """Fixture fournissant un scheduler arrêté."""
        s = IndexerScheduler(poll_interval=60)
        yield s
        if s._running:
            s.stop()

    def test_scheduler_initialization(self, scheduler):
        """Vérifie l'initialisation du scheduler."""
        assert scheduler.poll_interval == 60
        assert scheduler._running is False
        assert scheduler._stats["checks"] == 0
        assert scheduler._stats["jobs_created"] == 0

    def test_scheduler_start_stop(self, scheduler):
        """Vérifie le démarrage et l'arrêt."""
        assert scheduler._running is False
        
        scheduler.start()
        assert scheduler._running is True
        assert scheduler._thread is not None
        assert scheduler._thread.is_alive()
        
        scheduler.stop()
        assert scheduler._running is False

    def test_scheduler_double_start(self, scheduler):
        """Vérifie qu'un double démarrage est ignoré."""
        scheduler.start()
        scheduler.start()  # Ne doit pas planter
        assert scheduler._running is True
        scheduler.stop()

    def test_scheduler_stop_without_start(self, scheduler):
        """Vérifie que l'arrêt sans démarrage est sûr."""
        scheduler.stop()  # Ne doit pas planter
        assert scheduler._running is False

    def test_get_stats_initial(self, scheduler):
        """Vérifie les statistiques initiales."""
        stats = scheduler.get_stats()
        assert stats["checks"] == 0
        assert stats["jobs_created"] == 0
        assert stats["errors"] == 0
        assert stats["last_check"] is None

    def test_fetch_due_schedules_success(self, scheduler):
        """Vérifie la récupération des schedules dus."""
        now = datetime.now(timezone.utc)
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [
            ("s1", "Nuit", None, "0 22 * * *", "Europe/Paris",
             True, "c1", 5, now, None, 0)
        ]
        
        schedules = scheduler._fetch_due_schedules(mock_db)
        
        assert len(schedules) == 1
        assert schedules[0].name == "Nuit"
        assert schedules[0].cron_expression == "0 22 * * *"

    def test_fetch_due_schedules_empty(self, scheduler):
        """Vérifie le comportement quand aucun schedule n'est dû."""
        mock_db = MagicMock()
        mock_db.execute_query.return_value = []
        
        schedules = scheduler._fetch_due_schedules(mock_db)
        assert schedules == []

    def test_fetch_due_schedules_db_error(self, scheduler):
        """Vérifie la gestion d'erreur DB."""
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = Exception("DB Error")
        
        schedules = scheduler._fetch_due_schedules(mock_db)
        assert schedules == []

    def test_get_configs_for_schedule_with_config_id(self, scheduler):
        """Vérifie la récupération d'une config spécifique."""
        now = datetime.now(timezone.utc)
        schedule = IndexerScheduleConfig(
            id="s1", name="Test", description=None,
            cron_expression="0 22 * * *", timezone="Europe/Paris",
            is_active=True, config_id="config-1", priority=5,
            next_run_at=now, last_run_at=None, run_count=0
        )
        
        mock_db = MagicMock()
        mock_db.get_crawl_config_by_id.return_value = {
            "id": "config-1", "name": "Test Space",
            "start_path": "//server/share",
            "domain_zone": "WORKGROUP",
            "connection_username": "user", "connection_password": "pass",
            "connection_domain": None, "created_at": "2026-05-18"
        }
        
        configs = scheduler._get_configs_for_schedule(mock_db, schedule)
        
        assert len(configs) == 1
        assert configs[0]["name"] == "Test Space"

    def test_get_configs_for_schedule_all(self, scheduler):
        """Vérifie la récupération de toutes les configs."""
        now = datetime.now(timezone.utc)
        schedule = IndexerScheduleConfig(
            id="s1", name="Test", description=None,
            cron_expression="0 22 * * *", timezone="Europe/Paris",
            is_active=True, config_id=None, priority=5,
            next_run_at=now, last_run_at=None, run_count=0
        )
        
        mock_db = MagicMock()
        mock_db.list_crawl_configs.return_value = [
            {"id": "c1", "name": "Space 1", "start_path": "//srv1/share"},
            {"id": "c2", "name": "Space 2", "start_path": "//srv2/share"}
        ]
        
        configs = scheduler._get_configs_for_schedule(mock_db, schedule)
        
        assert len(configs) == 2

    def test_execute_schedule_creates_jobs(self, scheduler):
        """Vérifie que l'exécution d'un schedule crée bien les jobs."""
        now = datetime.now(timezone.utc)
        schedule = IndexerScheduleConfig(
            id="s1", name="Test", description=None,
            cron_expression="0 22 * * *", timezone="Europe/Paris",
            is_active=True, config_id="config-1", priority=5,
            next_run_at=now, last_run_at=None, run_count=0
        )
        
        mock_db = MagicMock()
        mock_db.get_crawl_config_by_id.return_value = {
            "id": "config-1", "name": "Test Space",
            "start_path": "//server/share",
            "domain_zone": "WORKGROUP",
            "connection_username": "user", "connection_password": "pass",
            "connection_domain": None, "created_at": "2026-05-18"
        }
        
        scheduler._execute_schedule(mock_db, schedule)
        
        # Vérifier que INSERT et UPDATE ont été appelés
        assert mock_db.execute_query.call_count >= 2
        assert scheduler._stats["jobs_created"] > 0

    def test_execute_schedule_no_configs(self, scheduler):
        """Vérifie le comportement quand aucune config n'est trouvée."""
        now = datetime.now(timezone.utc)
        schedule = IndexerScheduleConfig(
            id="s1", name="Test", description=None,
            cron_expression="0 22 * * *", timezone="Europe/Paris",
            is_active=True, config_id=None, priority=5,
            next_run_at=now, last_run_at=None, run_count=0
        )
        
        mock_db = MagicMock()
        mock_db.list_crawl_configs.return_value = []
        
        scheduler._execute_schedule(mock_db, schedule)
        assert scheduler._stats["jobs_created"] == 0

    def test_force_check_no_db(self, scheduler):
        """Vérifie que force_check ne plante pas si pas de DB."""
        # Pas de mock → _get_db retourne None
        count = scheduler.force_check()
        assert count == 0

    def test_global_scheduler_instance(self):
        """Vérifie l'instance globale du scheduler."""
        import backend.src.workers.indexer_scheduler as sched_module
        sched_module._scheduler_instance = None
        
        s1 = get_scheduler()
        s2 = get_scheduler()
        
        assert s1 is s2
        assert isinstance(s1, IndexerScheduler)

    def test_start_stop_global_scheduler(self):
        """Vérifie le démarrage/arrêt du scheduler global."""
        import backend.src.workers.indexer_scheduler as sched_module
        sched_module._scheduler_instance = None
        
        scheduler = start_scheduler()
        assert scheduler._running is True
        
        stop_scheduler()
        assert sched_module._scheduler_instance is None