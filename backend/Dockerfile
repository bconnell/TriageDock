FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && groupadd -r app && useradd -r -g app app
COPY backend/ ./
COPY --from=frontend-build /frontend/dist/index.html /app/templates/ui/index.html
COPY --from=frontend-build /frontend/dist/assets/ /app/static/ui/assets/
RUN DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "30"]
