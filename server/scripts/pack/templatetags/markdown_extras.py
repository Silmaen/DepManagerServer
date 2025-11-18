"""
Custom template tags for Markdown rendering.

This module provides template filters to render Markdown content as HTML
in Django templates with security considerations.
"""

import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(text: str) -> str:
    """
    Convert Markdown text to HTML.

    Supports:
    - Fenced code blocks with syntax highlighting
    - Tables
    - Automatic line breaks
    - Standard Markdown formatting

    :param text: Markdown formatted text
    :return: HTML safe string
    """
    if not text:
        return ""

    try:
        return mark_safe(
            markdown.markdown(
                text,
                extensions=[
                    "fenced_code",
                    "codehilite",
                    "tables",
                    "nl2br",
                    "sane_lists",
                ],
                extension_configs={
                    "codehilite": {"css_class": "highlight", "linenums": False}
                },
            )
        )
    except Exception as e:
        # Log error but return empty string to avoid breaking the page
        from pack.logger import logger

        logger.error(f"Error rendering markdown: {e}")
        return mark_safe(f'<p class="text-danger">Error rendering markdown content</p>')
