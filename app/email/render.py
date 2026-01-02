"""
Email HTML rendering utilities.
Provides functions to convert markdown and digest responses to HTML email format.
"""

import html
import markdown


def get_email_css() -> str:
    """
    Get the base CSS styles for email templates.
    
    Returns:
        str: CSS styles as a string
    """
    return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
        }
        h2 {
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 24px;
            margin-bottom: 8px;
            line-height: 1.4;
        }
        h3 {
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 20px;
            margin-bottom: 8px;
            line-height: 1.4;
        }
        p {
            margin: 8px 0;
            color: #4a4a4a;
        }
        strong {
            font-weight: 600;
            color: #1a1a1a;
        }
        em {
            font-style: italic;
            color: #666;
        }
        a {
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }
        a:hover {
            text-decoration: underline;
        }
        hr {
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 20px 0;
        }
        .greeting {
            font-size: 16px;
            font-weight: 500;
            color: #1a1a1a;
            margin-bottom: 12px;
        }
        .introduction {
            color: #4a4a4a;
            margin-bottom: 20px;
        }
        .article-link {
            display: inline-block;
            margin-top: 8px;
            color: #0066cc;
            font-size: 14px;
        }
        .greeting p {
            margin: 0;
        }
        .introduction p {
            margin: 0;
        }
        div {
            margin: 8px 0;
            color: #4a4a4a;
        }
        div p {
            margin: 4px 0;
        }
    """


def wrap_html_content(content: str) -> str:
    """
    Wrap HTML content with email template (DOCTYPE, head, body, CSS).
    
    Args:
        content: HTML content to wrap
        
    Returns:
        str: Complete HTML document with styling
    """
    css = get_email_css()
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
{css}
    </style>
</head>
<body>
{content}
</body>
</html>"""


def markdown_to_html(markdown_text: str) -> str:
    """
    Convert markdown text to HTML with email styling.
    
    Args:
        markdown_text: Markdown formatted text
        
    Returns:
        str: HTML formatted string with embedded styles
    """
    html_content = markdown.markdown(markdown_text, extensions=['extra', 'nl2br'])
    return wrap_html_content(html_content)


def digest_to_html(digest_response) -> str:
    """
    Convert EmailDigestResponse to HTML format.
    
    Args:
        digest_response: EmailDigestResponse object
        
    Returns:
        str: HTML formatted email digest
    """
    from app.agent.email_agent import EmailDigestResponse
    
    if not isinstance(digest_response, EmailDigestResponse):
        return markdown_to_html(digest_response.to_markdown() if hasattr(digest_response, 'to_markdown') else str(digest_response))
    
    html_parts = []
    greeting_html = markdown.markdown(digest_response.introduction.greeting, extensions=['extra', 'nl2br'])
    introduction_html = markdown.markdown(digest_response.introduction.introduction, extensions=['extra', 'nl2br'])
    html_parts.append(f'<div class="greeting">{greeting_html}</div>')
    html_parts.append(f'<div class="introduction">{introduction_html}</div>')
    html_parts.append('<hr>')
    
    for article in digest_response.articles:
        html_parts.append(f'<h3>{html.escape(article.title)}</h3>')
        summary_html = markdown.markdown(article.summary, extensions=['extra', 'nl2br'])
        html_parts.append(f'<div>{summary_html}</div>')
        html_parts.append(f'<p><a href="{html.escape(article.url)}" class="article-link">Read more →</a></p>')
        html_parts.append('<hr>')
    
    html_content = '\n'.join(html_parts)
    return wrap_html_content(html_content)

