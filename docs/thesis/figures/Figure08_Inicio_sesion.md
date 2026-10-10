# Figura 8. Pantalla de inicio de sesión

| Campo | Valor |
|---|---|
| Número | Figura 8 |
| Nombre | Pantalla de inicio de sesión |
| Tipo | Captura de pantalla |
| Archivo | `docs/thesis/figures/capturas/Figura08_inicio_sesion.png` |
| Ubicación | Anexo E; se cita en VIII.D.2 |
| Ruta del prototipo | `http://localhost:5173/login` |
| Estado | **Capturada** el 10 de octubre de 2026 con `tools/capture_figures.cjs` |

## Objetivo

Mostrar los dos modos de acceso que describe VIII.D.2: la cuenta institucional (correo `@uvg.edu.gt` y contraseña) y el modo invitado para aspirantes, padres de familia y visitantes, junto con la identidad gráfica de UVG mencionada en VI.K.

## Qué debe mostrar

- **Pantalla**: `/login` completa en escritorio. A la izquierda, el panel de marca con el logotipo de UVG Campus Altiplano, el título «Asistente Inteligente UVG» y las cuatro capacidades (Reglamentos, Becas, Consultas inteligentes, IA generativa). A la derecha, la tarjeta «Bienvenido».
- **Estado**: formulario **vacío**, sin errores ni avisos, sin foco visible en ningún campo, sin la sesión iniciada.
- **Usuario**: ninguno.
- **Elementos visibles**: campos de correo (marcador «nombre@uvg.edu.gt») y contraseña, botón «Iniciar sesión», botón «Ingresar con Microsoft», botón «Continuar como invitado», nota «¿No tienes cuenta institucional?…» y enlace de registro.

## Cómo capturarla

| Parámetro | Valor |
|---|---|
| Resolución | Viewport de 1440 × 900 px con DPR 2 → archivo de 2880 × 1800 px |
| Relación de aspecto | 16:10, sin recortar |
| Modo | Claro |
| Zoom | 100 % |
| Datos personales | Ninguno en pantalla |
| Momento | Cuando terminen las animaciones de entrada, unos 2 s después de cargar |

Pasos: [guía de capturas, Figura 8](../capture_guide.md#figura-8--inicio-de-sesión).

**Qué evitar**
- Pulsar «Ingresar con Microsoft»: muestra el aviso de que aún no está habilitado, y ese aviso no debe salir en la figura.
- Escribir un correo en el formulario.
- Capturar con el cursor encima de un botón (el estado *hover* cambia su color).

## Pie de figura

> Figura 8. Pantalla de inicio de sesión del prototipo. Elaboración propia con base en el prototipo desarrollado.

## Referencia dentro del texto

Insertada en el protocolo (VIII.D.2, después del punto 2):

> La Figura 8 (Anexo E) presenta la pantalla de acceso. Los miembros de la comunidad universitaria ingresan con su correo institucional y su contraseña, mientras que las personas externas pueden continuar como invitadas sin registrarse. El botón de acceso con Microsoft 365 está reservado para una integración futura con el directorio institucional y, en el prototipo, solo informa que esa opción aún no está habilitada.
