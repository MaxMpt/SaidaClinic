# Doc Saya — Django + PostgreSQL

Кабинет косметолога для Telegram Mini App. База — **только PostgreSQL**.
На сервере Postgres поднимается **отдельным контейнером**.

## Как вы хотели: локально → Git → сервер

1. Распакуйте архив, это уже готовый Django-проект.
2. Положите его в Git и запушьте.
3. На сервере `git clone` и поднимите Postgres контейнером, Django — рядом.

`.env` в Git **не коммитится**.

---

## 1. У себя на машине

Нужны Python 3.10+ и Docker (для Postgres).

```bash
cd docsaya-django
cp .env.example .env
```

В `.env` для локалки можно оставить `DEBUG=1`, `ALLOWED_HOSTS=*`, пароль Postgres любой.
`DATABASE_URL` должен смотреть на `127.0.0.1:5432` — это порт контейнера.

```bash
docker compose up -d db
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py createsuperuser
python manage.py runserver
```

Кабинет: корень сайта. Админка: `/django-admin/`.

Проверка, что контейнер жив:

```bash
docker compose ps
docker compose logs -f db
```

## 2. Git

```bash
git init
git add .
git commit -m "Doc Saya Django"
git remote add origin git@github.com:YOU/docsaya.git
git push -u origin main
```

В репозитории будут код, `docker-compose.yml` и `.env.example`. Секреты остаются только в `.env` на машине и на сервере.

## 3. Сервер

Docker + git + Python (если Django не в контейнере).

```bash
git clone git@github.com:YOU/docsaya.git
cd docsaya
cp .env.example .env
nano .env
```

В `.env` на проде:

| Ключ | Значение |
|---|---|
| `SECRET_KEY` | длинная случайная строка |
| `DEBUG` | `0` |
| `ALLOWED_HOSTS` | ваш домен |
| `CSRF_TRUSTED_ORIGINS` | `https://ваш-домен` |
| `POSTGRES_PASSWORD` | тот же пароль, что в `DATABASE_URL` |
| `DATABASE_URL` | `postgres://docsaya:ПАРОЛЬ@127.0.0.1:5432/docsaya` |
| `TELEGRAM_BOT_TOKEN` | токен BotFather |
| `MINI_APP_URL` | `https://ваш-домен` без `/` на конце |
| `ADMIN_TELEGRAM_ID` | `6935237776` |

### Postgres — отдельный контейнер

```bash
docker compose up -d db
```

Контейнер `docsaya-db`, данные в volume `docsaya_pg`. Порт `5432` слушает только localhost сервера, снаружи базы нет.

Дальше Django на хосте:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py setwebhook
gunicorn docsaya.wsgi:application --bind 127.0.0.1:8000 --workers 2
```

Либо всё в Docker (Postgres по-прежнему отдельный сервис):

```bash
docker compose --profile full up -d --build
```

Тогда веб ходит в базу по имени хоста `db`, не через `127.0.0.1`.

Обновление с Git:

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
# перезапуск gunicorn / systemd
```

Контейнер базы при `git pull` не трогайте. Volume живёт отдельно.

## 4. Nginx (https)

```nginx
server {
  listen 443 ssl;
  server_name your-domain.com;
  location /static/ { alias /path/to/docsaya-django/staticfiles/; }
  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}
```

## 5. Telegram

1. BotFather → Mini App URL = `MINI_APP_URL`
2. `python manage.py setwebhook` — вебхук на `https://домен/api/telegram`
3. `/start` пишет клиента в `clinic_client`. Сая (id `6935237776`) видит вкладку Кабинет.

## 6. Состав

- `clinic/` — модели, слоты, запись, Telegram
- `docker-compose.yml` — сервис `db` (Postgres 16) и опционально `web`
- `static/clinic/` — Mini App
- `/django-admin/` — услуги, записи, клиенты, витрина
