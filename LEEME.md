# 🚀 TenderAI Platform - LÉEME

## 📌 ¿Qué hay en este directorio?

Este es el **proyecto integrado completo** que fusiona:
- ✅ **BasePaginas** (plataforma Django con autenticación)
- ✅ **Agent_IA** (sistema RAG inteligente para licitaciones)

---

## 📂 Archivos de Documentación

| Archivo | Descripción |
|---------|-------------|
| **README.md** | Documentación principal (inglés) |
| **LEEME.md** | Este archivo (español) |
| **RESUMEN_EJECUTIVO.md** | Resumen de alto nivel del proyecto |
| **ARQUITECTURA_TECNICA.md** | Arquitectura detallada del sistema |
| **GUIA_IMPLEMENTACION.md** | Paso a paso para implementar |
| **COMANDOS_UTILES.md** | Referencia rápida de comandos |
| **DIAGRAMA_ARQUITECTURA.txt** | Diagrama visual ASCII |
| **requirements.txt** | Dependencias de Python |
| **.env.example** | Variables de entorno (plantilla) |
| **.gitignore** | Archivos a ignorar en Git |

---

## 🎯 ¿Por Dónde Empezar?

### **1. Lee primero:**
📖 **RESUMEN_EJECUTIVO.md** - Para entender qué es el proyecto

### **2. Entiende la arquitectura:**
🏗️ **ARQUITECTURA_TECNICA.md** - Diseño completo del sistema
🎨 **DIAGRAMA_ARQUITECTURA.txt** - Visualización ASCII

### **3. Implementa paso a paso:**
🛠️ **GUIA_IMPLEMENTACION.md** - 10 fases detalladas
📝 **COMANDOS_UTILES.md** - Comandos de terminal

---

## ⚡ Quick Start (Resumen Ultra Rápido)

```bash
# 1. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 2. Instalar Django básico
pip install Django==5.2.6 python-decouple

# 3. Crear proyecto Django
django-admin startproject TenderAI .

# 4. Configurar .env
cp .env.example .env
# Editar .env con tus API keys

# 5. Copiar apps desde BasePaginas
# (Ver GUIA_IMPLEMENTACION.md Fase 2)

# 6. Migrar base de datos
python manage.py migrate

# 7. Crear superusuario
python manage.py createsuperuser

# 8. Ejecutar servidor
python manage.py runserver
```

---

## 📊 Estructura del Proyecto (Final)

```
TenderAI_Platform/
│
├── 📚 DOCUMENTACIÓN (6 archivos principales)
│   ├── README.md
│   ├── LEEME.md (español)
│   ├── RESUMEN_EJECUTIVO.md
│   ├── ARQUITECTURA_TECNICA.md
│   ├── GUIA_IMPLEMENTACION.md
│   ├── COMANDOS_UTILES.md
│   └── DIAGRAMA_ARQUITECTURA.txt
│
├── ⚙️ CONFIGURACIÓN
│   ├── requirements.txt
│   ├── .env.example
│   ├── .gitignore
│   └── .venv/  (crear después)
│
├── 🎯 APPS DJANGO (crear después)
│   ├── authentication/      # Login, registro
│   ├── core/               # Templates base
│   ├── company/            # Perfil de empresa
│   ├── tenders/            # Gestión de licitaciones
│   ├── chat/               # Chatbot
│   └── notifications/      # Alertas
│
├── 🤖 AGENT_IA CORE (copiar después)
│   └── agent_ia_core/
│       ├── agent_graph.py
│       ├── retriever.py
│       ├── recommendation_engine.py
│       └── ... (15+ archivos)
│
├── 🗄️ DATOS (crear después)
│   └── data/
│       ├── xml/            # XMLs descargados
│       ├── records/        # JSONs normalizados
│       └── index/chroma/   # Índice vectorial
│
├── 🎨 FRONTEND (crear después)
│   ├── static/             # CSS, JS globales
│   ├── media/              # Uploads de usuarios
│   └── templates/          # Templates globales
│
└── 🐍 DJANGO (crear después)
    └── TenderAI/
        ├── settings.py
        ├── urls.py
        ├── wsgi.py
        └── celery.py
```

---

## 🧩 Componentes Principales

### **1. Authentication App** (Copiada de BasePaginas)
- ✅ Login con email o username
- ✅ Registro con verificación de email
- ✅ Recuperación de contraseña
- ✅ Modelo User extendido

### **2. Company App** (Nueva)
- 🆕 Perfil de empresa personalizado
- 🆕 CPV codes, NUTS regions
- 🆕 Rango presupuestario
- 🆕 Portfolio de proyectos

### **3. Tenders App** (Nueva)
- 🆕 Modelo Tender (licitaciones)
- 🆕 Sistema de recomendaciones
- 🆕 Búsqueda avanzada
- 🆕 Dashboard con TOP N

### **4. Chat App** (Nueva)
- 🆕 Chatbot con Agent_IA
- 🆕 Historial de conversaciones
- 🆕 API REST para mensajes
- 🆕 Modal flotante en UI

### **5. Agent_IA Core** (Copiado de Agent_IA)
- 🤖 Sistema RAG con LangGraph
- 🤖 Parser de XMLs eForms
- 🤖 Índice vectorial ChromaDB
- 🤖 Motor de recomendaciones

---

## 🔑 Variables de Entorno Importantes

```env
# Django
SECRET_KEY=tu-secret-key-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# LLM
LLM_PROVIDER=google  # o "openai"
GOOGLE_API_KEY=tu-api-key-aqui

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-password

# Authentication
EMAIL_VERIFICATION_REQUIRED=True
LOGIN_ATTEMPTS_ENABLED=False
```

Ver `.env.example` para configuración completa.

---

## 📋 Checklist de Implementación

- [ ] **Fase 1**: Setup Django base
- [ ] **Fase 2**: App authentication
- [ ] **Fase 3**: App core
- [ ] **Fase 4**: App company
- [ ] **Fase 5**: Integrar agent_ia_core
- [ ] **Fase 6**: App tenders
- [ ] **Fase 7**: App chat
- [ ] **Fase 8**: Templates y diseño
- [ ] **Fase 9**: Celery y tareas
- [ ] **Fase 10**: Testing y deploy

Ver **GUIA_IMPLEMENTACION.md** para detalles de cada fase.

---

## 🎨 Tecnologías Usadas

**Backend:**
- Django 5.2.6
- PostgreSQL / SQLite
- Celery + Redis

**IA/ML:**
- LangChain 0.3.14
- LangGraph 0.2.63
- Google Gemini 2.5 Flash
- ChromaDB

**Frontend:**
- Bootstrap 5.3
- Alpine.js
- Chart.js

---

## 📊 Estimación de Tiempos

| Fase | Tiempo Estimado |
|------|----------------|
| Fase 1: Setup Base | 3-4 horas |
| Fase 2: Authentication | 2 horas |
| Fase 3: Core | 2 horas |
| Fase 4: Company | 2-3 horas |
| Fase 5: Agent_IA | 4-5 horas |
| Fase 6: Tenders | 6-8 horas |
| Fase 7: Chat | 4-5 horas |
| Fase 8: Templates | 4-6 horas |
| Fase 9: Celery | 2-3 horas |
| Fase 10: Deploy | 4-6 horas |
| **TOTAL** | **25-35 horas** |

---

## 🆘 ¿Problemas?

### **No funciona algo?**
1. Revisa **COMANDOS_UTILES.md** sección "Troubleshooting"
2. Verifica que el entorno virtual está activado
3. Verifica que todas las dependencias están instaladas
4. Revisa los logs: `tail -f logs/tenderai.log`

### **Dudas sobre arquitectura?**
- Lee **ARQUITECTURA_TECNICA.md**
- Mira **DIAGRAMA_ARQUITECTURA.txt**

### **No sabes qué comando usar?**
- Consulta **COMANDOS_UTILES.md**

---

## 🎓 Consejos para el Desarrollo

1. **Implementa fase por fase**: No intentes hacer todo a la vez
2. **Prueba cada componente**: Asegúrate que funciona antes de continuar
3. **Git commits frecuentes**: Guarda tu progreso regularmente
4. **Usa datos de prueba**: Crea fixtures para testing
5. **Lee la documentación**: Está muy detallada por algo :)

---

## 📞 Información de Soporte

Este proyecto es una **integración personalizada** de:
- **BasePaginas** (Django template)
- **Agent_IA** (sistema RAG)

Para problemas específicos:
- **Django**: https://docs.djangoproject.com/
- **LangChain**: https://python.langchain.com/
- **Celery**: https://docs.celeryproject.org/

---

## 📝 Notas Importantes

### **Lo que SÍ está listo:**
✅ Arquitectura completa diseñada
✅ Documentación exhaustiva (6 documentos)
✅ Requirements.txt con todas las dependencias
✅ Configuración .env.example
✅ Guía paso a paso de implementación
✅ Comandos útiles de referencia

### **Lo que FALTA implementar:**
❌ Crear proyecto Django
❌ Copiar apps de BasePaginas
❌ Integrar Agent_IA
❌ Crear nuevas apps (company, tenders, chat)
❌ Crear templates
❌ Configurar Celery

### **Siguiente paso:**
🚀 Seguir **GUIA_IMPLEMENTACION.md** desde la Fase 1

---

## 🎯 Objetivo Final

Una **plataforma SaaS profesional** que permita a empresas:
- ✅ Encontrar licitaciones relevantes automáticamente
- ✅ Obtener recomendaciones personalizadas con probabilidad de éxito
- ✅ Consultar información mediante chatbot inteligente
- ✅ Gestionar su pipeline de oportunidades
- ✅ Recibir alertas de nuevas licitaciones

---

## 🌟 ¡Mucha suerte con la implementación!

Sigue la guía paso a paso y tendrás tu plataforma funcionando pronto.

**Recuerda:** La documentación está muy detallada. ¡Úsala! 📖

---

**Última actualización:** 2025-10-14
**Versión de documentación:** 1.0.0
**Estado:** Diseño completo - Listo para implementar
