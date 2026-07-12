FROM python:3.11-slim

WORKDIR /app

# fonts for kneeboard rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# pydcs from GitHub master (PyPI release is outdated); vendor the package if the
# wheel build fails (it's pure python)
RUN pip install --no-cache-dir "pydcs @ git+https://github.com/pydcs/dcs.git" || ( \
    git clone --depth 1 https://github.com/pydcs/dcs.git /tmp/pydcs && \
    cp -r /tmp/pydcs/dcs "$(python -c 'import site; print(site.getsitepackages()[0])')/" && \
    rm -rf /tmp/pydcs )

COPY missiongen ./missiongen
COPY vendor ./vendor
COPY docs ./docs
COPY server ./server
COPY frontend ./frontend

EXPOSE 8080
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8080"]
