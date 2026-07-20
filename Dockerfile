# Full-stack image: FastAPI API + frontend (landing + converter) + a Java runtime.
#
# One container = the WHOLE product works: conversion, language detection, AI
# validation, and JVM bytecode decompilation (CFR needs `java`). No split
# frontend/backend, no CORS, no serverless limits.
#
# Deploy anywhere that takes a Dockerfile (Render, Railway, Fly.io, HF Spaces).
# Required env var at runtime: GROQ_API_KEY
FROM python:3.12-slim

# `java` is required by the CFR bytecode decompiler (/decompile).
# Everything else works without it, but we want the full feature set.
RUN apt-get update \
 && apt-get install -y --no-install-recommends default-jre-headless \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first so image layers cache well.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# App code + frontend. main.py resolves public/ as ../public relative to itself.
COPY backend/ ./backend/
COPY public/  ./public/

ENV CODECONV_COMPILE_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000
WORKDIR /app/backend

# Hosts inject $PORT; bind to it, not a fixed port.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
