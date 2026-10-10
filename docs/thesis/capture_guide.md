# Guía de capturas del prototipo

Instrucciones para producir las Figuras 8 a 14 del protocolo de forma reproducible. Sigue los pasos en orden: el orden evita repetir conversaciones y que una captura contamine a la siguiente. Las fichas de cada figura ([`figures/`](figures/)) explican qué demuestra cada una; aquí solo está el procedimiento.

Tiempo estimado: 10 minutos con la opción automática, o de 60 a 90 minutos a mano.

## Estado actual

| Figura | Estado |
|---|---|
| 8 a 14 | **Capturadas** el 10 de octubre de 2026 en `figures/capturas/`, sin advertencias (ver `capture_report.json`) |
| 0.1 y 0.2 | **Hechos** el 10 de octubre de 2026: `SEED_DOCUMENTS_DIR=/app/data/sin-semilla` y 15 documentos indexados |
| 10, 11 y 13 | **Repetidas** el 10 de octubre de 2026 tras corregir las sugerencias de la pantalla inicial |

## Opción A · Automática (recomendada)

El script [`tools/capture_figures.cjs`](tools/capture_figures.cjs) hace todo lo que describe la opción B:
- abre Chrome con las condiciones de la sección 0.4;
- registra cuentas de demostración ficticias;
- escribe las conversaciones exactas;
- espera la respuesta real;
- guarda cada PNG con su nombre definitivo;
- comprueba fuentes, fundamentación y número de documentos.

1. Haz a mano los pasos 0.1 y 0.2 (son cambios de datos del sistema y no se automatizan).
2. Desde la raíz del repositorio:
   ```bash
   npm install --no-save --prefix docs/thesis/tools puppeteer-core
   NODE_PATH=docs/thesis/tools/node_modules node docs/thesis/tools/capture_figures.cjs
   ```
   Para repetir solo algunas figuras: `--only 14` o `--only 10,11,13`. Las Figuras 10, 11 y 13 van juntas porque comparten conversación.
3. Lee el resumen final. Si dice «Sin advertencias», las imágenes cumplen lo que exigen las fichas. Si lista advertencias (por ejemplo, «sigue indexado seguro_estudiantil.pdf»), corrige la causa y repite esa figura.
4. Mira cada PNG una vez antes de insertarlo.

Cada ejecución crea cuentas nuevas (`demo.tesis2`, `demo.tesis3`, …) si la anterior ya tiene mensajes, y consume unas cuatro respuestas del modelo.

## Opción B · Manual

## 0. Preparación del sistema

Hazlo una sola vez, antes de la primera captura.

### 0.1 Detener la indexación automática del corpus ficticio

El backend vuelve a indexar en cada arranque los PDF de ejemplo de `/app/documents` que no estén registrados. Si los borras sin este paso, reaparecen en el siguiente reinicio.

1. Abre `.env` en la raíz del proyecto y cambia la línea existente:
   ```
   SEED_DOCUMENTS_DIR=/app/documents
   ```
   por:
   ```
   SEED_DOCUMENTS_DIR=/app/data/sin-semilla
   ```
   La carpeta no existe a propósito: el backend registra un aviso y no siembra nada. Para volver al comportamiento original, restaura `/app/documents`.
2. Recrea el backend para que lea el `.env`:
   ```bash
   docker compose up -d --force-recreate backend
   ```
3. Espera a que `docker compose ps` muestre el backend como `healthy`.

### 0.2 Dejar solo los 15 documentos oficiales

1. Abre `http://localhost:5173/login` e inicia sesión con la cuenta administrativa (`DEFAULT_ADMIN_EMAIL` y `DEFAULT_ADMIN_PASSWORD` de tu `.env`).
2. En el panel lateral, entra a **Documentos oficiales** (`/admin`).
3. Elimina, con el icono de papelera y confirmando, estos tres documentos:
   - `becas_y_beneficios`
   - `reglamento_estudiantil`
   - `seguro_estudiantil`
4. Elimina **una** de las dos filas de «Administración de Empresas 2025».
5. Comprueba que quedan exactamente 15 filas, todas en «Indexado»:
   - Reglamento de Ayudas Financieras y Reglamento de Grupos Estudiantiles.
   - Proceso de Admisión e Inscripción, Calendario Académico y folleto general (Bifoliar).
   - Administración de Empresas, Agroforestería, Agrícola y Pecuaria, Centro de Idiomas, Educación Física, Facultad de Educación, ITEC, Industrialización de Alimentos, Informática y Maestría.
6. Cierra sesión.

> Este paso no es solo cosmético: el protocolo (VII.B) declara que el corpus ficticio se retira antes de la evaluación, y `evaluate.py` mide contra lo que esté indexado.

### 0.3 Comprobar que el modelo responde

Las Figuras 9, 11, 12 y 13 necesitan llamadas reales a Claude. Si la cuenta de Anthropic no tiene crédito, el asistente contesta «No pude completar la respuesta en este momento» y esas capturas no sirven.

1. Pulsa «Continuar como invitado».
2. Pregunta: `¿Qué es una beca?`
3. Si llega una respuesta con fuente, el modelo funciona. Cierra sesión (icono al pie del panel lateral).

### 0.4 Configurar Chrome para capturas exactas

Todas las capturas se toman con las herramientas de desarrollo de Chrome: dan siempre el mismo tamaño, sin barra de direcciones, pestañas ni cursor.

1. Abre `http://localhost:5173` en una ventana de Chrome **sin extensiones visibles**. Una ventana de invitado de Chrome sirve: perfil → «Abrir ventana de invitado».
2. Abre las herramientas de desarrollo: `Cmd + Opción + I` (macOS) o `Ctrl + Mayús + I` (Windows).
3. Activa la barra de dispositivos: `Cmd + Mayús + M` (macOS) o `Ctrl + Mayús + M` (Windows).
4. En la barra superior del área de la página:
   - **Dimensions**: `Responsive`, ancho `1440`, alto `900`.
   - Menú `⋮` de esa barra → **Add device pixel ratio** → elige **2.0**.
   - El zoom de la barra en **100 %**. El zoom del navegador también en 100 % (`Cmd + 0` o `Ctrl + 0`).
5. Fuerza el modo claro: en las herramientas de desarrollo, `⋮` → **More tools** → **Rendering** → *Emulate CSS media feature prefers-color-scheme* → `light`. Si el prototipo ya está en modo oscuro, usa además el conmutador sol/luna al pie del panel lateral.
6. Para capturar: menú `⋮` de la barra de dispositivos → **Capture screenshot**. Chrome descarga un PNG de 2880 × 1800 px. Usa **Capture full size screenshot** solo donde la ficha lo indique.
7. Antes de cada captura, saca el puntero del área de la página: un botón con el puntero encima cambia de color.

### 0.5 Carpeta y nombres de archivo

Guarda las capturas en `docs/thesis/figures/capturas/` con estos nombres exactos:

| Figura | Archivo |
|---|---|
| 5 | `Figura08_inicio_sesion.png` |
| 6 | `Figura09_modo_invitado.png` |
| 7 | `Figura10_pantalla_inicial.png` |
| 8 | `Figura11_respuesta_citada.png` |
| 9 | `Figura12_abstencion.png` |
| 10 | `Figura13_historial.png` |
| 11 | `Figura14_panel_administrativo.png` |

## Capturas

### Figura 8 · Inicio de sesión

1. **Pantalla**: `http://localhost:5173/login`, sin sesión iniciada (si entra al chat, cierra sesión).
2. **Usuario**: ninguno.
3. **Escribir**: nada. El formulario debe quedar vacío.
4. **Esperar**: el panel verde de la izquierda con «Asistente Inteligente UVG» y la tarjeta «Bienvenido» a la derecha, con las animaciones terminadas (2 s).
5. **Capturar**: Capture screenshot, con el puntero fuera de la página.
6. **Recortar**: nada.
7. **Nombre**: `Figura08_inicio_sesion.png`.
8. **Protocolo**: Anexo E, citada en VIII.D.2.

No pulses «Ingresar con Microsoft» antes de capturar: deja un aviso en la tarjeta. Si lo pulsaste, recarga la página.

### Figura 9 · Modo invitado

1. **Pantalla**: `/login` → **Continuar como invitado**. Se abre `/chat`.
2. **Usuario**: invitado (sesión nueva; si el panel ya muestra una conversación, cierra sesión y repite).
3. **Escribir** en el compositor y enviar con Intro:
   ```
   ¿Hasta cuándo puedo pagar la cuota de octubre sin recargo?
   ```
4. **Esperar**: una respuesta que diga que el último día es el **17 de octubre**, con el bloque «Fuente» del **Calendario Académico**. En pantalla deben verse la insignia «Invitado» en la cabecera y, al pie, «Estás utilizando Alexis como visitante…».
5. **Capturar**: con la respuesta completa y sin el indicador de escritura.
6. **Recortar**: nada.
7. **Nombre**: `Figura09_modo_invitado.png`.
8. **Protocolo**: Anexo E, citada en VIII.D.2.

Después, cierra sesión.

### Figura 10 · Pantalla inicial

> Antes, decide qué hacer con las sugerencias de la pantalla inicial (ficha de la [Figura 10](figures/Figure10_Pantalla_inicial.md#decisión-previa-obligatoria)).

1. **Pantalla**: `/login` → enlace «¿Aún no tienes cuenta? **Crear una**» (`/register`).
2. **Usuario**: crea la cuenta `demo.tesis@uvg.edu.gt` con una contraseña de al menos 8 caracteres. No uses tu correo real ni el de otra persona.
3. **Escribir**: nada en el chat.
4. **Esperar**: «Bienvenido al Asistente Inteligente UVG», las sugerencias, «En línea» en la cabecera y el correo de demostración al pie del panel lateral.
5. **Capturar**: con el puntero fuera de la página.
6. **Recortar**: nada.
7. **Nombre**: `Figura10_pantalla_inicial.png`.
8. **Protocolo**: Anexo E, citada en VIII.D.4.

No cierres sesión: la Figura 11 continúa aquí.

### Figura 11 · Respuesta con citación

1. **Pantalla**: el mismo chat de la Figura 10.
2. **Usuario**: `demo.tesis@uvg.edu.gt`.
3. **Escribir y enviar**:
   ```
   ¿Qué tipos de ayuda financiera ofrece la universidad?
   ```
4. **Esperar**: una respuesta que nombre la **beca**, el **crédito educativo** y el **subsidio por auxiliatura**. Debajo, el bloque «Fuentes» con «Reglamento de ayudas financieras», una ubicación que incluya **«Artículo 7. Tipos de ayudas financieras · págs. 4–5»** y la etiqueta «Confianza alta».
5. **Capturar**: si la respuesta y el bloque «Fuente» caben en 1440 × 900, usa Capture screenshot. Si no, desplázate hasta que se vean la pregunta y el bloque completo; como último recurso, usa Capture full size screenshot y recorta.
6. **Recortar** (solo con la captura completa): desde la cabecera hasta el compositor, manteniendo el ancho completo y el panel lateral.
7. **Nombre**: `Figura11_respuesta_citada.png`.
8. **Protocolo**: Anexo E, citada en VIII.D.4 y VIII.C.9.

Si la fuente no cita el artículo 7 o falta la página, no uses la captura: revisa que el paso 0.2 se haya hecho y que el reglamento esté «Indexado».

**No pulses «Nueva conversación»** en esta cuenta: ocultaría estos mensajes para la Figura 13.

### Figura 13 · Historial

Se hace ahora, antes que la 12, porque continúa la conversación de la Figura 11.

1. **Pantalla**: el mismo chat.
2. **Usuario**: `demo.tesis@uvg.edu.gt`.
3. **Escribir y enviar**:
   ```
   ¿Y en qué se diferencia la beca del crédito?
   ```
4. **Esperar**: una respuesta que explica que la beca no se reembolsa y el crédito sí, con una tabla comparativa.
5. **Cerrar sesión** con el icono al pie del panel lateral. Vuelve a iniciar sesión con `demo.tesis@uvg.edu.gt`.
6. **Esperar**: que la conversación se cargue sola, con «Hoy» en el panel lateral y la conversación seleccionada. Desplázate hasta que la pregunta «¿Y en qué se diferencia la beca del crédito?» quede arriba, debajo de la cabecera.
7. **Capturar** y guardar como `Figura13_historial.png`. No se recorta.
8. **Protocolo**: Anexo E, citada en VIII.D.4.

Cierra sesión.

### Figura 12 · Abstención

1. **Pantalla**: `/register`.
2. **Usuario**: crea una segunda cuenta, `demo2.tesis@uvg.edu.gt`, sin mensajes.
3. **Escribir y enviar**:
   ```
   ¿Cuál es el horario de atención de la biblioteca?
   ```
4. **Esperar**: un mensaje de abstención **sin** bloque «Fuente». En la captura del 10 de octubre empezó con «No logré relacionar tu mensaje con la normativa oficial…» y debajo apareció la nota «No encontré normativa que respalde una respuesta a esto». El texto puede variar; lo que importa es que no dé ningún horario.
5. **Capturar**: con la respuesta completa.
6. **Recortar**: nada.
7. **Nombre**: `Figura12_abstencion.png`.
8. **Protocolo**: Anexo E, citada en VIII.D.4 y VIII.C.8.

Si el asistente da un horario, **no captures**: es una alucinación y debe registrarse como hallazgo. Prueba con la pregunta de respaldo, «¿Cómo pido una constancia de estudios y cuánto cuesta?», desde una tercera cuenta nueva.

Cierra sesión.

### Figura 14 · Panel administrativo

1. **Pantalla**: `/login` con la cuenta administrativa → **Documentos oficiales** en el panel lateral (`/admin`).
2. **Usuario**: la cuenta administrativa del `.env`.
3. **Escribir**: nada; el buscador queda vacío.
4. **Esperar**: las 15 filas en «Indexado», sin notificaciones en pantalla.
5. **Capturar**: si las 15 filas no caben, usa Capture full size screenshot.
6. **Recortar** (solo con la captura completa): desde el título «Documentos» hasta la última fila.
7. **Nombre**: `Figura14_panel_administrativo.png`.
8. **Protocolo**: Anexo E, citada en VIII.D.4 y VII.B.

## Después de capturar

1. Revisa cada imagen al 100 %: texto nítido, sin cursor, sin notificaciones, sin datos reales.
2. Inserta cada imagen en Word con **Insertar → Imágenes**, ajustada al ancho del área de texto.
3. Debajo de cada imagen, inserta el pie con **Referencias → Insertar título**, etiqueta «Figura». Así Word numera solo y puede generar el índice de figuras. Copia el texto del pie desde la ficha correspondiente.
4. Pega los párrafos de referencia de cada ficha en la sección indicada.
5. Revierte el cambio del paso 0.1 solo cuando hayan terminado la evaluación y la defensa; mientras tanto, el corpus ficticio debe seguir fuera.
