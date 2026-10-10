#!/usr/bin/env node
/**
 * Captura automática de las Figuras 8 a 14 del protocolo (docs/thesis/capture_guide.md).
 *
 * Abre el prototipo en Chrome con las mismas condiciones que la guía manual:
 * viewport de 1440 × 900 px, densidad 2 (archivos de 2880 px de ancho), modo claro,
 * zoom 100 % y una sesión de navegador limpia por figura. Escribe las conversaciones
 * de la guía, espera la respuesta real del backend y guarda cada PNG con su nombre
 * definitivo. Al final escribe capture_report.json con las comprobaciones de cada figura
 * (fuentes citadas, fundamentación, número de documentos), que hay que revisar.
 *
 * No modifica el sistema salvo lo que haría una persona: registra cuentas de
 * demostración ficticias (demo.tesis…@uvg.edu.gt), abre sesiones de invitado y envía
 * preguntas, lo que consume llamadas a la API de Anthropic (unas 4 respuestas).
 *
 * Requisitos: el prototipo en ejecución (docker compose up), Node.js 18+, Google Chrome
 * y puppeteer-core:
 *     npm install --no-save puppeteer-core
 *
 * Uso (desde la raíz del repositorio):
 *     node docs/thesis/tools/capture_figures.cjs                 # las siete figuras
 *     node docs/thesis/tools/capture_figures.cjs --only 8,9      # solo algunas
 *
 * Variables opcionales: APP_URL (http://localhost:5173), API_URL (http://localhost:8000),
 * CHROME_PATH, DEMO_PASSWORD. La cuenta administrativa se lee de DEFAULT_ADMIN_EMAIL y
 * DEFAULT_ADMIN_PASSWORD en el .env de la raíz.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const OUT_DIR = path.resolve(__dirname, "..", "figures", "capturas");
const APP = (process.env.APP_URL || "http://localhost:5173").replace(/\/$/, "");
const API = (process.env.API_URL || "http://localhost:8000").replace(/\/$/, "");
const DEMO_PASSWORD = process.env.DEMO_PASSWORD || "Tesis-Demo-2026";
const VIEWPORT = { width: 1440, height: 900, deviceScaleFactor: 2 };
const MAX_HEIGHT = 1800;
const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].filter(Boolean);

const OFFICIAL_DOCUMENTS = 15;
const FICTIONAL = ["becas_y_beneficios", "reglamento_estudiantil", "seguro_estudiantil"];

const REPORT_PATH = path.join(OUT_DIR, "capture_report.json");
// Se fusiona con el reporte anterior: repetir una figura (--only) no borra las demás.
const report = (() => {
  try {
    const previous = JSON.parse(fs.readFileSync(REPORT_PATH, "utf8"));
    return { ...previous, generated_at: new Date().toISOString(), app: APP, figures: previous.figures || {} };
  } catch {
    return { generated_at: new Date().toISOString(), app: APP, figures: {} };
  }
})();
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// --------------------------------------------------------------------------- utilidades

function readEnv() {
  const values = {};
  try {
    for (const line of fs.readFileSync(path.join(ROOT, ".env"), "utf8").split(/\r?\n/)) {
      const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
      if (match) values[match[1]] = match[2].replace(/^["']|["']$/g, "");
    }
  } catch {
    // sin .env: se usan los valores por defecto del backend
  }
  return values;
}

async function api(method, route, body, token) {
  const response = await fetch(`${API}${route}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  return { status: response.status, data };
}

/** Primera cuenta `<base>[N]@uvg.edu.gt` sin mensajes: la registra o reutiliza una vacía. */
async function freshAccount(base) {
  for (let n = 1; n <= 50; n += 1) {
    const email = `${base}${n === 1 ? "" : n}@uvg.edu.gt`;
    const registered = await api("POST", "/auth/register", { email, password: DEMO_PASSWORD });
    if (registered.status === 201) return email;
    const login = await api("POST", "/auth/login", { email, password: DEMO_PASSWORD });
    if (login.status !== 200) continue; // existe con otra contraseña
    const history = await api("GET", "/chat/history", null, login.data.session_token);
    const messages = (history.data || []).reduce((total, c) => total + (c.messages || []).length, 0);
    if (messages === 0) return email;
  }
  throw new Error(`No se encontró una cuenta libre para ${base}`);
}

async function newPage(browser) {
  const context = await browser.createBrowserContext();
  const page = await context.newPage();
  await page.setViewport(VIEWPORT);
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);
  await page.evaluateOnNewDocument(() => {
    try {
      localStorage.setItem("theme", "light"); // next-themes
    } catch {
      /* sin almacenamiento */
    }
  });
  return { context, page };
}

/** Saca el puntero de cualquier botón: el estado hover cambia colores en la captura. */
async function parkPointer(page) {
  await page.mouse.move(VIEWPORT.width / 2, 3);
  await page.evaluate(() => document.activeElement instanceof HTMLElement && document.activeElement.blur());
  await sleep(400);
}

async function login(page, email, password) {
  await page.goto(`${APP}/login`, { waitUntil: "networkidle0" });
  await page.locator("::-p-aria(Correo institucional)").fill(email);
  await page.locator("::-p-aria(Contraseña)").fill(password);
  await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/auth/login")),
    page.locator("::-p-aria(Iniciar sesión)").click(),
  ]);
  await page.waitForSelector("::-p-aria(Escribe tu consulta)", { timeout: 30000 });
  await sleep(2500); // carga del historial y animaciones de entrada
}

async function logout(page) {
  await page.locator("::-p-aria(Cerrar sesión)").click();
  await page.waitForSelector("::-p-aria(Correo institucional)", { timeout: 15000 });
}

/** Envía una pregunta por la interfaz y devuelve la respuesta JSON del backend. */
async function ask(page, question) {
  await page.locator("::-p-aria(Escribe tu consulta)").fill(question);
  const [response] = await Promise.all([
    page.waitForResponse(
      (r) => r.url() === `${API}/chat` && r.request().method() === "POST",
      { timeout: 120000 },
    ),
    page.locator("::-p-aria(Enviar pregunta)").click(),
  ]);
  const body = await response.json();
  await sleep(3500); // Markdown, bloque de fuentes y fin del indicador de escritura
  return body;
}

/** Alto de viewport con el que la conversación cabe sin desplazar (16:10 como mínimo). */
async function fitThread(page) {
  const needed = await page.evaluate(() => {
    const thread = document.getElementById("conversacion");
    if (!thread) return 0;
    return window.innerHeight - thread.clientHeight + thread.scrollHeight;
  });
  const height = Math.min(MAX_HEIGHT, Math.max(VIEWPORT.height, Math.ceil(needed)));
  if (height !== VIEWPORT.height) {
    await page.setViewport({ ...VIEWPORT, height });
    await sleep(800);
    await page.evaluate(() => {
      const thread = document.getElementById("conversacion");
      if (thread) thread.scrollTop = thread.scrollHeight;
    });
    await sleep(500);
  }
  return height;
}

async function shot(page, figure, file, extra = {}, options = {}) {
  await parkPointer(page);
  const target = path.join(OUT_DIR, file);
  await page.screenshot({ path: target, ...options });
  const viewport = page.viewport();
  report.figures[figure] = {
    file: path.relative(ROOT, target),
    pixels: options.fullPage ? "página completa" : `${viewport.width * 2} × ${viewport.height * 2}`,
    ...extra,
  };
  console.log(`Figura ${figure}: ${path.relative(ROOT, target)}`);
}

function describeSources(answer) {
  return (answer.sources || []).map((s) =>
    [s.document_title || s.document_name, s.section, s.page_number && `pág. ${s.page_number}`]
      .filter(Boolean)
      .join(" · "),
  );
}

function checks(answer, expectations) {
  const sources = describeSources(answer);
  const result = {
    question_ok: true,
    is_grounded: answer.is_grounded,
    confidence: answer.confidence,
    sources,
    answer_start: (answer.answer_text || "").slice(0, 220),
    warnings: [],
  };
  if (expectations.grounded !== undefined && answer.is_grounded !== expectations.grounded) {
    result.warnings.push(`se esperaba is_grounded=${expectations.grounded}`);
  }
  if (expectations.source && !sources.some((s) => expectations.source.test(s))) {
    result.warnings.push(`ninguna fuente coincide con ${expectations.source}`);
  }
  if (expectations.text && !expectations.text.test(answer.answer_text || "")) {
    result.warnings.push(`la respuesta no contiene ${expectations.text}`);
  }
  if (expectations.noSources && sources.length) {
    result.warnings.push("una abstención no debería citar fuentes");
  }
  if (sources.some((s) => FICTIONAL.some((f) => s.toLowerCase().includes(f.replace(/_/g, " "))))) {
    result.warnings.push("cita un documento del corpus ficticio");
  }
  if (/No pude completar la respuesta/.test(answer.answer_text || "")) {
    result.warnings.push("fallo del proveedor: revisa el crédito de la API");
  }
  return result;
}

// --------------------------------------------------------------------------- figuras

async function figure8(browser) {
  const { context, page } = await newPage(browser);
  await page.goto(`${APP}/login`, { waitUntil: "networkidle0" });
  await sleep(2500);
  await shot(page, 8, "Figura08_inicio_sesion.png");
  await context.close();
}

async function figure9(browser) {
  const { context, page } = await newPage(browser);
  await page.goto(`${APP}/login`, { waitUntil: "networkidle0" });
  await page.locator("::-p-aria(Continuar como invitado)").click();
  await page.waitForSelector("::-p-aria(Escribe tu consulta)", { timeout: 30000 });
  await sleep(2000);
  const answer = await ask(page, "¿Hasta cuándo puedo pagar la cuota de octubre sin recargo?");
  await fitThread(page);
  await shot(page, 9, "Figura09_modo_invitado.png",
    checks(answer, { grounded: true, text: /17 de octubre/, source: /Calendario/i }));
  await context.close();
}

async function figures101113(browser) {
  const email = await freshAccount("demo.tesis");
  const { context, page } = await newPage(browser);
  await login(page, email, DEMO_PASSWORD);
  await shot(page, 10, "Figura10_pantalla_inicial.png", { account: email });

  const first = await ask(page, "¿Qué tipos de ayuda financiera ofrece la universidad?");
  await fitThread(page);
  await shot(page, 11, "Figura11_respuesta_citada.png", {
    account: email,
    ...checks(first, {
      grounded: true,
      text: /beca[\s\S]*cr[eé]dito[\s\S]*auxiliatura|auxiliatura[\s\S]*cr[eé]dito/i,
      source: /Art[ií]culo 7/i,
    }),
  });
  await page.setViewport(VIEWPORT);

  const second = await ask(page, "¿Y en qué se diferencia la beca del crédito?");
  await logout(page);
  await login(page, email, DEMO_PASSWORD);
  // Encuadre: desde la segunda pregunta (prueba de la elipsis) hacia abajo, con el
  // panel lateral visible; 1440 × 1100 mantiene una proporción imprimible.
  await page.setViewport({ ...VIEWPORT, height: 1100 });
  await sleep(800);
  await page.evaluate((text) => {
    const thread = document.getElementById("conversacion");
    const target = [...thread.querySelectorAll("*")].find(
      (el) => el.children.length === 0 && el.textContent.trim() === text,
    );
    if (target) thread.scrollTop += target.getBoundingClientRect().top - 110;
  }, "¿Y en qué se diferencia la beca del crédito?");
  await sleep(600);
  await shot(page, 13, "Figura13_historial.png", {
    account: email,
    turn2: checks(second, { grounded: true, text: /reembols/i }),
  });
  await context.close();
}

async function figure12(browser) {
  const email = await freshAccount("demo.abstencion");
  const { context, page } = await newPage(browser);
  await login(page, email, DEMO_PASSWORD);
  let answer = await ask(page, "¿Cuál es el horario de atención de la biblioteca?");
  let question = "Q31";
  if (answer.is_grounded) {
    // Respondió con un horario: es una alucinación y no sirve como figura (ver la ficha).
    report.hallucination_q31 = answer.answer_text;
    await context.close();
    const backup = await freshAccount("demo.abstencion");
    const retry = await newPage(browser);
    await login(retry.page, backup, DEMO_PASSWORD);
    answer = await ask(retry.page, "¿Cómo pido una constancia de estudios y cuánto cuesta?");
    question = "Q40";
    await fitThread(retry.page);
    await shot(retry.page, 12, "Figura12_abstencion.png",
      { account: backup, question, ...checks(answer, { grounded: false, noSources: true }) });
    await retry.context.close();
    return;
  }
  await fitThread(page);
  const kind = /Hay normativa relacionada/.test(answer.answer_text)
    ? "información insuficiente (después de la verificación)"
    : /No encontré normativa|No logré relacionar/.test(answer.answer_text)
      ? "sin normativa (antes de llamar al modelo)"
      : "otra";
  await shot(page, 12, "Figura12_abstencion.png", {
    account: email,
    question,
    abstention: kind,
    ...checks(answer, { grounded: false, noSources: true }),
  });
  await context.close();
}

async function figure14(browser) {
  const env = readEnv();
  const email = env.DEFAULT_ADMIN_EMAIL || "admin@uvg.edu.gt";
  const password = env.DEFAULT_ADMIN_PASSWORD || "admin123";
  const token = (await api("POST", "/auth/login", { email, password })).data?.session_token;
  const documents = token ? (await api("GET", "/admin/documents", null, token)).data || [] : [];
  const names = documents.map((d) => d.filename);
  const warnings = [];
  if (names.length !== OFFICIAL_DOCUMENTS) warnings.push(`hay ${names.length} documentos, no ${OFFICIAL_DOCUMENTS}`);
  for (const f of FICTIONAL) if (names.some((n) => n.includes(f))) warnings.push(`sigue indexado ${f}.pdf`);
  if (new Set(names).size !== names.length) warnings.push("hay documentos duplicados");
  if (documents.some((d) => d.status !== "indexed")) warnings.push("hay documentos sin indexar");

  const { context, page } = await newPage(browser);
  await login(page, email, password);
  await page.goto(`${APP}/admin`, { waitUntil: "networkidle0" });
  await sleep(2500);
  await shot(page, 14, "Figura14_panel_administrativo.png",
    { documents: names.length, warnings }, { fullPage: true });
  await context.close();
}

// --------------------------------------------------------------------------- principal

async function main() {
  const onlyArg = process.argv.indexOf("--only");
  const only = onlyArg > -1 ? new Set(process.argv[onlyArg + 1].split(",").map(Number)) : null;
  const wants = (...numbers) => !only || numbers.some((n) => only.has(n));

  const executablePath = CHROME_CANDIDATES.find((candidate) => fs.existsSync(candidate));
  if (!executablePath) throw new Error("No se encontró Google Chrome; define CHROME_PATH.");
  const health = await fetch(`${API}/health`).then((r) => r.ok).catch(() => false);
  if (!health) throw new Error(`El backend no responde en ${API}/health: ejecuta docker compose up.`);

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await puppeteer.launch({ executablePath, headless: true, args: ["--lang=es-GT"] });
  try {
    if (wants(8)) await figure8(browser);
    if (wants(9)) await figure9(browser);
    if (wants(10, 11, 13)) await figures101113(browser);
    if (wants(12)) await figure12(browser);
    if (wants(14)) await figure14(browser);
  } finally {
    await browser.close();
    fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
  }
  const warnings = Object.entries(report.figures).filter(([n]) => !only || only.has(Number(n))).flatMap(([n, f]) =>
    [...(f.warnings || []), ...(f.turn2?.warnings || [])].map((w) => `Figura ${n}: ${w}`));
  console.log(warnings.length ? `\nRevisar:\n- ${warnings.join("\n- ")}` : "\nSin advertencias.");
  console.log(`Reporte: ${path.relative(ROOT, REPORT_PATH)}`);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
