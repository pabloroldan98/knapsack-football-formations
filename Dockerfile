# Calculadora Fantasy – API (FastAPI)
# Uso: docker build -t calculadora-fantasy-api .
#       docker run -p 8000:8000 -e FRONTEND_URL=https://www.calculadorafantasy.com calculadora-fantasy-api

FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema que pueden necesitar algunos paquetes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la aplicación ( .dockerignore excluye frontend, .git, .venv, etc.)
COPY . .

# Puerto por defecto (se puede sobreescribir con -e PORT=8080)
ENV PORT=8000
EXPOSE 8000

# Variable obligatoria: URL del frontend para CORS
ENV FRONTEND_URL=https://www.calculadorafantasy.com

CMD ["sh", "-c", "python -m uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
