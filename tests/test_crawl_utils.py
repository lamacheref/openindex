"""
Tests unitaires pour les utilitaires de crawl SMB (T-INDEX-01)
Tests du client SMB simplifié via smbclient (subprocess)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from datetime import datetime
import subprocess
import os

# Ajout du chemin pour les imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.src.utils.crawl_utils import SMBClient


class FakeSubprocessResult:
    """Résultat factice de subprocess.run."""
    
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestSMBClientInitialization:
    """Tests de l'initialisation du client SMB."""

    def test_client_creation_default_domain(self):
        """Vérifie la création avec domaine par défaut."""
        client = SMBClient(
            host="server.local",
            share="partage",
            username="user",
            password="pass"
        )
        assert client.host == "server.local"
        assert client.share == "partage"
        assert client.username == "user"
        assert client.password == "pass"
        assert client.domain == "WORKGROUP"  # Domaine par défaut
        assert client.connected is False
        assert client._share_url == "//server.local/partage"

    def test_client_creation_custom_domain(self):
        """Vérifie la création avec domaine personnalisé."""
        client = SMBClient(
            host="server.local",
            share="partage",
            username="user",
            password="pass",
            domain="CUSTOM_DOMAIN"
        )
        assert client.domain == "CUSTOM_DOMAIN"
        assert client._share_url == "//server.local/partage"


class TestSMBClientConnect:
    """Tests de la méthode connect."""

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_connect_success(self, mock_run):
        """Vérifie une connexion réussie."""
        mock_run.return_value = FakeSubprocessResult(
            returncode=0,
            stdout="Sharename       Type      Comment\n---------       ----      -------\npartage         Disk      \n"
        )
        
        client = SMBClient("server", "share", "user", "pass")
        result = client.connect()
        
        assert result is True
        assert client.connected is True
        
        # Vérifier que smbclient a été appelé avec les bons arguments
        cmd = mock_run.call_args[0][0]
        assert "smbclient" in cmd
        assert "-L" in cmd
        assert "server" in cmd

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_connect_failure(self, mock_run):
        """Vérifie une connexion échouée."""
        mock_run.return_value = FakeSubprocessResult(
            returncode=1,
            stderr="Connection to server failed"
        )
        
        client = SMBClient("server", "share", "user", "pass")
        result = client.connect()
        
        assert result is False
        assert client.connected is False

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_connect_timeout(self, mock_run):
        """Vérifie le comportement en cas de timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="smbclient", timeout=10, output=""
        )
        
        client = SMBClient("server", "share", "user", "pass")
        result = client.connect()
        
        assert result is False
        assert client.connected is False

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_connect_password_via_env(self, mock_run):
        """Vérifie que le mot de passe est passé via variable d'environnement."""
        mock_run.return_value = FakeSubprocessResult(returncode=0)
        
        client = SMBClient("server", "share", "user", "secret_pass")
        client.connect()
        
        # Vérifier que PASSWD est dans l'environnement
        env = mock_run.call_args[1].get('env', {})
        assert env.get('PASSWD') == 'secret_pass'


class TestSMBClientDisconnect:
    """Tests de la méthode disconnect."""

    def test_disconnect(self):
        """Vérifie la déconnexion."""
        client = SMBClient("server", "share", "user", "pass")
        client.connected = True
        
        # La déconnexion ne fait rien pour smbclient (pas de connexion persistante)
        client.disconnect()
        assert client.connected is False


class TestSMBClientConnected:
    """Tests de l'attribut connected."""

    def test_connected_false_by_default(self):
        """Vérifie que connected est False par défaut."""
        client = SMBClient("server", "share", "user", "pass")
        assert client.connected is False
        
        client.connected = True
        assert client.connected is True


class TestSMBClientListDir:
    """Tests de la méthode list_dir."""

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_list_dir_success(self, mock_run):
        """Vérifie le listage réussi d'un répertoire."""
        mock_run.return_value = FakeSubprocessResult(
            returncode=0,
            stdout="  file1.txt            A  1024  Mon May 18 10:00:00 2026\n"
                   "  file2.pdf            A  2048  Mon May 18 10:05:00 2026\n"
                   "  D                   D  0     Mon May 18 09:00:00 2026  subfolder\n"
        )
        
        client = SMBClient("server", "share", "user", "pass")
        entries = client.list_dir("/remote/path")
        
        assert entries is not None
        assert len(entries) > 0

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_list_dir_empty(self, mock_run):
        """Vérifie le listage d'un répertoire vide."""
        mock_run.return_value = FakeSubprocessResult(
            returncode=0,
            stdout=""
        )
        
        client = SMBClient("server", "share", "user", "pass")
        entries = client.list_dir("/remote/path")
        
        assert isinstance(entries, list)

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_list_dir_failure(self, mock_run):
        """Vérifie la gestion d'erreur lors du listage."""
        mock_run.return_value = FakeSubprocessResult(
            returncode=1,
            stderr="NT_STATUS_ACCESS_DENIED"
        )
        
        client = SMBClient("server", "share", "user", "pass")
        entries = client.list_dir("/remote/path")
        
        assert entries == []


class TestGetFileInfo:
    """Tests de la fonction autonome get_file_info (hors de SMBClient)."""

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_get_file_info_success(self, mock_run):
        """Vérifie la récupération des infos via la fonction get_file_info."""
        from backend.src.utils.crawl_utils import get_file_info
        
        # Simuler list_dir qui retourne un répertoire avec le fichier cherché
        mock_run.return_value = FakeSubprocessResult(
            returncode=0,
            stdout="  file.txt            A  1048576  Mon May 18 10:00:00 2026\n"
                   "  other.pdf           A  2048    Mon May 18 10:00:00 2026\n"
        )
        
        client = SMBClient("server", "share", "user", "pass")
        info = get_file_info(client, "/remote/path/file.txt")
        
        assert info is not None
        assert info.get('name') == 'file.txt'
        assert info.get('size') == 1048576

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_get_file_info_not_found(self, mock_run):
        """Vérifie le comportement quand le fichier n'existe pas."""
        from backend.src.utils.crawl_utils import get_file_info
        
        mock_run.return_value = FakeSubprocessResult(
            returncode=0,
            stdout="  other.txt           A  512     Mon May 18 10:00:00 2026\n"
        )
        
        client = SMBClient("server", "share", "user", "pass")
        info = get_file_info(client, "/remote/path/missing.txt")
        
        assert info is None

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_get_file_info_list_error(self, mock_run):
        """Vérifie la gestion d'erreur quand le listage échoue."""
        from backend.src.utils.crawl_utils import get_file_info
        
        mock_run.return_value = FakeSubprocessResult(
            returncode=1,
            stderr="NT_STATUS_ACCESS_DENIED"
        )
        
        client = SMBClient("server", "share", "user", "pass")
        info = get_file_info(client, "/remote/path/file.txt")
        
        assert info is None

class TestSMBClientFileExists:
    """Tests de la méthode file_exists."""

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_file_exists_true(self, mock_run):
        """Vérifie que file_exists retourne True quand le fichier existe."""
        # Premier appel (déjà mocké par défaut), second appel pour list_dir
        mock_run.return_value = FakeSubprocessResult(
            returncode=0,
            stdout="  target.txt          A  1024    Mon May 18 10:00:00 2026\n"
        )
        
        client = SMBClient("server", "share", "user", "pass")
        assert client.file_exists("/remote/path/target.txt") is True

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_file_exists_false(self, mock_run):
        """Vérifie que file_exists retourne False quand le fichier n'existe pas."""
        mock_run.return_value = FakeSubprocessResult(
            returncode=0,
            stdout="  other.txt           A  512     Mon May 18 10:00:00 2026\n"
        )
        
        client = SMBClient("server", "share", "user", "pass")
        assert client.file_exists("/remote/path/missing.txt") is False

    @patch('backend.src.utils.crawl_utils.subprocess.run')
    def test_file_exists_error(self, mock_run):
        """Vérifie que file_exists retourne False en cas d'erreur."""
        mock_run.return_value = FakeSubprocessResult(
            returncode=1,
            stderr="NT_STATUS_OBJECT_NAME_NOT_FOUND"
        )
        
        client = SMBClient("server", "share", "user", "pass")
        assert client.file_exists("/remote/path/file.txt") is False
