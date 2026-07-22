from pathlib import Path

import yaml


def test_compose_does_not_shadow_image_model_catalogs():
    compose = yaml.safe_load((Path(__file__).parents[1] / "docker-compose.yml").read_text())
    volumes = compose["services"]["pal-mcp"].get("volumes", [])

    assert not any(str(volume).endswith(":/app/conf") for volume in volumes)


def test_requirements_support_responses_api():
    requirements = (Path(__file__).parents[1] / "requirements.txt").read_text()

    assert "openai>=1.66.0" in requirements
