# Guía de Despliegue - Calculadora Fantasy

## Arquitectura

```
calculadorafantasy.com (IONOS)          Render.com (gratis)
┌──────────────────────────┐           ┌──────────────────────────────┐
│  index.html (landing)    │           │  api.py (FastAPI + Uvicorn)  │
│  app/index.html          │ ── API ──>│  main.py, group_knapsack.py  │
│  app/css/style.css       │  (HTTPS)  │  player.py, MCKP.py          │
│  app/js/app.js           │           │  json_files/ (datos)         │
└──────────────────────────┘           └──────────────────────────────┘
  Solo archivos estáticos                Ejecuta Python (knapsack,
  (no ejecuta código)                    cálculos, datos de jugadores)
```

### ¿Por qué dos sitios?

- **IONOS** (tu hosting actual): Sirve solo archivos estáticos (HTML, CSS, JS, imágenes).
  No puede ejecutar Python. Ya lo tienes pagado y tu dominio apunta ahí.
- **Render.com** (gratis): Ejecuta tu código Python (FastAPI) que hace los cálculos
  del knapsack, carga datos de jugadores, etc. Esto NO puede ir en IONOS ni en
  GitHub Pages porque necesita un servidor Python activo.

> **¿Y GitHub Pages?** GitHub Pages es igual que IONOS: solo sirve archivos estáticos.
> Podría sustituir a IONOS para el frontend, pero NO puede sustituir a Render para
> el backend. Como ya tienes IONOS con tu dominio configurado, no tiene sentido
> mover el frontend a GitHub Pages. Si en el futuro dejas IONOS, entonces sí podrías
> usar GitHub Pages (gratis) para el frontend.

---

## 1. Desplegar el Backend (API)

### Opción A: Render.com (gratis)

1. Haz **push** de tus cambios a GitHub (necesario para que Render clone el repo).
2. Crea una cuenta en [render.com](https://render.com) y conecta tu repositorio.
3. Crea un nuevo **Web Service**:
   - **Runtime**: Python 3
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free (750 horas/mes)
4. En **Environment** añade:
   - `FRONTEND_URL` = `https://www.calculadorafantasy.com`
5. Guarda y despliega. Tu API quedará en una URL como:
   `https://knapsack-football-formations.onrender.com`

**Si el deploy falla**: revisa que **api.py** esté en el repo (en la raíz) y que en Render **Root Directory** esté vacío. Build = `pip install -r requirements.txt`, Start = `uvicorn api:app --host 0.0.0.0 --port $PORT`.

> **Nota sobre el plan Free de Render**: El servidor se "duerme" tras 15 min sin
> tráfico. La primera petición tras un periodo de inactividad tardará ~30 seg
> mientras se despierta. Después irá normal. Si quieres evitar esto, puedes usar
> el plan Starter ($7/mes) o configurar un "keep-alive" ping (un cron job que
> haga un request a `/api/health` cada 14 minutos).

### Alternativa: Railway.app

1. Crea cuenta en [railway.app](https://railway.app)
2. Nuevo proyecto → Deploy from GitHub repo
3. Railway detecta el `Procfile` automáticamente
4. Añade la variable `FRONTEND_URL`
5. Te da una URL tipo: `https://calculadora-fantasy.up.railway.app`
6. Railway da $5/mes de crédito gratis (suficiente para uso moderado)

### Opción B: Docker (para que lo hostee un amigo o un VPS)

Tienes una imagen Docker configurable. Tu amigo (o tú en un VPS) solo necesita la URL del frontend y exponer el puerto.

#### Paso a paso para quien hostea (tu amigo)

1. **Clonar el repo** (o que tú le pases el código):
   ```bash
   git clone https://github.com/TU-USUARIO/knapsack_football_formations.git
   cd knapsack_football_formations
   ```

2. **Configuración mínima**
   Crear un archivo `docker.env` (o el nombre que use) con una sola variable:
   ```bash
   FRONTEND_URL=https://www.calculadorafantasy.com
   ```
   (Puede copiar `docker.env.example` y renombrarlo/editarlo.)

3. **Construir la imagen**:
   ```bash
   docker build -t calculadora-fantasy-api .
   ```

4. **Ejecutar el contenedor**:
   ```bash
   docker run -d --name calculadora-api --restart unless-stopped \
     --env-file docker.env \
     -p 8000:8000 \
     calculadora-fantasy-api
   ```
   - `-p 8000:8000`: el API queda en el puerto 8000 del servidor.
   - Si quiere otro puerto en el host: `-p 9080:8000` (entonces la API sería `http://IP:9080`).

5. **Probar**:
   ```bash
   curl http://localhost:8000/api/health
   ```
   Debe devolver `{"status":"ok"}`.

6. **Exponer al exterior**
   Quien hostea debe:
   - Abrir el puerto 8000 (o el que haya usado) en el firewall.
   - Tener un dominio (o IP fija) y, si quiere HTTPS, un reverse proxy (nginx, Caddy, etc.) delante del contenedor.

7. **Decirte la URL final del API**
   Ejemplo: `https://api.calculadorafantasy.com` o `http://IP:8000`.
   Tú pones esa URL en `app/js/app.js` en la variable `API_BASE` (ver paso 2).

#### Comandos útiles para quien hostea

```bash
# Ver logs
docker logs -f calculadora-api

# Parar
docker stop calculadora-api

# Arrancar de nuevo
docker start calculadora-api

# Actualizar (tras un git pull)
docker stop calculadora-api && docker rm calculadora-api
docker build -t calculadora-fantasy-api .
docker run -d --name calculadora-api --restart unless-stopped --env-file docker.env -p 8000:8000 calculadora-fantasy-api
```

---

### Verificar que la API funciona

```bash
curl https://knapsack-football-formations.onrender.com/api/health
# Debe devolver: {"status": "ok"}
```

(Sustituye por la URL de tu API si usas Docker en otro servidor.)

---

## 2. Actualizar la URL del API en el Frontend

Edita `app/js/app.js`, línea ~8. Si usas Render con la URL que te dieron:

```javascript
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : 'https://knapsack-football-formations.onrender.com';
```

Si tu amigo te da otra URL (por ejemplo `https://api.calculadorafantasy.com`), pon esa en lugar de `https://knapsack-football-formations.onrender.com`.

---

## 3. Desplegar el Frontend en IONOS

### 3A. Subir archivos a IONOS (FTP o panel)

Sube estos archivos/carpetas a la raíz de tu hosting (`/public/`):

```
/public/                    (raíz del hosting en IONOS)
├── index.html              (landing page)
├── img/                    (imágenes del landing)
│   ├── logo.png
│   ├── screenshot1.png
│   └── ...
├── app/
│   ├── index.html          (aplicación principal)
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── ads.txt                 (contenido ver sección 4)
```

### Deploy automático con GitHub Actions (recomendado)

Cada vez que haces **push a `master`** y los cambios tocan archivos del frontend
(`index.html`, `app/`, `img/`, `ads.txt`), GitHub Actions sube automáticamente
esos archivos a IONOS por SFTP. No tienes que subir nada a mano.

**Configuración (una sola vez):**

1. En IONOS, crea/usa un acceso SFTP (en tu panel → Hosting → SFTP/SSH).
   Apunta: host, usuario, contraseña y puerto (normalmente 22).

2. En GitHub, ve a tu repo → **Settings** → **Secrets and variables** → **Actions** →
   **New repository secret**. Crea estos 4 secretos:

   | Nombre | Valor |
   |--------|-------|
   | `IONOS_HOST` | Host SFTP (ej. `access-xxxx.webspace-data.io`) |
   | `IONOS_USER` | Tu usuario SFTP |
   | `IONOS_PASS` | Tu contraseña SFTP |
   | `IONOS_PORT` | `22` |

3. Haz push. El workflow `.github/workflows/deploy-ionos-frontend.yml` ya está
   en el repo y se ejecutará automáticamente.

**¿Qué sube?** Solo estos archivos/carpetas a `/public` en IONOS:
- `index.html` (landing)
- `ads.txt`
- `img/` (imágenes)
- `app/` (HTML + CSS + JS de la aplicación)

No sube nada del backend (`api.py`, `main.py`, `json_files/`, etc.).

**¿Y si quiero subir algo a mano?** Sigue funcionando: puedes subir por FTP/panel
en cualquier momento. El workflow es solo un atajo automático.

### Archivos que NO subes a IONOS

- Código del backend (`api.py`, `main.py`, etc.), `json_files/`, `.env`, `requirements.txt`, `Procfile`, `Dockerfile`.

### 3B. Si el frontend lo sirve tu amigo (mismo servidor que el API)

Si el backend corre en Docker en un servidor de tu amigo y quieres que también sirva el frontend desde ahí:

- Que monte la carpeta `app/` (y si quieres el `index.html` de la raíz) en un nginx u otro servidor web, **o**
- Que exponga el mismo contenedor sirviendo estáticos (el `api.py` ya puede servir la carpeta `app/` si se monta; si no, lo más simple es IONOS para el frontend y solo Docker para el API).

Recomendación: mantener el frontend en IONOS (ya lo tienes) y el API en Render o en Docker en casa de tu amigo.

---

## 4. Google Ads / AdSense

### Requisitos para aprobar AdSense

1. **Cookie Consent**: Ya incluido en `app/index.html` (banner de cookies).
2. **Política de Privacidad**: Ya incluida como modal en la app.
3. **ads.txt**: En la raíz de IONOS (junto a `index.html`) crea el archivo `ads.txt` con **una línea**:
   ```
   google.com, pub-7891666149137266, DIRECT, f08c47fec0942fa0
   ```
   (Ese es tu ID de editor; si AdSense te da otro formato, usa el que te indiquen.)
4. **Google Analytics** (opcional): Solo si quieres estadísticas con GA. En `app/js/app.js` busca `G-XXXXXXXXXX` y sustituye por tu ID de medición (ej. `G-QXF4YKPSMD`). Si no usas GA, puedes dejar el placeholder o quitar ese script.

### Pasos en AdSense

1. Entra en [Google AdSense](https://adsense.google.com).
2. Añade tu sitio `calculadorafantasy.com`.
3. Copia el código de verificación que te den y pégalo en el `<head>` de `index.html` y de `app/index.html`.
4. Espera la aprobación (suele tardar 1–3 días).

---

## 5. Base de datos MySQL (opcional)

### Opción A: Aiven (recomendado, gratis)

1. Crea cuenta en [aiven.io](https://aiven.io)
2. Crea un servicio MySQL (plan Free: 1 GB)
3. Ejecuta `db_schema.sql` para crear las tablas:
   ```bash
   mysql -h TU-HOST -P TU-PUERTO -u TU-USUARIO -p --ssl-mode=REQUIRED < db_schema.sql
   ```
4. Añade las credenciales como variables de entorno en Render/Railway:
   ```
   DB_HOST=mysql-xxx.aivencloud.com
   DB_PORT=12345
   DB_USER=avnadmin
   DB_PASSWORD=tu_password
   DB_NAME=calculadora_fantasy
   DB_SSL=true
   ```

### Opción B: Oracle Cloud Free Tier

1. Crea cuenta en [Oracle Cloud](https://cloud.oracle.com/free)
2. Crea una instancia MySQL Always Free
3. Mismo proceso de configuración

---

## 6. Desarrollo Local

### Iniciar el backend:

```bash
# Desde la raíz del proyecto
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

### Abrir el frontend:

Abre `app/index.html` directamente en el navegador, o sirve con:

```bash
python -m http.server 3000
# Luego abre http://localhost:3000/app/
```

El frontend detecta `localhost` y apunta automáticamente a `http://localhost:8000`.

---

## 7. Actualizar datos de jugadores

Los datos se actualizan automáticamente via GitHub Actions (tus scrapers).
El backend (`api.py`) lee los `json_files/` en cada request (con caché de 10 min).

Si quieres generar JSONs estáticos como backup:

```bash
python export_players_json.py --all
# Genera archivos en data/
```

---

## 8. Checklist pre-producción

- [ ] **Render**: Start command = `uvicorn api:app --host 0.0.0.0 --port $PORT`
- [ ] `API_BASE` en `app/js/app.js` apunta a tu API (ej. `https://knapsack-football-formations.onrender.com`)
- [ ] `ads.txt` en la raíz de IONOS con la línea de AdSense (pub-7891666149137266)
- [ ] Variable `FRONTEND_URL=https://www.calculadorafantasy.com` en Render (o en `docker.env` si usas Docker)
- [ ] Probar `curl https://TU-URL-API/api/health` → `{"status":"ok"}`
- [ ] Probar en el navegador: cargar jugadores y calcular 11s
- [ ] Cookie consent y política de privacidad visibles
- [ ] (Opcional) Google Analytics: sustituir `G-XXXXXXXXXX` en `app.js` por `G-QXF4YKPSMD` si usas GA
- [ ] (Opcional) MySQL y variables de BD si quieres guardar estadísticas
