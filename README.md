# Adrobot

## Зависимости

- Docker и Docker Compose
- Доступ к Keitaro и ключ Admin API

## Запуск

1. Скопируйте `backend/.env.example` в `backend/.env`.
2. В `backend/.env` укажите адрес Keitaro в `KEITARO_URL` и ключ в `KEITARO_API_KEY`.
3. В корне проекта запустите:

   ```bash
   docker compose up -d --build
   ```

4. Откройте [http://127.0.0.1:8080](http://127.0.0.1:8080).

При запуске backend миграции применяются автоматически. Для остановки используйте `docker compose down`.

## Миграции

Применить существующие миграции:

```bash
docker compose exec backend alembic upgrade head
```

После изменения моделей создайте и проверьте новую миграцию:

```bash
docker compose up -d --build backend
docker compose exec backend alembic revision --autogenerate -m "описание изменения"
docker compose cp backend:/app/migrations/versions/. backend/migrations/versions/
```

Проверьте созданный файл в `backend/migrations/versions/`, затем примените миграцию командой выше.
