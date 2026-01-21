"""
Documentation serving router
Serves User Manual and Technical Manual as HTML
"""

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse
import markdown
import os

router = APIRouter()

def get_doc_path(filename: str) -> str:
    """Get absolute path to documentation file"""
    # Documentation files are mounted in /docs/ inside the container
    return os.path.join("/docs", filename)

def markdown_to_html(md_content: str, title: str, include_mermaid: bool = False) -> str:
    """Convert markdown to styled HTML"""
    import re
    import html

    # Convert markdown to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['fenced_code', 'tables', 'toc', 'nl2br']
    )

    # Replace mermaid code blocks with divs for rendering
    if include_mermaid:
        # Replace <pre><code class="language-mermaid">...</code></pre> with <div class="mermaid">...</div>
        def replace_mermaid(match):
            mermaid_code = match.group(1)
            # Unescape HTML entities
            mermaid_code = html.unescape(mermaid_code)
            return f'<div class="mermaid">{mermaid_code}</div>'

        html_content = re.sub(
            r'<pre><code class="language-mermaid">(.*?)</code></pre>',
            replace_mermaid,
            html_content,
            flags=re.DOTALL
        )
        # Also handle standalone code blocks
        html_content = re.sub(
            r'<code class="language-mermaid">(.*?)</code>',
            replace_mermaid,
            html_content,
            flags=re.DOTALL
        )

    # Add Mermaid.js script if needed
    mermaid_script = ""
    if include_mermaid:
        mermaid_script = """
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({
                startOnLoad: true,
                theme: 'default',
                securityLevel: 'loose'
            });
        </script>
        """

    # Wrap in a styled HTML template
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ombudsman.AI</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                background: #f5f5f5;
                padding: 0;
                margin: 0;
            }}

            .header {{
                background: #1976d2;
                color: white;
                padding: 0.5rem 2rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                gap: 1.5rem;
                min-height: 64px;
            }}

            .header h1 {{
                font-size: 1.25rem;
                margin: 0;
                font-weight: 500;
                color: white;
            }}

            .header p {{
                color: white;
                opacity: 0.9;
                font-size: 0.875rem;
                margin: 0;
                padding-left: 1.5rem;
                border-left: 1px solid rgba(255,255,255,0.3);
            }}

            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
                background: white;
                min-height: calc(100vh - 150px);
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}

            .content {{
                padding: 2rem 0;
            }}

            h1, h2, h3, h4, h5, h6 {{
                margin-top: 2rem;
                margin-bottom: 1rem;
                color: #1976d2;
            }}

            h1 {{
                font-size: 2.5rem;
                border-bottom: 3px solid #1976d2;
                padding-bottom: 0.5rem;
            }}

            h2 {{
                font-size: 2rem;
                border-bottom: 2px solid #e0e0e0;
                padding-bottom: 0.5rem;
            }}

            h3 {{
                font-size: 1.5rem;
            }}

            p {{
                margin-bottom: 1rem;
            }}

            code {{
                background: #f5f5f5;
                padding: 0.2rem 0.4rem;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 0.9rem;
                color: #d32f2f;
            }}

            pre {{
                background: #263238;
                color: #aed581;
                padding: 1rem;
                border-radius: 5px;
                overflow-x: auto;
                margin: 1rem 0;
            }}

            pre code {{
                background: none;
                color: inherit;
                padding: 0;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 1rem 0;
            }}

            th, td {{
                padding: 0.75rem;
                text-align: left;
                border: 1px solid #ddd;
            }}

            th {{
                background: #1976d2;
                color: white;
                font-weight: 600;
            }}

            tr:nth-child(even) {{
                background: #f5f5f5;
            }}

            ul, ol {{
                margin: 1rem 0;
                padding-left: 2rem;
            }}

            li {{
                margin: 0.5rem 0;
            }}

            blockquote {{
                border-left: 4px solid #1976d2;
                padding-left: 1rem;
                margin: 1rem 0;
                color: #666;
                font-style: italic;
            }}

            a {{
                color: #1976d2;
                text-decoration: none;
            }}

            a:hover {{
                text-decoration: underline;
            }}

            .toc {{
                background: #f5f5f5;
                padding: 1.5rem;
                border-radius: 5px;
                margin: 2rem 0;
            }}

            .toc h2 {{
                margin-top: 0;
            }}

            .back-button {{
                display: inline-block;
                background: #1976d2;
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 5px;
                text-decoration: none;
                margin-bottom: 1rem;
                transition: background 0.3s;
            }}

            .back-button:hover {{
                background: #1565c0;
                text-decoration: none;
            }}

            .footer {{
                background: #263238;
                color: white;
                text-align: center;
                padding: 1.5rem;
                margin-top: 2rem;
            }}

            @media print {{
                .header, .back-button, .footer {{
                    display: none;
                }}

                .container {{
                    box-shadow: none;
                    padding: 0;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Ombudsman.AI</h1>
            {f'<p>{title}</p>' if title else ''}
        </div>

        <div class="container">
            <a href="http://localhost:3002" class="back-button">← Back to Dashboard</a>

            <div class="content">
                {html_content}
            </div>
        </div>

        <div class="footer">
            <p>© 2025 Ombudsman.AI. All rights reserved.</p>
        </div>

        {mermaid_script}
    </body>
    </html>
    """

@router.get("/user-manual", response_class=HTMLResponse)
async def get_user_manual():
    """Serve the User Manual as HTML"""
    try:
        doc_path = get_doc_path("USER_MANUAL.md")

        if not os.path.exists(doc_path):
            return HTMLResponse(
                content="<h1>User Manual not found</h1><p>Please ensure USER_MANUAL.md exists in the project root.</p>",
                status_code=404
            )

        with open(doc_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        html = markdown_to_html(md_content, "User Manual")
        return HTMLResponse(content=html)

    except Exception as e:
        return HTMLResponse(
            content=f"<h1>Error loading User Manual</h1><p>{str(e)}</p>",
            status_code=500
        )

@router.get("/technical-manual", response_class=HTMLResponse)
async def get_technical_manual():
    """Serve the Technical Manual as HTML"""
    try:
        doc_path = get_doc_path("TECHNICAL_MANUAL.md")

        if not os.path.exists(doc_path):
            return HTMLResponse(
                content="<h1>Technical Manual not found</h1><p>Please ensure TECHNICAL_MANUAL.md exists in the project root.</p>",
                status_code=404
            )

        with open(doc_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        html = markdown_to_html(md_content, "Technical Manual")
        return HTMLResponse(content=html)

    except Exception as e:
        return HTMLResponse(
            content=f"<h1>Error loading Technical Manual</h1><p>{str(e)}</p>",
            status_code=500
        )

@router.get("/architecture", response_class=HTMLResponse)
async def get_architecture():
    """Serve the Architecture documentation as HTML"""
    try:
        doc_path = get_doc_path("ARCHITECTURE.md")

        if not os.path.exists(doc_path):
            return HTMLResponse(
                content="<h1>Architecture documentation not found</h1><p>Please ensure ARCHITECTURE.md exists in the project root.</p>",
                status_code=404
            )

        with open(doc_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        html = markdown_to_html(md_content, "System Architecture")
        return HTMLResponse(content=html)

    except Exception as e:
        return HTMLResponse(
            content=f"<h1>Error loading Architecture documentation</h1><p>{str(e)}</p>",
            status_code=500
        )

@router.get("/architecture-diagrams", response_class=HTMLResponse)
async def get_architecture_diagrams():
    """Serve the Architecture Diagrams as HTML with Mermaid rendering"""
    try:
        doc_path = get_doc_path("ARCHITECTURE_DIAGRAM.md")

        if not os.path.exists(doc_path):
            return HTMLResponse(
                content="<h1>Architecture Diagrams not found</h1><p>Please ensure ARCHITECTURE_DIAGRAM.md exists in the project root.</p>",
                status_code=404
            )

        with open(doc_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Enable Mermaid rendering for diagram visualization
        html = markdown_to_html(md_content, "Architecture Diagrams", include_mermaid=True)
        return HTMLResponse(content=html)

    except Exception as e:
        return HTMLResponse(
            content=f"<h1>Error loading Architecture Diagrams</h1><p>{str(e)}</p>",
            status_code=500
        )

@router.get("/", response_class=HTMLResponse)
async def docs_index():
    """Documentation index page"""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Documentation - Ombudsman.AI</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5;
            }

            .header {
                background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
                color: white;
                padding: 3rem 2rem;
                text-align: center;
            }

            .header h1 {
                font-size: 3rem;
                margin-bottom: 1rem;
            }

            .container {
                max-width: 1200px;
                margin: 2rem auto;
                padding: 2rem;
            }

            .docs-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 2rem;
            }

            .doc-card {
                background: white;
                padding: 2rem;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                transition: transform 0.3s, box-shadow 0.3s;
                text-decoration: none;
                color: inherit;
                display: block;
            }

            .doc-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 4px 16px rgba(0,0,0,0.15);
            }

            .doc-card h2 {
                color: #1976d2;
                margin-bottom: 1rem;
                font-size: 1.8rem;
            }

            .doc-card p {
                color: #666;
                line-height: 1.6;
                margin-bottom: 1rem;
            }

            .doc-card .badge {
                display: inline-block;
                background: #1976d2;
                color: white;
                padding: 0.25rem 0.75rem;
                border-radius: 3px;
                font-size: 0.8rem;
                font-weight: 600;
            }

            .back-button {
                display: inline-block;
                background: #1976d2;
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 5px;
                text-decoration: none;
                margin-bottom: 2rem;
            }

            .back-button:hover {
                background: #1565c0;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📚 Documentation</h1>
            <p>Comprehensive guides for Ombudsman Validation Studio</p>
        </div>

        <div class="container">
            <a href="http://localhost:3002" class="back-button">← Back to Dashboard</a>

            <div class="docs-grid">
                <a href="/docs/user-manual" class="doc-card">
                    <h2>User Manual</h2>
                    <p>Complete end-user guide with step-by-step instructions for all features, best practices, and troubleshooting.</p>
                    <span class="badge">32,000+ words</span>
                </a>

                <a href="/docs/technical-manual" class="doc-card">
                    <h2>Technical Manual</h2>
                    <p>Developer documentation with architecture details, API reference, code examples, and implementation guides.</p>
                    <span class="badge">18,000+ words</span>
                </a>

                <a href="/docs/architecture" class="doc-card">
                    <h2>System Architecture</h2>
                    <p>Detailed system architecture documentation covering components, data flows, security, and performance.</p>
                    <span class="badge">87KB</span>
                </a>

                <a href="/docs/architecture-diagrams" class="doc-card">
                    <h2>Architecture Diagrams</h2>
                    <p>12 interactive Mermaid diagrams visualizing system architecture, data flows, and component relationships.</p>
                    <span class="badge">Diagrams</span>
                </a>

                <a href="http://localhost:8000/docs" class="doc-card">
                    <h2>API Documentation</h2>
                    <p>Interactive API documentation with all endpoints, request/response examples, and testing interface.</p>
                    <span class="badge">Interactive</span>
                </a>
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html)
