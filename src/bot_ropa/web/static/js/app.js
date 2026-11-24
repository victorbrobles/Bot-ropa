// Vestia · interfaz web
// Sin dependencias: router por hash, menú y la sección "¿Qué me pongo?".

const $ = (sel, root = document) => root.querySelector(sel);

/** Crea elementos de forma segura (el texto nunca se interpreta como HTML). */
function h(tag, attrs = {}, ...children) {
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

const storage = {
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

async function api(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let data = null;
  try { data = await res.json(); } catch { /* respuesta vacía */ }
  if (!res.ok) throw new Error(data?.detail && typeof data.detail === "string"
    ? data.detail : "Algo ha fallado. Inténtalo de nuevo.");
  return data;
}

const debounce = (fn, ms) => {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
};

// =============================================================== Router
const ROUTES = {
  "/": "Vestia · Qué me pongo hoy",
  "/que-me-pongo": "¿Qué me pongo? · Vestia",
  "/armario": "Mi armario · Vestia",
  "/explorar": "Explorar outfits · Vestia",
};

function currentRoute() {
  const hash = location.hash;
  if (hash.startsWith("#/")) {
    const path = hash.slice(1);
    return ROUTES[path] ? { path } : { path: "/" };
  }
  return { path: "/", anchor: hash.slice(1) || null };
}

let lastPath = null;
function navigate() {
  const { path, anchor } = currentRoute();
  document.querySelectorAll("[data-view]").forEach((v) => { v.hidden = v.dataset.view !== path; });
  document.querySelectorAll(".menu a").forEach((a) => {
    if (a.dataset.route === path) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  document.title = ROUTES[path];
  closeMenu();
  if (anchor) {
    document.getElementById(anchor)?.scrollIntoView({ behavior: "smooth" });
  } else if (path !== lastPath) {
    window.scrollTo({ top: 0 });
    if (lastPath !== null) $("#app").focus({ preventScroll: true });
  }
  lastPath = path;
  if (path === "/que-me-pongo") outfitView.enter();
  updateFloatingButton();
}

// ================================================================= Menú
const menuBtn = $("#menu-btn");
const menu = $("#menu");

function openMenu() {
  menu.hidden = false;
  menuBtn.setAttribute("aria-expanded", "true");
  menuBtn.setAttribute("aria-label", "Cerrar menú");
}
function closeMenu() {
  menu.hidden = true;
  menuBtn.setAttribute("aria-expanded", "false");
  menuBtn.setAttribute("aria-label", "Abrir menú");
}
menuBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  menu.hidden ? openMenu() : closeMenu();
});
document.addEventListener("click", (e) => {
  if (!menu.hidden && !menu.contains(e.target)) closeMenu();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !menu.hidden) { closeMenu(); menuBtn.focus(); }
});

// ================================================== Buscador de localidades
function createLocationSearch({ label, placeholder, onSelect, autofocus = false }) {
  const id = `search-${Math.random().toString(36).slice(2, 8)}`;
  const input = h("input", {
    id, type: "search", placeholder, autocomplete: "off", enterkeyhint: "search",
    "aria-describedby": `${id}-hint`,
  });
  const list = h("ul", { class: "results", hidden: true, "aria-label": "Resultados" });
  const hint = h("p", { id: `${id}-hint`, class: "sr-only" }, "Escribe al menos dos letras y elige una opción de la lista.");
  let results = [];
  let seq = 0;

  const show = (items, emptyText) => {
    list.replaceChildren();
    if (!items.length) {
      list.append(h("li", { class: "empty" }, emptyText));
    } else {
      items.forEach((loc) => list.append(h("li", {},
        h("button", { type: "button", onclick: () => choose(loc) },
          h("strong", {}, loc.name), " ",
          h("small", {}, [loc.region, loc.country].filter(Boolean).join(", "))))));
    }
    list.hidden = false;
  };

  const choose = (loc) => {
    list.hidden = true;
    input.value = "";
    onSelect({ ...loc, source: "manual" });
  };

  const search = debounce(async () => {
    const q = input.value.trim();
    if (q.length < 2) { list.hidden = true; return; }
    const mine = ++seq;
    try {
      const data = await api(`/locations?q=${encodeURIComponent(q)}`);
      if (mine !== seq) return;
      results = data.results;
      show(results, "No encontramos esa zona. Prueba con otro nombre.");
    } catch (err) {
      if (mine === seq) show([], err.message);
    }
  }, 280);

  input.addEventListener("input", search);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); if (results[0] && !list.hidden) choose(results[0]); }
    if (e.key === "ArrowDown") { e.preventDefault(); list.querySelector("button")?.focus(); }
  });
  list.addEventListener("keydown", (e) => {
    const buttons = [...list.querySelectorAll("button")];
    const i = buttons.indexOf(document.activeElement);
    if (e.key === "ArrowDown") { e.preventDefault(); buttons[Math.min(i + 1, buttons.length - 1)]?.focus(); }
    if (e.key === "ArrowUp") { e.preventDefault(); i <= 0 ? input.focus() : buttons[i - 1].focus(); }
    if (e.key === "Escape") { list.hidden = true; input.focus(); }
  });

  const el = h("div", { class: "search" },
    h("label", { for: id }, label), hint,
    h("div", { class: "search-box" }, input), list);
  if (autofocus) requestAnimationFrame(() => input.focus());
  return el;
}

// ===================================================== ¿Qué me pongo?
const DEFAULT_PREFS = {
  mood: null, color: null, occasion: "diario", fit: "cualquiera",
  when: "now", hour: (new Date().getHours() + 1) % 24, hours: 8,
  trip: false, destination: null,
};

const outfitView = {
  started: false,
  options: null,
  origin: null,
  geo: "idle", // idle | locating | granted | denied | error | unsupported
  searching: false,
  prefs: { ...DEFAULT_PREFS, ...storage.get("prefs", {}), when: "now", destination: null, trip: false },
  result: null,
  loading: false,
  error: null,
  seq: 0,

  async enter() {
    if (this.started) return;
    this.started = true;
    this.renderLocation();
    this.renderResult();
    try {
      this.options = await api("/options");
      this.renderOptions();
    } catch (err) {
      this.error = err.message;
      this.renderResult();
    }
    this.locate();
  },

  // ------------------------------------------------------------ ubicación
  async locate() {
    if (!("geolocation" in navigator)) {
      this.geo = "unsupported";
      this.searching = true;
      return this.renderLocation();
    }
    try {
      const status = await navigator.permissions?.query({ name: "geolocation" });
      if (status?.state === "denied") {
        this.geo = "denied";
        this.searching = true;
        return this.renderLocation();
      }
    } catch { /* la API de permisos no está en todos los navegadores */ }

    this.geo = "locating";
    this.renderLocation();
    this.renderResult();
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.geo = "granted";
        // Redondeamos a ~1 km: suficiente para el tiempo y más privado.
        const round = (n) => Math.round(n * 100) / 100;
        this.setOrigin({
          name: "Tu ubicación actual",
          latitude: round(pos.coords.latitude),
          longitude: round(pos.coords.longitude),
          source: "gps",
        });
      },
      (err) => {
        this.geo = err.code === err.PERMISSION_DENIED ? "denied" : "error";
        this.searching = true;
        this.renderLocation();
        this.renderResult();
      },
      { timeout: 12000, maximumAge: 10 * 60 * 1000, enableHighAccuracy: false },
    );
  },

  setOrigin(loc) {
    this.origin = loc;
    this.searching = false;
    if (loc.source === "manual") storage.set("lastPlace", loc);
    this.renderLocation();
    $("#options").hidden = !this.options;
    this.fetchOutfit();
  },

  renderLocation() {
    const card = $("#location-card");
    card.replaceChildren();

    if (this.geo === "locating") {
      card.append(h("div", { class: "loc-row" },
        h("div", { class: "loc-current" }, h("span", { class: "spinner", "aria-hidden": "true" }),
          h("div", {}, h("div", { class: "loc-name" }, "Buscando tu ubicación…"),
            h("div", { class: "loc-sub" }, "Acepta el permiso del navegador para usar el tiempo de tu zona."))),
        h("button", { type: "button", class: "link-btn", onclick: () => { this.geo = "idle"; this.searching = true; this.renderLocation(); this.renderResult(); } },
          "Prefiero escribirla")));
      return;
    }

    if (this.searching || !this.origin) {
      if (!this.origin && (this.geo === "denied" || this.geo === "error" || this.geo === "unsupported")) {
        const text = {
          denied: "No tenemos permiso para ver tu ubicación. Escribe tu zona para continuar.",
          error: "No hemos podido obtener tu ubicación. Escribe tu zona para continuar.",
          unsupported: "Tu navegador no permite compartir la ubicación. Escribe tu zona para continuar.",
        }[this.geo];
        card.append(h("p", { class: "loc-msg", role: "status" }, h("span", { "aria-hidden": "true" }, "📍"), text));
      }
      card.append(createLocationSearch({
        label: this.origin ? "¿Qué zona quieres consultar?" : "¿Dónde estás?",
        placeholder: "Escribe tu ciudad o pueblo",
        onSelect: (loc) => this.setOrigin(loc),
        autofocus: Boolean(this.origin),
      }));
      const actions = h("div", { class: "loc-actions" });
      const last = storage.get("lastPlace", null);
      if (!this.origin && last) {
        actions.append(h("button", { type: "button", class: "chip", onclick: () => this.setOrigin(last) },
          "🕘 ", last.name));
      }
      if (this.geo !== "denied" && this.geo !== "unsupported" && this.origin?.source !== "gps") {
        actions.append(h("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => this.locate() },
          "📍 Usar mi ubicación"));
      }
      if (this.origin) {
        actions.append(h("button", { type: "button", class: "link-btn", onclick: () => { this.searching = false; this.renderLocation(); } },
          "Cancelar"));
      }
      if (actions.childElementCount) card.append(actions);
      return;
    }

    const o = this.origin;
    const sub = o.source === "gps"
      ? "Detectada automáticamente"
      : [o.region, o.country].filter(Boolean).join(", ") || "Zona elegida por ti";
    card.append(h("div", { class: "loc-row" },
      h("div", { class: "loc-current" },
        h("span", { class: "loc-pin", "aria-hidden": "true" }, o.source === "gps" ? "📍" : "🏙️"),
        h("div", {}, h("div", { class: "loc-name" }, o.name), h("div", { class: "loc-sub" }, sub))),
      h("div", { class: "loc-actions" },
        o.source !== "gps" && this.geo === "granted"
          ? h("button", { type: "button", class: "link-btn", onclick: () => this.locate() }, "Volver a mi ubicación")
          : null,
        h("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => { this.searching = true; this.renderLocation(); } },
          "Cambiar zona"))));
  },

  // ------------------------------------------------------------- petición
  buildRequest() {
    const p = this.prefs;
    const strip = ({ source, label, ...loc }) => loc;
    return {
      origin: strip(this.origin),
      destination: p.trip && p.destination ? strip(p.destination) : null,
      hours: p.hours,
      day_offset: p.when === "tomorrow" ? 1 : 0,
      start_hour: p.when === "now" ? null : p.hour,
      occasion: p.occasion,
      mood: p.mood,
      color: p.color,
      fit: p.fit,
    };
  },

  async fetchOutfit() {
    if (!this.origin) return;
    const mine = ++this.seq;
    this.loading = true;
    this.error = null;
    this.renderResult();
    try {
      const data = await api("/outfit", { method: "POST", body: JSON.stringify(this.buildRequest()) });
      if (mine !== this.seq) return;
      this.result = data;
      $("#attribution").textContent = data.attribution;
    } catch (err) {
      if (mine !== this.seq) return;
      this.error = err.message;
    }
    this.loading = false;
    this.renderResult();
  },

  // ------------------------------------------------------------ resultado
  renderResult() {
    const box = $("#result");
    if (this.error) {
      box.replaceChildren(h("div", { class: "card error-card", role: "alert" },
        h("span", { "aria-hidden": "true", style: { fontSize: "1.6rem" } }, "⚠️"),
        h("div", {}, h("strong", {}, "No hemos podido preparar tu outfit"), h("p", {}, this.error)),
        this.origin ? h("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => this.fetchOutfit() }, "Reintentar") : null));
      return;
    }
    if (!this.result) {
      if (this.loading || this.geo === "locating") {
        box.replaceChildren(
          h("div", { class: "skeleton", style: { height: "220px" }, "aria-hidden": "true" }),
          h("div", { class: "skeleton", style: { height: "360px" }, "aria-hidden": "true" }),
          h("p", { class: "sr-only" }, "Cargando…"));
      } else {
        box.replaceChildren(h("div", { class: "card empty-state" },
          h("span", { class: "big", "aria-hidden": "true" }, "🧭"),
          h("p", {}, "Dinos dónde estás y te diremos qué ponerte.")));
      }
      return;
    }
    box.replaceChildren(this.weatherCard(this.result.weather), this.outfitCard(this.result.outfit));
    box.classList.toggle("updating", this.loading);
    box.setAttribute("aria-busy", this.loading ? "true" : "false");
    updateFloatingButton();
  },

  weatherCard(weather) {
    const s = weather.overall;
    const first = weather.places[0];
    const hours = first.hours;
    const startH = hours[0].local_hour;
    const endH = (hours[hours.length - 1].local_hour + 1) % 24;
    const fmt = (hr) => `${String(hr).padStart(2, "0")}:00`;
    const when = this.prefs.when === "now"
      ? `Desde ahora hasta las ${fmt(endH)}`
      : `${this.prefs.when === "tomorrow" ? "Mañana" : "Hoy"} de ${fmt(startH)} a ${fmt(endH)}`;

    const places = weather.places.length > 1
      ? h("div", { class: "places" }, weather.places.map((p, i) =>
        h("div", { class: "place" },
          h("span", {}, i === 0 ? "🏠 " : "🧳 ", i === 0 ? this.origin.name : p.location.name),
          h("span", {}, `${p.summary.condition.icon} ${p.summary.min_feels}°–${p.summary.max_feels}° · 💧${p.summary.precip_probability}%`))))
      : null;

    return h("section", { class: "card weather-card", "aria-label": "El tiempo" },
      h("div", { class: "wx-top" },
        h("span", { class: "wx-icon", "aria-hidden": "true" }, s.condition.icon),
        h("div", {},
          h("div", { class: "wx-when" }, when),
          h("div", { class: "wx-cond" }, s.condition.label),
          h("div", { class: "wx-temp" }, `${s.min_feels}° – ${s.max_feels}°`, " ",
            h("small", {}, "de sensación")))),
      h("div", { class: "wx-stats" },
        h("div", { class: "stat" }, h("span", {}, "💧 Lluvia"), h("strong", {}, `${s.precip_probability}%`)),
        h("div", { class: "stat" }, h("span", {}, "💨 Viento"), h("strong", {}, `${s.max_wind} km/h`)),
        h("div", { class: "stat" }, h("span", {}, "🔆 UV máx."), h("strong", {}, String(Math.round(s.max_uv))))),
      places,
      h("div", { class: "hourly", role: "list", "aria-label": "Previsión por horas" },
        hours.map((hr) => h("div", { class: "hour", role: "listitem" },
          h("small", {}, fmt(hr.local_hour)),
          h("span", { class: "i", title: hr.label, "aria-label": hr.label }, hr.icon),
          h("strong", {}, `${hr.temperature}°`),
          hr.precip_probability >= 20 ? h("span", { class: "rain" }, `${hr.precip_probability}%`) : h("span", { class: "rain" }, " ")))));
  },

  outfitCard(outfit) {
    return h("section", { class: "card outfit-card", id: "outfit", "aria-label": "Tu outfit" },
      h("div", { class: "outfit-head" },
        h("h2", {}, "Tu outfit"),
        h("p", {}, outfit.headline)),
      h("ul", { class: "items" }, outfit.items.map((item, i) =>
        h("li", { class: "item", style: { animationDelay: `${i * 40}ms` } },
          h("span", { class: "item-swatch", vars: { "--c": item.color.hex }, "aria-hidden": "true" }, item.icon),
          h("div", {},
            h("div", { class: "item-slot" }, item.slot_label),
            h("div", { class: "item-name" }, item.name),
            h("div", { class: "item-color" }, h("i", { vars: { "--c": item.color.hex } }), item.color.label),
            h("p", { class: "item-reason" }, item.reason),
            item.alternatives.length
              ? h("p", { class: "item-alt" }, "O también: ", item.alternatives.join(" · "))
              : null)))),
      outfit.accessories.length ? h("div", {},
        h("h3", { class: "subhead" }, "Complementos"),
        h("div", { class: "acc-list" }, outfit.accessories.map((a) =>
          h("span", { class: "acc", title: a.reason },
            h("span", { "aria-hidden": "true" }, a.icon), a.name, " ", h("small", {}, `· ${a.reason}`))))) : null,
      h("div", {},
        h("h3", { class: "subhead" }, "Paleta de colores"),
        h("div", { class: "palette", role: "img", "aria-label": `Colores: ${outfit.palette.map((c) => c.label).join(", ")}` },
          outfit.palette.map((c) => h("i", { vars: { "--c": c.hex }, title: c.label })))),
      outfit.tips.length ? h("div", {},
        h("h3", { class: "subhead" }, "Consejos"),
        h("ul", { class: "tips" }, outfit.tips.map((t) => h("li", {}, t)))) : null);
  },

  // ------------------------------------------------------------- opciones
  setPref(changes, { refetch = true } = {}) {
    Object.assign(this.prefs, changes);
    const { mood, color, occasion, fit, hours } = this.prefs;
    storage.set("prefs", { mood, color, occasion, fit, hours });
    this.syncOptions();
    if (refetch) this.refetchSoon();
  },

  refetchSoon: debounce(function () { outfitView.fetchOutfit(); }, 250),

  renderOptions() {
    const o = this.options;
    $("#opt-mood").replaceChildren(...o.moods.map((m) =>
      h("button", { type: "button", class: "chip", "data-value": m.id,
        onclick: () => this.setPref({ mood: this.prefs.mood === m.id ? null : m.id }) },
        h("span", { "aria-hidden": "true" }, m.icon), m.label)));

    $("#opt-occasion").replaceChildren(...o.occasions.map((oc) =>
      h("button", { type: "button", class: "chip", role: "radio", "data-value": oc.id,
        onclick: () => this.setPref({ occasion: oc.id }) },
        h("span", { "aria-hidden": "true" }, oc.icon), oc.label)));
    $("#opt-occasion").setAttribute("role", "radiogroup");
    $("#opt-occasion").setAttribute("aria-label", "Ocasión");

    $("#opt-fit").replaceChildren(...o.fits.map((f) =>
      h("button", { type: "button", role: "radio", "data-value": f.id,
        onclick: () => this.setPref({ fit: f.id }) }, f.label)));

    $("#opt-color").replaceChildren(
      h("button", { type: "button", class: "swatch swatch-none", "data-value": "",
        onclick: () => this.setPref({ color: null }) }, "Sin preferencia"),
      ...o.colors.map((c) => h("button", {
        type: "button", class: "swatch", "data-value": c.id, vars: { "--c": c.hex },
        title: c.label, "aria-label": c.label,
        onclick: () => this.setPref({ color: this.prefs.color === c.id ? null : c.id }),
      })));

    const hourSel = $("#opt-hour");
    hourSel.replaceChildren(...Array.from({ length: 24 }, (_, i) =>
      h("option", { value: i }, `${String(i).padStart(2, "0")}:00`)));
    hourSel.addEventListener("change", () => this.setPref({ hour: Number(hourSel.value) }));

    $("#opt-when").querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", () => this.setPref({ when: b.dataset.value })));

    const range = $("#opt-hours");
    range.max = o.max_hours;
    range.addEventListener("input", () => {
      $("#opt-hours-out").textContent = `${range.value} h`;
      this.setPref({ hours: Number(range.value) });
    });

    $("#opt-trip").addEventListener("change", (e) => {
      const trip = e.target.checked;
      this.setPref({ trip }, { refetch: Boolean(this.prefs.destination) });
      this.renderDestination();
    });

    $("#see-outfit").addEventListener("click", () =>
      $("#result").scrollIntoView({ behavior: "smooth", block: "start" }));

    this.syncOptions();
    this.renderDestination();
    $("#options").hidden = !this.origin;
  },

  renderDestination() {
    const box = $("#opt-destination");
    box.hidden = !this.prefs.trip;
    box.replaceChildren();
    if (!this.prefs.trip) return;
    const dest = this.prefs.destination;
    if (dest) {
      box.append(h("div", { class: "dest-chosen" },
        h("span", {}, "🧳 ", h("strong", {}, dest.name), " ",
          h("small", {}, [dest.region, dest.country].filter(Boolean).join(", "))),
        h("button", { type: "button", class: "link-btn",
          onclick: () => { this.setPref({ destination: null }); this.renderDestination(); } }, "Cambiar")));
    } else {
      box.append(createLocationSearch({
        label: "¿A qué zona vas?",
        placeholder: "Ciudad de destino",
        onSelect: (loc) => { this.setPref({ destination: loc }); this.renderDestination(); },
        autofocus: true,
      }));
    }
  },

  syncOptions() {
    const p = this.prefs;
    const mark = (sel, attr, value) =>
      document.querySelectorAll(`${sel} [data-value]`).forEach((b) =>
        b.setAttribute(attr, String(b.dataset.value === (value ?? ""))));
    mark("#opt-mood", "aria-pressed", p.mood);
    mark("#opt-occasion", "aria-checked", p.occasion);
    mark("#opt-fit", "aria-checked", p.fit);
    mark("#opt-color", "aria-pressed", p.color);
    mark("#opt-when", "aria-checked", p.when);
    $("#opt-hour-wrap").hidden = p.when === "now";
    $("#opt-hour").value = String(p.hour);
    $("#opt-hours").value = String(p.hours);
    $("#opt-hours-out").textContent = `${p.hours} h`;
    $("#opt-trip").checked = p.trip;
  },
};

// ====================================== Botón flotante "Ver outfit"
const floating = $("#to-outfit");
let resultVisible = true;
function updateFloatingButton() {
  const onOutfit = currentRoute().path === "/que-me-pongo";
  floating.hidden = !(onOutfit && outfitView.result && !resultVisible);
}
if ("IntersectionObserver" in window) {
  new IntersectionObserver(([entry]) => {
    resultVisible = entry.isIntersecting;
    updateFloatingButton();
  }, { threshold: 0.05 }).observe($("#result"));
}
floating.addEventListener("click", () =>
  $("#result").scrollIntoView({ behavior: "smooth", block: "start" }));

window.addEventListener("hashchange", navigate);
navigate();
