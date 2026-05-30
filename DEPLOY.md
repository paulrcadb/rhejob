# Deploy em VPS

## Rodando direto no Linux

```bash
cd job-analyzer
cp .env.example .env
chmod +x start.sh
./start.sh
```

A API e o frontend servido pelo FastAPI ficam disponíveis em:

```text
http://SEU_IP:8000/
http://SEU_IP:8000/app/
```

Para publicar o frontend na Hostinger em `rhejobs.com.br/app`, envie o conteúdo da pasta `frontend/` para a pasta `/app/` da hospedagem. Ajuste em `frontend/config.js`:

```js
window.RHJOB_API_URL = "https://SEU-BACKEND-RENDER.onrender.com";
```

## Variáveis importantes

```text
API_URL=https://SEU-BACKEND-RENDER.onrender.com
DATABASE_URL=sqlite:///data/database.db
APP_BASE_PATH=/app
CORS_ORIGINS=*
COOKIE_SAMESITE=lax
COOKIE_SECURE=false
```

Como frontend e API estarão em domínios diferentes usando HTTPS e cookie de login, use:

```text
COOKIE_SAMESITE=none
COOKIE_SECURE=true
```

Em produção, prefira trocar `CORS_ORIGINS=*` pelo domínio real do frontend.

## Rodando com Docker

```bash
docker build -t rhejobs-api .
docker run -d \
  --name rhejobs-api \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/logs:/app/logs \
  rhejobs-api
```

## Nginx como proxy reverso

Exemplo para expor a API em `api.rhejobs.com.br`:

```nginx
server {
    listen 80;
    server_name api.rhejobs.com.br;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
