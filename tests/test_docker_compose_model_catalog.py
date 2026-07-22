from pathlib import Path

import yaml


def _volume_target(volume):
    if isinstance(volume, str):
        parts = volume.split(":")
        return parts[1] if len(parts) > 1 else None
    if isinstance(volume, dict):
        return volume.get("target")
    return None


def test_compose_does_not_shadow_image_model_catalogs():
    compose = yaml.safe_load((Path(__file__).parents[1] / "docker-compose.yml").read_text())
    volumes = compose["services"]["pal-mcp"].get("volumes", [])

    assert all(_volume_target(volume) != "/app/conf" for volume in volumes)


def test_volume_target_handles_short_and_long_compose_syntax():
    assert _volume_target("./conf:/app/conf:ro") == "/app/conf"
    assert _volume_target({"type": "bind", "source": "./conf", "target": "/app/conf"}) == "/app/conf"


def test_requirements_support_responses_api():
    requirements = (Path(__file__).parents[1] / "requirements.txt").read_text()
    project = (Path(__file__).parents[1] / "pyproject.toml").read_text()

    assert "openai>=1.66.0" in requirements
    assert '"openai>=1.66.0"' in project
