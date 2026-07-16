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

# run unprivileged
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8080
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8080"]
