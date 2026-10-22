import json
from pathlib import Path

import pytest

from app.main import app

SNAPSHOT = Path(__file__).resolve().parents[2] / "web" / "openapi.json"
PUBLIC_JSON = (
    ("get", "/api/categories"), ("get", "/api/kinds"), ("get", "/api/tags"), ("get", "/api/projects"),
    ("get", "/api/projects/featured"), ("get", "/api/projects/{project_id}"), ("get", "/api/how-i-work"),
    ("get", "/api/experience"), ("get", "/api/education"), ("get", "/api/articles"), ("get", "/api/articles/{article_id}"),
    ("get", "/api/profile"), ("get", "/api/settings"), ("get", "/api/updates"), ("post", "/api/ask"),
    ("get", "/api/health"), ("get", "/api/health/live"),
)


def test_the_committed_openapi_file_matches_the_api():
    """web/openapi.json is what the website's types are generated from. If this fails, run in api/:
    python -m scripts.export_openapi   and then in web/:   npm run api:types"""
    if not SNAPSHOT.exists():
        pytest.skip("web/ is not next to api/ (running inside the api container)")
    assert json.loads(SNAPSHOT.read_text(encoding="utf-8")) == app.openapi()


def test_only_the_public_api_is_described():
    paths = app.openapi()["paths"]
    assert paths and all(path.startswith("/api/") for path in paths)  # no admin pages, which are HTML for one person


def test_every_public_json_route_has_a_typed_response():
    """A route without a response model would become `any` in TypeScript."""
    paths = app.openapi()["paths"]
    for method, path in PUBLIC_JSON:
        ok = paths[path][method]["responses"]["200"]["content"]["application/json"]["schema"]
        assert ok and ok != {}, (method, path)


def test_the_models_describe_the_fields_the_website_reads():
    schemas = app.openapi()["components"]["schemas"]
    assert {"ProjectCard", "ProjectDetail", "ProjectList", "WorkItem", "ArticleCard", "ArticleDetail", "ProfileOut",
            "SettingsOut", "AskOut", "CategoryOut", "TagCount", "ImageOut"} <= set(schemas)
    assert schemas["WorkItem"]["properties"]["span"]["enum"] == ["range", "ongoing", "moment"]
    assert "how_i_work_project_id" in schemas["SettingsOut"]["properties"]
    assert set(schemas["AskOut"]["properties"]["mode"]["enum"]) >= {"answer", "no_answer", "fallback", "rate_limited"}
    assert "images" in schemas["ProjectDetail"]["required"] and "images" not in schemas["ProjectCard"]["properties"]
