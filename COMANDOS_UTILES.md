# 🔧 Comandos Útiles - TenderAI Platform

Referencia rápida de comandos para desarrollo y administración.

---

## 🚀 Setup Inicial

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de entorno
cp .env.example .env
# Editar .env con tus valores

# Crear directorios de datos
mkdir -p data/xml data/records data/index/chroma logs
```

---

## 🗄️ Base de Datos

### **Migraciones**

```bash
# Crear migraciones para todas las apps
python manage.py makemigrations

# Crear migraciones para una app específica
python manage.py makemigrations authentication
python manage.py makemigrations company
python manage.py makemigrations tenders
python manage.py makemigrations chat

# Aplicar migraciones
python manage.py migrate

# Ver migraciones aplicadas
python manage.py showmigrations

# Revertir una migración
python manage.py migrate authentication 0001

# Ver SQL de una migración
python manage.py sqlmigrate authentication 0001
```

### **Usuarios**

```bash
# Crear superusuario
python manage.py createsuperuser

# Cambiar contraseña de un usuario
python manage.py changepassword usuario@example.com

# Shell interactivo de Django
python manage.py shell

# Dentro del shell:
from authentication.models import User
user = User.objects.get(email='usuario@example.com')
user.email_verified = True
user.save()
```

### **Resetear Base de Datos** (¡CUIDADO!)

```bash
# Eliminar base de datos SQLite
rm db.sqlite3

# Eliminar todas las migraciones
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Recrear migraciones
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

---

## 🏃 Servidor de Desarrollo

```bash
# Ejecutar servidor
python manage.py runserver

# Ejecutar en puerto diferente
python manage.py runserver 8080

# Ejecutar accesible desde red
python manage.py runserver 0.0.0.0:8000

# Ejecutar con configuración específica
DJANGO_SETTINGS_MODULE=TenderAI.settings_dev python manage.py runserver
```

---

## 📦 Archivos Estáticos

```bash
# Colectar archivos estáticos (producción)
python manage.py collectstatic

# Sin confirmación
python manage.py collectstatic --noinput

# Limpiar archivos estáticos antiguos
python manage.py collectstatic --clear
```

---

## 🤖 Agent_IA - Gestión de Licitaciones

### **Descarga de XMLs desde TED**

```bash
# Descargar licitaciones de los últimos 7 días
python manage.py download_tenders --days 7

# Descargar con filtros específicos
python manage.py download_tenders --days 30 --country ESP --cpv 7226

# Ver opciones disponibles
python manage.py download_tenders --help
```

### **Ingesta de XMLs**

```bash
# Ingestar todos los XMLs pendientes
python manage.py ingest_tenders

# Ingestar un XML específico
python manage.py ingest_tenders --file data/xml/123456-2025.xml

# Modo verbose (más información)
python manage.py ingest_tenders --verbose
```

### **Construcción de Índice Vectorial**

```bash
# Construir índice completo desde cero
python manage.py build_index

# Reconstruir índice (elimina el anterior)
python manage.py build_index --rebuild

# Añadir solo nuevos documentos
python manage.py build_index --incremental
```

### **Generación de Recomendaciones**

```bash
# Generar recomendaciones para todos los usuarios
python manage.py generate_recommendations

# Para un usuario específico
python manage.py generate_recommendations --user usuario@example.com

# Solo usuarios con perfil completo
python manage.py generate_recommendations --complete-only
```

### **Estadísticas**

```bash
# Ver estadísticas del sistema
python manage.py stats

# Estadísticas detalladas
python manage.py stats --detailed
```

---

## 🔄 Celery - Tareas Asíncronas

### **Ejecutar Workers**

```bash
# Worker básico
celery -A TenderAI worker -l info

# Worker en Windows (solo ejecutor)
celery -A TenderAI worker -l info -P solo

# Worker con auto-reload (desarrollo)
celery -A TenderAI worker -l info --autoreload

# Worker con más concurrencia
celery -A TenderAI worker -l info --concurrency=8

# Worker específico para colas
celery -A TenderAI worker -Q tenders,notifications -l info
```

### **Ejecutar Beat Scheduler**

```bash
# Beat básico
celery -A TenderAI beat -l info

# Beat con scheduler persistente
celery -A TenderAI beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### **Monitoreo**

```bash
# Flower (web UI para monitoreo)
celery -A TenderAI flower

# Acceder a: http://localhost:5555

# Ver tareas activas
celery -A TenderAI inspect active

# Ver tareas programadas
celery -A TenderAI inspect scheduled

# Ver estadísticas
celery -A TenderAI inspect stats

# Purgar todas las tareas
celery -A TenderAI purge
```

### **Control de Tareas**

```bash
# Cancelar una tarea
celery -A TenderAI revoke <task_id>

# Cancelar con terminación
celery -A TenderAI revoke <task_id> --terminate

# Reiniciar workers
celery -A TenderAI control pool_restart
```

---

## 🧪 Testing

```bash
# Ejecutar todos los tests
python manage.py test

# Tests de una app específica
python manage.py test authentication
python manage.py test tenders

# Tests con verbosidad
python manage.py test --verbosity=2

# Tests paralelos
python manage.py test --parallel

# Tests con coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Genera reporte HTML en htmlcov/

# Pytest (si instalado)
pytest
pytest tests/tenders/
pytest -v  # verbose
pytest -x  # stop on first failure
pytest --cov=tenders  # con cobertura
```

---

## 🐞 Debug y Logging

```bash
# Ver logs en tiempo real
tail -f logs/tenderai.log

# Ver logs de Celery
tail -f logs/celery.log

# Ver tracking de tokens LLM
tail -f logs/tokens.jsonl

# Buscar errores en logs
grep ERROR logs/tenderai.log

# Ver logs de hoy
grep "$(date +%Y-%m-%d)" logs/tenderai.log
```

---

## 📊 Admin de Django

```bash
# Abrir admin
# Navegar a: http://localhost:8000/admin/

# Crear grupos y permisos
python manage.py shell
from django.contrib.auth.models import Group, Permission
group = Group.objects.create(name='Empresa')
# Añadir permisos...
```

---

## 🔍 Django Shell - Comandos Útiles

```bash
# Abrir shell
python manage.py shell

# O usar ipython si está instalado
python manage.py shell -i ipython
```

### **Dentro del shell:**

```python
# Importar modelos
from authentication.models import User
from company.models import CompanyProfile
from tenders.models import Tender, TenderRecommendation
from chat.models import ChatSession, ChatMessage

# Consultas básicas
User.objects.all()
User.objects.count()
User.objects.filter(email_verified=True)

# Crear usuario de prueba
user = User.objects.create_user(
    username='test',
    email='test@example.com',
    password='Test123!'
)
user.email_verified = True
user.save()

# Crear perfil de empresa
profile = CompanyProfile.objects.create(
    user=user,
    company_name='Test Company',
    size='mediana',
    preferred_cpv_codes=['72267100'],
    preferred_regions=['ES300'],
    budget_range={'min_eur': 200000, 'max_eur': 1000000},
    is_complete=True
)

# Contar licitaciones
Tender.objects.count()
Tender.objects.filter(budget_amount__gte=500000).count()

# Ver recomendaciones de un usuario
recs = TenderRecommendation.objects.filter(user=user).order_by('-score_total')[:5]
for rec in recs:
    print(f"{rec.tender.title}: {rec.score_total}/100")

# Probar Agent_IA
from agent_ia_core.agent_graph import create_agent
agent = create_agent()
result = agent.query("¿Cuál es el presupuesto de SAP?")
print(result['answer'])

# Salir del shell
exit()
```

---

## 🔐 Seguridad

```bash
# Verificar configuración de seguridad
python manage.py check --deploy

# Generar nuevo SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Verificar URLs
python manage.py show_urls  # (requiere django-extensions)
```

---

## 📦 Gestión de Dependencias

```bash
# Instalar nueva dependencia
pip install nombre-paquete

# Actualizar requirements.txt
pip freeze > requirements.txt

# Verificar paquetes desactualizados
pip list --outdated

# Actualizar un paquete
pip install --upgrade nombre-paquete

# Instalar desde requirements.txt
pip install -r requirements.txt

# Desinstalar un paquete
pip uninstall nombre-paquete
```

---

## 🚀 Producción

### **Gunicorn**

```bash
# Ejecutar Gunicorn
gunicorn TenderAI.wsgi:application --bind 0.0.0.0:8000

# Con workers
gunicorn TenderAI.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Con logs
gunicorn TenderAI.wsgi:application --bind 0.0.0.0:8000 --workers 4 --access-logfile logs/access.log --error-logfile logs/error.log

# En background
gunicorn TenderAI.wsgi:application --bind 0.0.0.0:8000 --daemon
```

### **Supervisord (para mantener servicios corriendo)**

```bash
# Instalar supervisor
sudo apt-get install supervisor

# Configurar en /etc/supervisor/conf.d/tenderai.conf
# Ver ejemplo en docs/deployment/supervisor.conf

# Comandos
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start tenderai
sudo supervisorctl stop tenderai
sudo supervisorctl restart tenderai
sudo supervisorctl status
```

---

## 📁 Gestión de Archivos

```bash
# Ver tamaño de directorios
du -sh data/
du -sh media/
du -sh staticfiles/

# Limpiar archivos temporales
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -delete

# Backup de base de datos SQLite
cp db.sqlite3 backups/db_$(date +%Y%m%d).sqlite3

# Backup de PostgreSQL
pg_dump tenderai_db > backups/db_$(date +%Y%m%d).sql

# Restaurar PostgreSQL
psql tenderai_db < backups/db_20250114.sql
```

---

## 🔄 Git

```bash
# Inicializar repositorio
git init

# Añadir archivos
git add .

# Commit
git commit -m "Initial commit"

# Crear rama
git checkout -b feature/nueva-funcionalidad

# Ver cambios
git status
git diff

# Historial
git log --oneline --graph

# Revertir cambios
git checkout -- archivo.py
git reset --hard HEAD
```

---

## 💡 Tips y Trucos

### **Crear fixture de datos**

```bash
# Exportar datos
python manage.py dumpdata authentication.User --indent 2 > fixtures/users.json
python manage.py dumpdata tenders.Tender --indent 2 > fixtures/tenders.json

# Importar datos
python manage.py loaddata fixtures/users.json
python manage.py loaddata fixtures/tenders.json
```

### **Ver queries SQL ejecutadas**

```python
# En el shell
from django.db import connection
from tenders.models import Tender

# Ejecutar query
Tender.objects.filter(budget_amount__gte=500000)

# Ver SQL
print(connection.queries)
```

### **Performance profiling**

```bash
# Instalar django-silk
pip install django-silk

# Añadir a INSTALLED_APPS y middleware
# Visitar: http://localhost:8000/silk/
```

---

## 🆘 Troubleshooting

### **Error: ModuleNotFoundError**

```bash
# Verificar que el entorno virtual está activado
which python  # Linux/Mac
where python  # Windows

# Reinstalar dependencias
pip install -r requirements.txt
```

### **Error: Connection refused (Redis)**

```bash
# Verificar que Redis está corriendo
redis-cli ping
# Respuesta esperada: PONG

# Iniciar Redis
# Windows: redis-server.exe
# Linux: sudo systemctl start redis
```

### **Error: Migraciones conflictivas**

```bash
# Ver migraciones conflictivas
python manage.py showmigrations

# Crear migración de merge
python manage.py makemigrations --merge
```

### **Error: Ports already in use**

```bash
# Windows: Encontrar proceso en puerto 8000
netstat -ano | findstr :8000
# Matar proceso
taskkill /PID <pid> /F

# Linux: Encontrar y matar proceso
lsof -ti:8000 | xargs kill -9
```

---

## 📚 Recursos Adicionales

```bash
# Django docs
https://docs.djangoproject.com/

# Celery docs
https://docs.celeryproject.org/

# LangChain docs
https://python.langchain.com/

# Bootstrap docs
https://getbootstrap.com/docs/
```

---

**¡Guarda este archivo como referencia rápida! 📖**
