from app.api import bp
from app.extensions import db
from flask import request, abort, jsonify, url_for, current_app
from app.models import User, Post
import sqlalchemy as sa


@bp.route("/.well-known/webfinger")
def webfinger():
    resource = request.args.get("resource", "")
    if not resource.startswith("acct:"):
        abort(400, "Invalid resource format")

    # Extract the username from the resource identifier "acct:username@example.com"
    try:
        username, domain = resource[5:].split("@", 1)
    except ValueError:
        abort(400, "Invalid resource format")

    # Find the user in the database
    user = User.query.filter_by(username=username).first()
    if not user:
        abort(404, "User not found")

    # Build the WebFinger JRD response
    jrd = {
        "subject": resource,
        "aliases": [
            url_for("api.webfinger", _external=True)
            + f"?resource=acct:{user.username}@{domain}"
        ],
        "links": [
            {
                "rel": "self",
                "type": "application/activity+json",
                "href": url_for("api.actor", username=user.username, _external=True),
            }
        ],
    }
    return jsonify(jrd)


@bp.route("/actor/<string:username>")
def actor(username: str):
    user = User.query.filter_by(username=username).first_or_404()
    public_keys = []
    # If the user has multiple public keys (assumed to be stored in user.public_keys), use them.
    # Otherwise, use a default public key.
    if hasattr(user, "public_keys") and user.public_keys:
        for key in user.public_keys:
            public_keys.append(
                {
                    "id": f"{get_actor_url(user.username)}#{key.key_id}",
                    "owner": get_actor_url(user.username),
                    "publicKeyPem": key.public_key_pem,
                }
            )
    else:
        public_keys.append({})

    return jsonify(
        {
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": get_actor_url(user.username),
            "type": "Person",
            "preferredUsername": user.username,
            "inbox": f"{get_actor_url(user.username)}/inbox",
            "outbox": f"{get_actor_url(user.username)}/outbox",
            "followers": f"{get_actor_url(user.username)}/followers",
            "publicKeys": public_keys,
        }
    )


def get_actor_url(username: str):
    """Returns the actor URL based on the current server hostname."""
    return f"{request.host_url.rstrip('/')}/actors/{username}"


@bp.route("/actors/<string:username>/outbox")
def outbox(username: str):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get("page", 1, type=int)
    query = (
        sa.select(Post).where(Post.user_id == user.id).order_by(Post.created_at.desc())
    )
    posts_paginated = db.paginate(
        query, page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
    )
    next_url = (
        url_for(
            "api.outbox",
            username=username,
            page=posts_paginated.next_num,
            _external=True,
        )
        if posts_paginated.has_next
        else None
    )
    posts: list[dict[str, str, list, dict]] = []
    for post in posts_paginated:
        posts.append(
            {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": url_for(
                    "api.get_activity",
                    post_id=post.id,
                    _external=True,
                    username=username,
                ),
                "type": "Create",
                "actor": get_actor_url(username),
                "published": post.created_at.isoformat(),
                "to": ["https://www.w3.org/ns/activitystreams#Public"],
                "object": {
                    "id": url_for(
                        "main.view_post", post_id=post.id, _external=True
                    ),  # User-readable version
                    "type": "Note",
                    "attributedTo": get_actor_url(username),
                    "content": post.content,
                    "published": post.created_at.isoformat(),
                    "url": url_for(
                        "main.view_post", post_id=post.id, _external=True
                    ),  # Explicit user-readable link
                },
            }
        )
    return jsonify(
        {
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": f"{get_actor_url(username)}/outbox",
            "type": "OrderedCollectionPage",
            "totalItems": len(user.posts),
            "orderedItems": posts,
            "next": next_url,
        }
    )


@bp.route("/actors/<string:username>/posts/<int:post_id>/activity")
def get_activity(username, post_id):
    user = User.query.filter_by(username=username).first_or_404()
    post: Post = Post.query.filter_by(id=post_id, user_id=user.id).first_or_404()

    return jsonify(
        {
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": url_for(
                "bp.get_activity", username=username, post_id=post.id, _external=True
            ),
            "type": "Create",
            "actor": get_actor_url(username),
            "published": post.created_at.isoformat(),
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "object": {
                "id": url_for("main.view_post", post_id=post.id, _external=True),
                "type": "Note",
                "attributedTo": get_actor_url(username),
                "content": post.content,
                "published": post.created_at.isoformat(),
                "url": url_for("main.view_post", post_id=post.id, _external=True),
            },
        }
    )
