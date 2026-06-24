# Text Your Song – Web-App + Analyse-Pipeline.
# Enthält ffmpeg (für yt-dlp/librosa/demucs). Schwere ML-Pakete optional via Build-Arg.
FROM python:3.11-slim

ARG INSTALL_HEAVY=true

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-heavy.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_HEAVY" = "true" ]; then \
         pip install --no-cache-dir -r requirements-heavy.txt; \
       fi

COPY pyproject.toml ./
COPY src ./src
COPY webapp ./webapp
COPY worker.py ./
RUN pip install --no-cache-dir -e .

ENV WORKSPACE_DIR=/data/workspace
VOLUME ["/data/workspace"]
EXPOSE 8000

CMD ["uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
