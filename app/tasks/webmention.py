# tasks/webmention.py
import httpx
from urllib.parse import urlparse
from app.extensions import db
from app.models import Webmention, Blog  # You need a model to store them

def is_valid_webmention(source, target):
    try:
        resp = httpx.get(source, timeout=5)
        return resp.status_code == 200 and target in resp.text
    except Exception:
        return False

def process_webmention(source: str, target: str):
    if not is_valid_webmention(source, target):
        return False
    
    target_url = urlparse(target)

    # Split hostname by dots
    parts = target_url.hostname.split('.')

    # Assumes domain is like 'example.com' (2 parts). Subdomains will be everything before that.
    slug = '.'.join(parts[:-2]) if len(parts) > 2 else ''
    if not slug:
        target_path_parts = target_url.path.strip('/').split('/')  # ['foo', 'bar', 'baz']

        slug = target_path_parts[1] if len(target_path_parts) > 1 else ''
        return False
    blog = Blog.query.filter_by(slug=slug).first()

    if not blog:
        return False

    # Example: storing in DB
    mention = Webmention(source=source, target=target, verified=True, blog=blog)
    db.session.add(mention)
    db.session.commit()
    return True