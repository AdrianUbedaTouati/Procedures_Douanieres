# 🐛 Instrucciones para Debugging del Problema de Login

## ⚠️ PROBLEMA ACTUAL
Cuando inicias sesión, te redirige al home pero **sin la sesión iniciada** (apareces como no autenticado).

## ✅ LO QUE YA SE HIZO
1. ✅ Agregado `SESSION_SAVE_EVERY_REQUEST = True` en settings.py
2. ✅ Agregado `request.session.modified = True` y `session.save()` en login_view
3. ✅ Configurado SESSION_ENGINE para usar base de datos
4. ✅ Verificado middleware (orden correcto)
5. ✅ Verificado context_processors (auth está presente)
6. ✅ Agregado **logging detallado** en login_view y home_view

---

## 🔍 PRÓXIMOS PASOS - DEBUGGING

### OPCIÓN 1: Ver Logs del Servidor (RECOMENDADO)

He agregado logging detallado que te mostrará exactamente qué está pasando.

**Pasos:**

1. **Abre una terminal** y ejecuta el servidor Django:
   ```bash
   cd C:\Users\annnd\Desktop\Trabajo\TED
   python manage.py runserver
   ```

2. **Abre tu navegador** y ve a: `http://localhost:8000/login/`

3. **Intenta iniciar sesión** con tu usuario

4. **Observa la consola del servidor** - verás mensajes como estos:

   ```
   [LOGIN DEBUG] POST recibido. Username: tu_usuario
   [LOGIN DEBUG] Formulario válido. Usuario: tu_usuario (ID: 1)
   [LOGIN DEBUG] Session key ANTES de login: None
   [LOGIN DEBUG] Session key DESPUÉS de login: abc123xyz...
   [LOGIN DEBUG] User ID en sesión: 1
   [LOGIN DEBUG] User autenticado: True
   [LOGIN DEBUG] Remember me: SÍ (sesión dura 2 semanas)
   [LOGIN DEBUG] Sesión guardada forzadamente
   [LOGIN DEBUG] Session key FINAL: abc123xyz...
   [LOGIN DEBUG] Redirigiendo a: core:home

   [HOME DEBUG] Usuario autenticado: True/False ← **ESTO ES CRÍTICO**
   [HOME DEBUG] Usuario: tu_usuario (ID: 1)
   [HOME DEBUG] Session key: abc123xyz...
   [HOME DEBUG] User ID en sesión: 1
   ```

5. **Copia y pega TODO el output** del servidor aquí o en un archivo de texto

**QUÉ BUSCAR:**
- ✅ Si en LOGIN dice `User autenticado: True` pero en HOME dice `Usuario autenticado: False`, **la sesión se pierde en el redirect**
- ✅ Si `Session key` cambia entre LOGIN y HOME, hay un problema de cookies
- ✅ Si en LOGIN dice `Formulario NO válido`, hay un problema con las credenciales

---

### OPCIÓN 2: Ejecutar Script de Test

He creado un script que simula el flujo de login completo.

**Pasos:**

1. **Abre una terminal** y ejecuta:
   ```bash
   cd C:\Users\annnd\Desktop\Trabajo\TED
   python test_login_flow.py
   ```

2. **IMPORTANTE**: El script necesita tu contraseña real. Si no funciona, primero resetea la contraseña:
   ```bash
   python manage.py changepassword adrian
   ```
   (Crea una contraseña simple como `test1234` para testing)

3. Luego edita `test_login_flow.py` línea 59 y pon tu contraseña:
   ```python
   'password': 'test1234',  # ← Cambiar por tu contraseña real
   ```

4. Ejecuta el script de nuevo y **copia TODO el output**

---

### OPCIÓN 3: Verificar Cookies del Navegador

El problema podría ser que **el navegador no está guardando las cookies**.

**Pasos:**

1. **Abre tu navegador** (Chrome, Firefox, Edge)

2. **Abre DevTools** (F12)

3. **Ve a la pestaña "Application" (Chrome) o "Storage" (Firefox)**

4. **Mira "Cookies" > "http://localhost:8000"**

5. **Intenta hacer login**

6. **Después del login**, verifica si hay una cookie llamada `sessionid`:
   - ✅ Si existe: Copia su valor y expiration date
   - ❌ Si NO existe: **El servidor no está enviando la cookie** (problema de configuración)

7. **Haz refresh (F5)** en la página home

8. **Verifica si la cookie `sessionid` sigue ahí**:
   - ✅ Si sigue: El problema es que el servidor no está leyendo la cookie
   - ❌ Si desapareció: El navegador está borrando la cookie (problema de configuración de cookies)

**Toma un screenshot** de la sección de cookies y compártelo.

---

## 🔧 POSIBLES SOLUCIONES SEGÚN EL PROBLEMA

### CASO A: Cookie `sessionid` NO se crea

**Problema**: El servidor no está enviando la cookie al navegador.

**Solución**:
```bash
# Verifica que DEBUG=True
cat .env | grep DEBUG

# Si no está, agrégalo:
echo "DEBUG=True" >> .env
```

Luego **reinicia el servidor**.

---

### CASO B: Cookie `sessionid` se crea pero desaparece

**Problema**: El navegador está borrando la cookie.

**Soluciones posibles**:

1. **Limpia las cookies del navegador**:
   - Chrome: Ctrl+Shift+Delete > Cookies
   - Reinicia el navegador completamente

2. **Verifica que estés usando `localhost` o `127.0.0.1`**:
   - ✅ Correcto: `http://localhost:8000`
   - ✅ Correcto: `http://127.0.0.1:8000`
   - ❌ Incorrecto: `http://192.168.x.x:8000`

3. **Intenta en modo incógnito** (Ctrl+Shift+N):
   - Si funciona en incógnito, el problema es una extensión o configuración del navegador

---

### CASO C: Cookie existe pero servidor no la lee

**Problema**: El servidor tiene la cookie pero no está autenticando al usuario.

**Solución**: Agregar más configuraciones de sesión en `settings.py`:

```python
# Al final de settings.py
SESSION_COOKIE_NAME = 'sessionid'
SESSION_COOKIE_DOMAIN = None  # Usar dominio actual
SESSION_COOKIE_PATH = '/'
```

---

## 📋 CHECKLIST RÁPIDO

Verifica estas cosas:

- [ ] Servidor Django corriendo en `http://localhost:8000`
- [ ] DEBUG=True en `.env`
- [ ] ALLOWED_HOSTS incluye `localhost,127.0.0.1`
- [ ] Usuario existe y está activo (`email_verified=True`)
- [ ] Cookies habilitadas en el navegador
- [ ] No estás usando navegación privada (a menos que sea para testing)
- [ ] DevTools abierto mirando cookies

---

## 🆘 SI NADA FUNCIONA

Si después de probar todo esto el problema persiste, **necesito los logs completos**:

1. **Output del servidor Django** (OPCIÓN 1)
2. **Output del script test_login_flow.py** (OPCIÓN 2)
3. **Screenshot de las cookies del navegador** (OPCIÓN 3)

Con esa información podré identificar exactamente dónde se está rompiendo el flujo.

---

## 🎯 SIGUIENTE PASO INMEDIATO

**HAZ OPCIÓN 1 PRIMERO** - Es la más rápida y efectiva:

1. Ejecuta: `python manage.py runserver`
2. Intenta hacer login
3. Copia TODO el output del servidor
4. Compártelo conmigo

**Los logs te dirán exactamente qué está pasando.**

---

**Última actualización**: Agregado logging detallado en `authentication/views.py` (login_view) y `core/views.py` (home_view)
