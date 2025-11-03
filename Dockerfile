# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
   PYTHONUNBUFFERED=1 \
   PIP_NO_CACHE_DIR=1 \
   PORT=8000 \
   STREAMLIT_SERVER_HEADLESS=true \
   STREAMLIT_BROWSER_GATHER_USAGE_STATS=false 

# System deps for pyodbc + ODBC 18 (modern, no apt-key)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg ca-certificates apt-transport-https build-essential unixodbc-dev \
 && install -d /usr/share/keyrings \
 && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/microsoft-prod.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
   && pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root for security
RUN useradd -ms /bin/bash appuser \
   && mkdir -p /home/appuser/.streamlit \
   && chown -R appuser:appuser /home/appuser /app 
USER appuser 

EXPOSE 8000
CMD ["streamlit", "run", "streamlit_app/Main.py", "--server.address=0.0.0.0", "--server.port=${PORT}"]