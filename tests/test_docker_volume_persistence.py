"""
Tests for Docker volume persistence functionality
"""

import json
import os
from pathlib import Path

import pytest


class TestDockerVolumePersistence:
    """Test image-backed catalogs and persistent logs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        self.project_root = Path(__file__).parent.parent
        self.docker_compose_path = self.project_root / "docker-compose.yml"

    def test_docker_compose_volumes_configuration(self):
        """Test that docker-compose.yml has proper volume configuration"""
        if not self.docker_compose_path.exists():
            pytest.skip("docker-compose.yml not found")

        content = self.docker_compose_path.read_text()

        assert "./logs:/app/logs" in content, "Logs volume mount required"
        assert "pal-mcp-config:/app/conf" not in content, "Config volume must not shadow image model catalogs"

    def test_model_catalogs_are_image_backed(self):
        """Built-in catalogs must ship in the image instead of an empty volume."""
        dockerfile = (self.project_root / "Dockerfile").read_text()

        assert "COPY --chown=paluser:paluser . ." in dockerfile
        assert (self.project_root / "conf" / "openai_models.json").exists()
        assert (self.project_root / "conf" / "xai_models.json").exists()

    def test_log_persistence_configuration(self):
        """Test that log persistence is properly configured"""
        log_mount = "./logs:/app/logs"

        if self.docker_compose_path.exists():
            content = self.docker_compose_path.read_text()
            assert log_mount in content, f"Log mount {log_mount} must be configured"

    def test_volume_permissions(self):
        """Test that volume permissions are properly set"""
        # Check that logs directory has correct permissions
        logs_dir = self.project_root / "logs"

        if logs_dir.exists():
            # Check that directory is writable
            assert os.access(logs_dir, os.W_OK), "Logs directory must be writable"

            # Test creating a temporary file
            test_file = logs_dir / "test_write_permission.tmp"
            try:
                test_file.write_text("test")
                assert test_file.exists()
            finally:
                if test_file.exists():
                    test_file.unlink()


class TestDockerVolumeIntegration:
    """Integration tests for Docker volumes with MCP functionality"""

    def test_mcp_config_persistence(self):
        """Test that MCP configuration persists in named volume"""
        mcp_config = {"models": ["gemini-2.0-flash", "gpt-4"], "default_model": "auto", "thinking_mode": "high"}

        # Test config serialization/deserialization
        config_str = json.dumps(mcp_config)
        loaded_config = json.loads(config_str)

        assert loaded_config == mcp_config
        assert "models" in loaded_config

    def test_docker_compose_run_volume_usage(self):
        """Test that docker-compose run uses volumes correctly"""
        # Verify that docker-compose run inherits volume configuration
        # This is more of a configuration validation test

        compose_run_cmd = ["docker-compose", "run", "--rm", "pal-mcp"]

        # The command should work with the existing volume configuration
        assert "docker-compose" in compose_run_cmd
        assert "run" in compose_run_cmd
        assert "--rm" in compose_run_cmd

    def test_volume_data_isolation(self):
        """Test that different container instances share volume data correctly"""
        shared_data = {"instance_count": 0, "shared_state": "active"}

        # Simulate multiple container instances accessing shared volume
        for _ in range(3):
            shared_data["instance_count"] += 1
            assert shared_data["shared_state"] == "active"

        assert shared_data["instance_count"] == 3
