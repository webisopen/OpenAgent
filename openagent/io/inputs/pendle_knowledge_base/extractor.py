from io import BytesIO

from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter


def docling_extractor(html: str) -> str:
    """Extract content from HTML and convert to markdown using docling.

    Args:
        html: Raw HTML content to convert

    Returns:
        Markdown formatted string
    """
    try:
        # Create document stream from HTML
        buf = BytesIO(html.encode('utf-8'))
        source = DocumentStream(name="webpage.html", stream=buf)

        # Convert to markdown using docling
        converter = DocumentConverter()
        result = converter.convert(source)
        markdown = result.document.export_to_markdown()
        return markdown
    except Exception as e:
        print(f"Error converting HTML to markdown: {e}")
        return ""
