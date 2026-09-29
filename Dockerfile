FROM python:3.11-slim

WORKDIR /app

# fonts for kneeboard rendering (no git — pydcs is vendored, see below)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# pydcs is VENDORED in vendor/dcs and put on sys.path by server/app.py. Do NOT
# pip-install it: the vendored copy always wins (sys.path.insert), so a pip
# install would pull an unpinned upstream at build time and then never be used —
# non-reproducible AND inert. The vendored tree is the single source of truth.
COPY missiongen ./missiongen
COPY vendor ./vendor
COPY docs ./docs
COPY server ./server
COPY frontend ./frontend
# THE IMAGE CARRIES NO CONTENT. Not the uploaded packs, not the generated ones.
#
# This was tried the other way for exactly one release: the four built-in
# syllabi were built into the image, which made it 44 MB heavier and the
# release zip 59 MB — big enough that it could no longer be handed over a
# normal channel. The deciding argument is not the size though, it is the
# coupling: content baked into an image can only change by deploying, and a
# corrected premise line is not a deploy.
#
# So packs are PRODUCED by scripts/build_pack.py and UPLOADED through /admin to
# the Fly volume (PACKS_DATA_DIR). Adding, fixing or removing content never
# touches this file. See docs/content-architecture.md.

# run unprivileged
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8080
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8080"]
