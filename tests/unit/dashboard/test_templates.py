"""Tests for the dashboard's Jinja environment."""

from adw.dashboard.server import build_templates


def test_build_templates_registers_the_format_filters() -> None:
    env = build_templates().env
    template = env.from_string(
        "{{ 1234.5|cost }} {{ 1500|tokens }} {{ 90|duration }} {{ 2048|filesize }}"
    )

    assert template.render() == "$1,234.50 1.5K 1m 30s 2.0 KB"
