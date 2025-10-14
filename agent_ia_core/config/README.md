# Configuración del Sistema

Esta carpeta contiene toda la configuración personalizable del sistema.

## 📁 Archivos

### `.env.example` → `.env`
**Propósito:** Variables de entorno (API keys, proveedor LLM)

**Uso:**
```bash
# 1. Copiar plantilla
cp .env.example .env

# 2. Editar .env y añadir tus credenciales
LLM_PROVIDER=google
GOOGLE_API_KEY=tu_api_key_aqui
```

---

### `company_profile.json`
**Propósito:** Perfil de tu empresa para el motor de recomendaciones

**Secciones:**
- `company_info`: Información básica (nombre, tamaño, facturación)
- `capabilities`: Capacidades técnicas, tecnologías, certificaciones
- `experience`: Portfolio de proyectos, experiencia sector público
- `bidding_preferences`: Preferencias de licitación (CPV, presupuesto, regiones)
- `competitive_analysis`: Competidores, ventajas, debilidades
- `risk_factors`: Capacidad financiera, disponibilidad equipo

**Cómo personalizar:**
1. Abrir `company_profile.json`
2. Rellenar con información real de tu empresa
3. Ajustar `preferred_cpv_codes` según tu especialización
4. Definir `budget_range` según tu capacidad
5. Listar `previous_clients` y `relevant_projects`

**Impacto:**
El motor de recomendaciones usa este perfil para calcular el TOP 5 de licitaciones más adecuadas.

---

### `prompts_config.yaml`
**Propósito:** Personalizar todos los prompts del agente sin modificar código

**Secciones configurables:**

#### 1. System Prompt Principal
```yaml
system_prompt:
  role: "Eres un asistente especializado en licitaciones..."
  behavior_rules:
    - "Responde SOLO basándote en el contexto"
    - "NUNCA inventes información"
  citation_rules:
    format: "[ID | sección | archivo]"
```

#### 2. Grading Prompt
```yaml
grading_prompt:
  relevance_criteria:
    - "El documento contiene información directamente relacionada"
    - "El contenido es específico y no genérico"
```

#### 3. Parámetros de Generación
```yaml
generation_params:
  temperature: 0.0          # Determinismo
  max_tokens: 1000
```

**Cuándo modificar:**
- Para cambiar el tono del asistente (formal, informal)
- Para ajustar criterios de relevancia
- Para cambiar formato de citas
- Para personalizar mensajes de error

---

### `recommendation_config.yaml`
**Propósito:** Configurar el motor de recomendaciones (pesos, scoring, criterios)

**Secciones configurables:**

#### 1. Pesos de Categorías (deben sumar 1.0)
```yaml
category_weights:
  technical: 0.30       # 30% - Compatibilidad técnica
  budget: 0.25          # 25% - Presupuesto
  geographic: 0.15      # 15% - Geografía
  experience: 0.20      # 20% - Experiencia
  competition: 0.10     # 10% - Competencia
```

**Ejemplo de ajuste:**
Si tu empresa prioriza presupuesto sobre geografía:
```yaml
category_weights:
  technical: 0.30
  budget: 0.35          # Aumentado de 0.25
  geographic: 0.05      # Reducido de 0.15
  experience: 0.20
  competition: 0.10
```

#### 2. Scoring Técnico
```yaml
technical_scoring:
  cpv_match:
    score: 50           # Puntos por CPV alineado
  keyword_match:
    score_per_keyword: 10
    max_score: 30
```

#### 3. Scoring Presupuestario
```yaml
budget_scoring:
  in_range:
    score: 100          # Presupuesto perfecto
  below_minimum:
    calculation: "ratio * 50"
```

#### 4. Probabilidad de Éxito
```yaml
success_probability:
  penalties:
    per_warning: 5                  # -5% por cada advertencia
    financial_capacity_low: 10      # -10% si capacidad baja
  company_size_adjustment:
    pequeña: 0.85       # -15%
    mediana: 1.00       # Sin ajuste
    grande: 1.10        # +10%
```

**Cuándo modificar:**
- Para cambiar prioridades (más peso a experiencia vs presupuesto)
- Para ajustar scoring según tu modelo de negocio
- Para personalizar advertencias y penalizaciones
- Para calibrar probabilidades de éxito

---

## 🔄 Workflow de Personalización

### 1. Setup Inicial
```bash
# Copiar .env
cp config/.env.example .env
nano .env  # Añadir API key
```

### 2. Configurar Empresa
```bash
nano config/company_profile.json
# Rellenar:
# - Nombre empresa
# - Capacidades técnicas
# - Presupuesto objetivo
# - Regiones preferidas
```

### 3. (Opcional) Ajustar Prompts
```bash
nano config/prompts_config.yaml
# Modificar solo si quieres personalizar tono o formato
```

### 4. (Opcional) Ajustar Recomendaciones
```bash
nano config/recommendation_config.yaml
# Modificar pesos según tus prioridades
```

### 5. Probar
```bash
# Probar recomendaciones
python -m src.recommendation_engine -n 5

# Probar consultas
python -m src.serve_cli
```

---

## ⚠️ Advertencias

### No commitear `.env`
El archivo `.env` contiene API keys sensibles. **NUNCA** hacer commit de este archivo.

✅ Commiteado: `.env.example` (plantilla)
❌ No commitear: `.env` (con credenciales)

### Validación de configuración
Los archivos YAML y JSON son validados al inicio:
- YAML: Sintaxis correcta
- JSON: Esquema válido
- Pesos: Deben sumar 1.0

Si hay error, el sistema lo indicará al arrancar.

---

## 📝 Ejemplos de Personalización

### Empresa de Consultoría SAP
```json
// company_profile.json
{
  "bidding_preferences": {
    "preferred_cpv_codes": ["72267100", "72262000"],
    "budget_range": {"min_eur": 500000, "max_eur": 5000000}
  }
}
```

```yaml
# recommendation_config.yaml
category_weights:
  technical: 0.40       # +10% (especialización)
  budget: 0.25
  geographic: 0.10      # -5% (menos importante)
  experience: 0.20
  competition: 0.05     # -5% (menos importante)
```

### Startup Pequeña
```json
// company_profile.json
{
  "company_info": {
    "size": "pequeña",
    "annual_revenue_eur": 500000
  },
  "bidding_preferences": {
    "budget_range": {"min_eur": 50000, "max_eur": 500000}
  }
}
```

```yaml
# recommendation_config.yaml
budget_scoring:
  below_minimum:
    calculation: "ratio * 70"  # Más tolerante con presupuestos pequeños
```

---

## 🔗 Referencias

- Ver [ESTRUCTURA_PROYECTO.md](../ESTRUCTURA_PROYECTO.md) para arquitectura general
- Ver [docs/TECHNICAL_GUIDE.md](../docs/TECHNICAL_GUIDE.md) para detalles técnicos
- Ver [README.md](../README.md) para guía de uso

---

**Última actualización:** 2025-10-14
