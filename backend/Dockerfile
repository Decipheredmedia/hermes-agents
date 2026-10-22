FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/instagram.db
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY backend/app ./backend/app
COPY backend/api ./backend/api
COPY backend/models ./backend/models
COPY backend/integrations ./backend/integrations
COPY backend/ollama_client.py ./backend/ollama_client.py
COPY orchestrator ./orchestrator
RUN mkdir -p /data
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
