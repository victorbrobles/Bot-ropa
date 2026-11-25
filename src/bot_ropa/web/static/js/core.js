// Utilidades compartidas por todas las secciones.

export const $ = (sel, root = document) => root.querySelector(sel);

/** Crea elementos de forma segura (el texto nunca se interpreta como HTML). */
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "style") Object.assign(el.style, value);
    else if (key === "vars") for (const [k, v] of Object.entries(value)) el.style.setProperty(k, v);
    else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else el.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

export const storage = {
  get(key, fallback) {
    try {
      const raw = localStorage.getItem(`vestia:${key}`);
      return raw === null ? fallback : JSON.parse(raw);
    } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(`vestia:${key}`, JSON.stringify(value)); } catch { /* sin almacenamiento */ }
  },
};

export async function api(path, options = {}) {
  const isForm = options.body instanceof FormData;
  const res = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...options,
    headers: isForm || !options.body ? options.headers : { "Content-Type": "application/json", ...options.headers },
  });
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch { /* respuesta vacía */ }
  if (!res.ok) throw new Error(data?.detail && typeof data.detail === "string"
    ? data.detail : res.status === 422 ? "Revisa los datos introducidos." : "Algo ha fallado. Inténtalo de nuevo.");
  return data;
}

export const debounce = (fn, ms) => {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
};

let optionsPromise = null;
/** Opciones del servidor (ánimos, colores, tipos de prenda...), cargadas una vez. */
export function getOptions() {
  optionsPromise ??= api("/options").catch((err) => { optionsPromise = null; throw err; });
  return optionsPromise;
}

/** Aviso breve en la parte inferior de la pantalla. */
export function toast(message) {
  const el = h("div", { class: "toast", role: "status" }, message);
  document.body.append(el);
  setTimeout(() => el.classList.add("out"), 2600);
  setTimeout(() => el.remove(), 3000);
}
