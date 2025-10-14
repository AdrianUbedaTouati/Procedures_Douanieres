# TenderAI Platform - Guía de Despliegue

Ver README.md para instrucciones completas de instalación.

## Desarrollo

1. Clonar repositorio
2. Crear entorno virtual
3. Instalar dependencias: pip install -r requirements.txt
4. Configurar .env
5. python manage.py migrate
6. python manage.py createsuperuser
7. python manage.py runserver

## Producción

- Usar PostgreSQL
- Configurar Gunicorn + Nginx
- Activar SSL con Let's Encrypt
- DEBUG=False en .env
