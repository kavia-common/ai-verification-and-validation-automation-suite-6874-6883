"""
LLMService provides an abstraction over LLM providers with a mock mode.

Supported providers:
- mock (default): returns deterministic canned outputs suitable for tests
- openai (placeholder): demonstrates structure, returns fallback when no key
"""
from typing import List, Dict, Any
from .env import get_env


class LLMService:
    """Abstraction over LLM providers. Defaults to mock outputs."""

    def __init__(self) -> None:
        env = get_env()
        self.provider = env.llm_provider
        self.mock = env.llm_mock_mode
        self.api_key = env.llm_api_key

    # PUBLIC_INTERFACE
    def generate_test_cases(self, srs_title: str, srs_content: str) -> List[Dict[str, Any]]:
        """Generate structured test cases from SRS content."""
        if self.mock or self.provider == "mock":
            # Deterministic mock test cases
            return [
                {
                    "name": f"Verify title presence: {srs_title}",
                    "description": "Ensure the application displays the correct title on the homepage.",
                    "priority": "P1",
                    "tags": "ui,smoke",
                },
                {
                    "name": "Check login flow",
                    "description": "User can login with valid credentials and reach dashboard.",
                    "priority": "P0",
                    "tags": "auth,critical",
                },
            ]
        # Placeholder for real provider integration
        return [
            {
                "name": "Sample LLM Case",
                "description": "LLM provider not configured; returning placeholder.",
                "priority": "P2",
                "tags": "placeholder",
            }
        ]

    # PUBLIC_INTERFACE
    def generate_script(self, test_case: Dict[str, Any]) -> str:
        """Generate a pytest+Playwright script content for a given test case."""
        if self.mock or self.provider == "mock":
            # Very simple Playwright UI test using pytest
            name_slug = test_case.get("name", "test_case").lower().replace(" ", "_").replace(":", "")
            return f'''import pytest
from playwright.sync_api import sync_playwright


@pytest.mark.parametrize("url", ["https://example.com"])
def test_{name_slug}(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        assert page.title() is not None
        browser.close()
'''
        # Real provider would craft more detailed script
        return f"# Placeholder script for: {test_case.get('name','Unnamed')}\n"
