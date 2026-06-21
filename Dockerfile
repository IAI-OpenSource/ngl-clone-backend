# --- Étape 1 : Base commune ---
FROM python:3.11-slim AS builder

ENV WORKDIR=/app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR $WORKDIR

# Installation des dépendances système minimales
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# On installe dans /usr/local ici pour que Playwright soit directement accessible pour la suite du build
RUN pip install --no-cache-dir -r requirements.txt

# Télécharge Chromium dans le cache Playwright. Les dépendances système sont
# installées dans le stage runtime, là où le worker lance réellement le navigateur.
RUN playwright install chromium

# --- Stage 2: Runtime ---
FROM python:3.11-slim
ENV WORKDIR=/app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR $WORKDIR

# Récupération de tout l'environnement Python propre (y compris les navigateurs Playwright installés)
COPY --from=builder /usr/local /usr/local
# Playwright installe par défaut ses navigateurs dans ~/.cache/ms-playwright, on les copie aussi !
COPY --from=builder /root/.cache /root/.cache

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && DEBIAN_FRONTEND=noninteractive playwright install-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY . .
