// Sección "Mi armario": listado, alta de prendas con identificación y edición.

import { $, api, getOptions, h, toast } from "./core.js";

const MAX_PHOTOS = 3;
const PHOTO_HINTS = [
  { icon: "👕", title: "La prenda", text: "Entera, extendida y con buena luz" },
  { icon: "🏷️", title: "Etiqueta de marca", text: "La del cuello o la cintura" },
  { icon: "🧵", title: "Etiqueta de composición", text: "La de lavado: dice los materiales exactos" },
];
const LEVELS = [
  { id: 0, label: "Calor", hint: "24 °C o más" },
  { id: 1, label: "Templado", hint: "18-24 °C" },
  { id: 2, label: "Fresco", hint: "13-18 °C" },
  { id: 3, label: "Frío suave", hint: "8-13 °C" },
  { id: 4, label: "Frío", hint: "3-8 °C" },
  { id: 5, label: "Mucho frío", hint: "menos de 3 °C" },
];
const PATTERN_LABELS = { liso: "Liso", rayas: "Rayas", cuadros: "Cuadros", estampado: "Estampado", lunares: "Lunares", otro: "Otro" };
const UNCONFIRMED_LABELS = { marca: "marca", modelo: "modelo", referencia: "referencia", composicion: "composición", colores: "colores", tipo: "tipo de prenda" };
const IDENTIFY_STEPS = ["Mirando la foto…", "Leyendo las etiquetas…", "Buscando la ficha del producto…", "Comprobando materiales y colores…", "Casi está…"];

// ------------------------------------------------------------ imágenes
/** Reduce la foto a 1600 px en JPEG. De paso elimina los metadatos EXIF (incluida la ubicación GPS). */
async function prepareImage(file) {
  if (!file.type.startsWith("image/")) throw new Error("Ese archivo no es una imagen.");
  let source;
  try {
    source = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    source = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("No hemos podido leer esa imagen. Prueba con una foto JPG o PNG."));
      img.src = URL.createObjectURL(file);
    });
  }
  const scale = Math.min(1, 1600 / Math.max(source.width, source.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(source.width * scale);
  canvas.height = Math.round(source.height * scale);
  canvas.getContext("2d").drawImage(source, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.86));
  if (!blob) throw new Error("No hemos podido procesar la foto.");
  return { blob, url: URL.createObjectURL(blob) };
}

// ------------------------------------------------------------ helpers de vista
const pct = (n) => (n === null || n === undefined ? "" : `${Number.isInteger(n) ? n : n.toFixed(1)} %`);
const materialsText = (d) => d.materials.length
  ? d.materials.map((m) => `${m.percent ? pct(m.percent) + " " : ""}${m.fiber}`).join(" · ")
  : "Composición desconocida";
const brandLine = (d) => [d.brand, d.model].filter(Boolean).join(" · ");
const confidenceLabel = (c) => (c >= 0.8 ? "Alta" : c >= 0.5 ? "Media" : "Baja");

function colorDots(colors) {
  return h("span", { class: "dots" }, colors.map((c) =>
    h("i", { vars: { "--c": c.hex || "#ccc" }, title: c.name })));
}

function emptyDetails() {
  return {
    name: "", base_type: "", brand: null, model: null, reference: null, colors: [], materials: [],
    pattern: "liso", levels: [], waterproof: false, windproof: false, occasions: [], tags: [],
    fit: "unisex", product_url: null, notes: null,
  };
}

// ================================================================ vista
export const wardrobeView = {
  started: false,
  options: null,
  items: [],
  loading: true,
  error: null,
  filter: "todas",
  flow: null, // estado del alta de una prenda

  async enter() {
    if (!this.started) {
      this.started = true;
      $("#wd-add-btn").addEventListener("click", () => this.startFlow());
      $("#wd-dialog").addEventListener("click", (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); });
    }
    this.render();
    try {
      [this.options, this.items] = await Promise.all([
        getOptions(),
        api("/wardrobe/items").then((d) => d.items),
      ]);
      this.error = null;
    } catch (err) {
      this.error = err.message;
    }
    this.loading = false;
    this.render();
  },

  render() {
    const main = $("#wd-main");
    $("#wd-add-btn").hidden = Boolean(this.flow);
    $("#wd-count").textContent = this.loading ? "" : this.items.length === 1 ? "1 prenda" : `${this.items.length} prendas`;
    if (this.flow) return main.replaceChildren(this.renderFlow());
    if (this.error) {
      return main.replaceChildren(h("div", { class: "card error-card", role: "alert" },
        h("span", { "aria-hidden": "true" }, "⚠️"), h("p", {}, this.error)));
    }
    if (this.loading) {
      return main.replaceChildren(h("div", { class: "wd-grid" },
        [1, 2, 3, 4].map(() => h("div", { class: "skeleton", style: { aspectRatio: "4 / 6" } }))));
    }
    if (!this.items.length) {
      return main.replaceChildren(h("div", { class: "card wd-empty" },
        h("span", { class: "big", "aria-hidden": "true" }, "🧺"),
        h("h2", {}, "Tu armario está vacío"),
        h("p", {}, "Haz una foto a una prenda y la reconoceremos: marca, modelo, colores y materiales. Así tus recomendaciones saldrán de tu propia ropa."),
        h("button", { type: "button", class: "btn btn-primary", onclick: () => this.startFlow() }, "Añadir mi primera prenda")));
    }
    main.replaceChildren(this.renderFilters(), this.renderGrid());
  },

  renderFilters() {
    const counts = {};
    this.items.forEach((i) => { counts[i.details.slot] = (counts[i.details.slot] || 0) + 1; });
    const slots = this.options.slots.filter((s) => counts[s.id]);
    if (this.filter !== "todas" && !counts[this.filter]) this.filter = "todas";
    const chip = (id, label, n) => h("button", {
      type: "button", class: "chip", "aria-pressed": String(this.filter === id),
      onclick: () => { this.filter = id; this.render(); },
    }, label, h("span", { class: "chip-count" }, String(n)));
    return h("div", { class: "chips wd-filters", role: "group", "aria-label": "Filtrar por tipo" },
      chip("todas", "Todas", this.items.length), slots.map((s) => chip(s.id, s.label, counts[s.id])));
  },

  renderGrid() {
    const items = this.filter === "todas" ? this.items : this.items.filter((i) => i.details.slot === this.filter);
    return h("ul", { class: "wd-grid" }, items.map((item) => {
      const d = item.details;
      const bg = d.colors[0]?.hex || "#ddd";
      return h("li", {},
        h("button", { type: "button", class: "wd-card", onclick: () => this.openItem(item) },
          h("div", { class: "wd-photo", vars: { "--c": bg } },
            item.photos.length
              ? h("img", { src: item.photos[0], alt: "", loading: "lazy" })
              : h("span", { class: "wd-photo-icon", "aria-hidden": "true" }, d.icon)),
          h("div", { class: "wd-card-body" },
            h("span", { class: "wd-type" }, d.base_type_name),
            h("strong", { class: "wd-name" }, d.name),
            brandLine(d) ? h("span", { class: "wd-brand" }, brandLine(d)) : null,
            h("span", { class: "wd-meta" }, colorDots(d.colors), h("span", {}, materialsText(d))),
            d.materials_complete ? null : h("span", { class: "badge badge-warn" }, "Composición sin confirmar"))));
    }));
  },

  // ---------------------------------------------------------- detalle
  openItem(item) {
    const dialog = $("#wd-dialog");
    const d = item.details;
    const row = (label, value) => value ? h("div", { class: "kv" }, h("dt", {}, label), h("dd", {}, value)) : null;
    dialog.replaceChildren(h("div", { class: "sheet-inner" },
      h("div", { class: "sheet-head" },
        h("div", {}, h("p", { class: "eyebrow" }, d.base_type_name), h("h2", {}, d.name)),
        h("button", { type: "button", class: "icon-btn", "aria-label": "Cerrar", onclick: () => dialog.close() }, "✕")),
      item.photos.length ? h("div", { class: "gallery" }, item.photos.map((src) => h("img", { src, alt: `Foto de ${d.name}` }))) : null,
      h("dl", { class: "kvs" },
        row("Marca", d.brand), row("Modelo", d.model), row("Referencia", d.reference),
        row("Colores", d.colors.length ? h("span", { class: "color-list" }, d.colors.map((c) =>
          h("span", { class: "color-pill" }, h("i", { vars: { "--c": c.hex } }), c.name))) : null),
        row("Composición", h("span", {}, materialsText(d), " ",
          d.materials_complete ? h("span", { class: "badge badge-live" }, "Exacta") : h("span", { class: "badge badge-warn" }, "Sin confirmar"))),
        row("Estampado", PATTERN_LABELS[d.pattern]),
        row("Abriga para", d.levels.map((lv) => LEVELS[lv].label).join(", ")),
        row("Protección", [d.waterproof && "Impermeable", d.windproof && "Cortavientos"].filter(Boolean).join(" · ") || null),
        row("Ocasiones", d.occasions.map((o) => this.options.occasions.find((x) => x.id === o)?.label).join(", ")),
        row("Ficha", d.product_url ? h("a", { href: d.product_url, target: "_blank", rel: "noopener noreferrer" }, "Ver producto ↗") : null),
        row("Notas", d.notes)),
      h("div", { class: "sheet-actions" },
        h("button", { type: "button", class: "btn btn-ghost btn-small danger", onclick: () => this.deleteItem(item) }, "Eliminar"),
        h("button", { type: "button", class: "btn btn-primary btn-small", onclick: () => this.editItem(item) }, "Editar datos"))));
    if (!dialog.open) dialog.showModal();
  },

  editItem(item) {
    const dialog = $("#wd-dialog");
    dialog.replaceChildren(h("div", { class: "sheet-inner" },
      h("div", { class: "sheet-head" }, h("h2", {}, "Editar prenda"),
        h("button", { type: "button", class: "icon-btn", "aria-label": "Cerrar", onclick: () => dialog.close() }, "✕")),
      this.detailsForm(structuredClone(item.details), {
        submitLabel: "Guardar cambios",
        onCancel: () => this.openItem(item),
        onSubmit: async (details) => {
          const updated = await api(`/wardrobe/items/${item.id}`, { method: "PUT", body: JSON.stringify(details) });
          this.items = this.items.map((i) => (i.id === item.id ? updated : i));
          this.render();
          this.openItem(updated);
          toast("Cambios guardados");
        },
      })));
  },

  async deleteItem(item) {
    if (!confirm(`¿Eliminar «${item.details.name}» de tu armario?`)) return;
    try {
      await api(`/wardrobe/items/${item.id}`, { method: "DELETE" });
      this.items = this.items.filter((i) => i.id !== item.id);
      $("#wd-dialog").close();
      this.render();
      toast("Prenda eliminada");
    } catch (err) {
      toast(err.message);
    }
  },

  // ---------------------------------------------------------- alta
  startFlow() {
    this.flow = { step: "photos", photos: [], url: "", description: "", rejected: [], result: null, error: null };
    this.render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  },

  closeFlow() {
    this.flow?.photos.forEach((p) => URL.revokeObjectURL(p.url));
    this.flow = null;
    this.render();
  },

  goto(step, extra = {}) {
    Object.assign(this.flow, { step, error: null }, extra);
    this.render();
    $("#wd-main").scrollIntoView({ behavior: "smooth", block: "start" });
  },

  renderFlow() {
    const f = this.flow;
    const stepIndex = { photos: 0, identifying: 0, proposal: 1, help: 1, review: 2 }[f.step];
    const steps = ["Foto", "Confirmar", "Guardar"];
    const body = {
      photos: () => this.stepPhotos(),
      identifying: () => this.stepIdentifying(),
      proposal: () => this.stepProposal(),
      help: () => this.stepHelp(),
      review: () => this.stepReview(),
    }[f.step]();
    return h("div", { class: "flow" },
      h("div", { class: "flow-top" },
        h("button", { type: "button", class: "link-btn", onclick: () => this.closeFlow() }, "← Volver al armario"),
        h("ol", { class: "stepper", "aria-label": "Pasos" }, steps.map((s, i) =>
          h("li", { class: i < stepIndex ? "done" : i === stepIndex ? "current" : "", "aria-current": i === stepIndex ? "step" : null },
            h("span", {}, i < stepIndex ? "✓" : String(i + 1)), s)))),
      f.error ? h("div", { class: "card error-card", role: "alert" }, h("span", { "aria-hidden": "true" }, "⚠️"), h("p", {}, f.error)) : null,
      body);
  },

  photoPicker() {
    const f = this.flow;
    const input = h("input", { type: "file", accept: "image/*", multiple: true, class: "sr-only", id: "wd-file" });
    input.addEventListener("change", async () => {
      const files = [...input.files].slice(0, MAX_PHOTOS - f.photos.length);
      for (const file of files) {
        try {
          f.photos.push(await prepareImage(file));
        } catch (err) {
          f.error = err.message;
        }
      }
      this.render();
    });
    const tiles = PHOTO_HINTS.map((hint, i) => {
      const photo = f.photos[i];
      if (photo) {
        return h("div", { class: "ph-tile filled" },
          h("img", { src: photo.url, alt: `Foto ${i + 1}` }),
          h("button", { type: "button", class: "ph-remove", "aria-label": `Quitar foto ${i + 1}`,
            onclick: () => { URL.revokeObjectURL(photo.url); f.photos.splice(i, 1); this.render(); } }, "✕"),
          h("span", { class: "ph-caption" }, hint.title));
      }
      const isNext = i === f.photos.length;
      return h(isNext ? "label" : "div", { class: `ph-tile ${isNext ? "next" : "ghost"}`, for: isNext ? "wd-file" : null },
        h("span", { class: "ph-icon", "aria-hidden": "true" }, hint.icon),
        h("strong", {}, hint.title),
        h("small", {}, hint.text),
        isNext ? h("span", { class: "ph-cta" }, f.photos.length ? "＋ Añadir foto" : "📷 Hacer o subir foto") : null);
    });
    return h("div", {}, input, h("div", { class: "ph-grid" }, tiles));
  },

  extraInfoFields(open) {
    const f = this.flow;
    const url = h("input", { type: "url", inputmode: "url", placeholder: "https://…", value: f.url, id: "wd-url" });
    url.addEventListener("input", () => { f.url = url.value; this.syncIdentifyButton(); });
    const desc = h("textarea", { rows: 3, placeholder: "Marca, modelo, materiales, color… lo que sepas o ponga la etiqueta", id: "wd-desc" }, f.description);
    desc.addEventListener("input", () => { f.description = desc.value; this.syncIdentifyButton(); });
    const fields = h("div", { class: "form-grid" },
      h("label", { class: "field" }, h("span", {}, "Enlace del producto (web de la marca o tienda)"), url),
      h("label", { class: "field" }, h("span", {}, "Descripción"), desc));
    return open ? fields : h("details", { class: "more" }, h("summary", {}, "¿Tienes el enlace o algún dato? (opcional)"), fields);
  },

  hasInput() {
    const f = this.flow;
    return f.photos.length > 0 || f.url.trim() || f.description.trim();
  },

  syncIdentifyButton() {
    const btn = $("#wd-identify");
    if (btn) btn.disabled = !this.hasInput();
  },

  stepPhotos() {
    return h("section", { class: "card flow-card" },
      h("h2", {}, "Haz una foto a tu prenda"),
      h("p", { class: "muted" }, "Con la foto de las etiquetas podemos saber la marca y los materiales exactos. Puedes subir hasta 3 fotos."),
      this.photoPicker(),
      this.extraInfoFields(false),
      h("div", { class: "flow-actions" },
        h("button", { type: "button", class: "btn btn-primary", id: "wd-identify", disabled: !this.hasInput(), onclick: () => this.identify() },
          "Identificar prenda"),
        h("button", { type: "button", class: "link-btn", onclick: () => this.goto("review", { draft: emptyDetails(), source: "manual" }) },
          "Prefiero rellenarla a mano")));
  },

  stepIdentifying() {
    const msg = h("p", { class: "id-msg", "aria-live": "polite" }, IDENTIFY_STEPS[0]);
    let i = 0;
    const timer = setInterval(() => {
      if (!msg.isConnected) return clearInterval(timer);
      i = Math.min(i + 1, IDENTIFY_STEPS.length - 1);
      msg.textContent = IDENTIFY_STEPS[i];
    }, 4000);
    return h("section", { class: "card flow-card identifying" },
      h("div", { class: "scan" },
        this.flow.photos[0] ? h("img", { src: this.flow.photos[0].url, alt: "" }) : h("span", { class: "big" }, "🔎"),
        h("span", { class: "scan-line", "aria-hidden": "true" })),
      msg,
      h("p", { class: "muted small" }, "Buscamos la ficha exacta del producto. Puede tardar hasta un minuto."));
  },

  async identify() {
    const f = this.flow;
    const form = new FormData();
    f.photos.forEach((p, i) => form.append("photos", p.blob, `foto-${i + 1}.jpg`));
    if (f.url.trim()) form.append("product_url", f.url.trim());
    if (f.description.trim()) form.append("description", f.description.trim());
    if (f.rejected.length) form.append("rejected", JSON.stringify(f.rejected));
    const source = f.photos.length ? "foto" : f.url.trim() ? "enlace" : "descripcion";
    this.goto("identifying");
    try {
      const result = await api("/wardrobe/identify", { method: "POST", body: form });
      if (this.flow !== f) return; // el usuario salió mientras tanto
      if (result.status === "desconocida" || !result.candidate) {
        this.goto("help", { result, source, error: null });
      } else {
        this.goto("proposal", { result, source });
      }
    } catch (err) {
      if (this.flow !== f) return;
      this.goto(f.rejected.length || f.url || f.description ? "help" : "photos");
      f.error = err.message;
      this.render();
    }
  },

  stepProposal() {
    const { result } = this.flow;
    const d = result.candidate;
    const unconfirmed = result.unconfirmed.map((u) => UNCONFIRMED_LABELS[u] || u);
    const level = confidenceLabel(result.confidence);
    return h("section", { class: "card flow-card" },
      h("h2", {}, "¿Es esta tu prenda?"),
      h("div", { class: "proposal" },
        h("div", { class: "wd-photo proposal-photo", vars: { "--c": d.colors[0]?.hex || "#ddd" } },
          this.flow.photos[0] ? h("img", { src: this.flow.photos[0].url, alt: "Tu foto" }) : h("span", { class: "wd-photo-icon" }, d.icon)),
        h("div", { class: "proposal-info" },
          h("span", { class: "wd-type" }, d.base_type_name),
          h("strong", { class: "proposal-name" }, d.name),
          brandLine(d) ? h("span", { class: "wd-brand" }, brandLine(d)) : h("span", { class: "wd-brand muted" }, "Marca sin identificar"),
          d.reference ? h("span", { class: "muted small" }, `Ref. ${d.reference}`) : null,
          h("div", { class: `confidence c-${level.toLowerCase()}` },
            h("span", {}, `Coincidencia ${level.toLowerCase()}`),
            h("span", { class: "meter" }, h("i", { style: { width: `${Math.round(result.confidence * 100)}%` } }))))),
      h("dl", { class: "kvs" },
        h("div", { class: "kv" }, h("dt", {}, "Colores"), h("dd", {}, d.colors.length
          ? h("span", { class: "color-list" }, d.colors.map((c) => h("span", { class: "color-pill" }, h("i", { vars: { "--c": c.hex } }), c.name)))
          : "—")),
        h("div", { class: "kv" }, h("dt", {}, "Composición"), h("dd", {}, materialsText(d), " ",
          d.materials_complete ? h("span", { class: "badge badge-live" }, "Exacta") : h("span", { class: "badge badge-warn" }, "Sin confirmar"))),
        d.waterproof || d.windproof ? h("div", { class: "kv" }, h("dt", {}, "Protección"),
          h("dd", {}, [d.waterproof && "Impermeable", d.windproof && "Cortavientos"].filter(Boolean).join(" · "))) : null),
      result.message ? h("blockquote", { class: "ai-note" }, result.message) : null,
      unconfirmed.length ? h("p", { class: "warn-line" }, "⚠️ Sin confirmar: ", unconfirmed.join(", "),
        ". Si quieres que sea exacto, pulsa «No es esta» y añade el enlace o una foto de la etiqueta.") : null,
      result.alternatives.length ? h("p", { class: "muted small" }, "También podría ser: ",
        result.alternatives.map((a) => a.label).join(" · ")) : null,
      result.sources.length ? h("p", { class: "sources" }, "Fuentes: ", result.sources.map((s) => {
        let host = s;
        try { host = new URL(s).hostname.replace(/^www\./, ""); } catch { /* url rara */ }
        return h("a", { href: s, target: "_blank", rel: "noopener noreferrer" }, host);
      })) : null,
      h("div", { class: "flow-actions" },
        h("button", { type: "button", class: "btn btn-primary", onclick: () => this.save(d) }, "Sí, es esta"),
        h("button", { type: "button", class: "btn btn-ghost", onclick: () => this.reject() }, "No es esta"),
        h("button", { type: "button", class: "link-btn", onclick: () => this.goto("review", { draft: structuredClone(d) }) },
          "Es esta, pero quiero corregir algún dato")));
  },

  reject() {
    const d = this.flow.result.candidate;
    const label = [d.brand, d.model || d.name].filter(Boolean).join(" · ");
    if (label && !this.flow.rejected.includes(label)) this.flow.rejected.push(label);
    this.goto("help");
  },

  stepHelp() {
    const f = this.flow;
    const unknown = f.result && (f.result.status === "desconocida" || !f.result.candidate);
    return h("section", { class: "card flow-card" },
      h("h2", {}, "Ayúdanos a encontrarla"),
      h("p", { class: "muted" }, unknown && f.result?.message
        ? f.result.message
        : "Pega el enlace del producto o escribe lo que sepas de ella. Una foto de la etiqueta de composición también ayuda mucho."),
      f.rejected.length ? h("p", { class: "muted small" }, "Descartadas: ", f.rejected.join(" · ")) : null,
      this.extraInfoFields(true),
      h("details", { class: "more", open: f.photos.length < 2 }, h("summary", {}, `Fotos (${f.photos.length}/${MAX_PHOTOS})`), this.photoPicker()),
      h("div", { class: "flow-actions" },
        h("button", { type: "button", class: "btn btn-primary", id: "wd-identify", disabled: !this.hasInput(), onclick: () => this.identify() },
          "Volver a buscar"),
        h("button", { type: "button", class: "link-btn",
          onclick: () => this.goto("review", { draft: f.result?.candidate ? structuredClone(f.result.candidate) : emptyDetails() }) },
          "Rellenar los datos a mano")));
  },

  stepReview() {
    const f = this.flow;
    return h("section", { class: "card flow-card" },
      h("h2", {}, "Revisa los datos"),
      h("p", { class: "muted" }, "Cuanto más exactos, mejores serán tus recomendaciones."),
      this.detailsForm(f.draft, {
        submitLabel: "Guardar en mi armario",
        onCancel: () => this.goto(f.result?.candidate ? "proposal" : "photos"),
        onSubmit: (details) => this.save(details, f.source, true),
      }));
  },

  async save(details, source = this.flow.source, rethrow = false) {
    const f = this.flow;
    const form = new FormData();
    form.append("details", JSON.stringify(details));
    form.append("source", source || "foto");
    if (f.result?.confidence !== undefined && source !== "manual") form.append("confidence", String(f.result.confidence));
    f.photos.forEach((p, i) => form.append("photos", p.blob, `foto-${i + 1}.jpg`));
    try {
      const item = await api("/wardrobe/items", { method: "POST", body: form });
      this.items = [item, ...this.items];
      this.closeFlow();
      toast(`«${item.details.name}» guardada en tu armario`);
    } catch (err) {
      if (rethrow) throw err; // el formulario muestra el error junto al botón
      f.error = err.message;
      this.render();
    }
  },

  // ---------------------------------------------------------- formulario
  detailsForm(d, { submitLabel, onSubmit, onCancel }) {
    const o = this.options;
    const err = h("p", { class: "form-error", role: "alert", hidden: true });
    const text = (key, label, attrs = {}) => {
      const input = h("input", { type: "text", value: d[key] ?? "", ...attrs });
      input.addEventListener("input", () => { d[key] = input.value.trim() || null; });
      return h("label", { class: "field" }, h("span", {}, label), input);
    };

    // Tipo de prenda, agrupado por parte del cuerpo
    const typeSel = h("select", { required: true },
      h("option", { value: "" }, "Elige un tipo…"),
      o.slots.map((s) => h("optgroup", { label: s.label },
        o.garment_types.filter((g) => g.slot === s.id).map((g) =>
          h("option", { value: g.id, selected: g.id === d.base_type }, `${g.icon} ${g.name}`)))));
    typeSel.addEventListener("change", () => { d.base_type = typeSel.value; });

    // Colores
    const colorsBox = h("div", { class: "rows" });
    const renderColors = () => colorsBox.replaceChildren(
      ...d.colors.map((c, i) => {
        const name = h("input", { type: "text", value: c.name, "aria-label": "Nombre del color", placeholder: "p. ej. verde botella" });
        name.addEventListener("input", () => { c.name = name.value; });
        const sel = h("select", { "aria-label": "Color de la paleta" }, o.colors.map((pc) =>
          h("option", { value: pc.id, selected: pc.id === c.palette_id }, pc.label)));
        const dot = h("i", { class: "swatch-dot", vars: { "--c": c.hex || o.colors.find((x) => x.id === c.palette_id)?.hex } });
        sel.addEventListener("change", () => {
          c.palette_id = sel.value;
          c.hex = o.colors.find((x) => x.id === sel.value).hex;
          dot.style.setProperty("--c", c.hex);
        });
        return h("div", { class: "row-line" }, dot, name, sel,
          h("button", { type: "button", class: "icon-btn", "aria-label": "Quitar color", onclick: () => { d.colors.splice(i, 1); renderColors(); } }, "✕"));
      }),
      h("button", { type: "button", class: "link-btn", onclick: () => {
        d.colors.push({ name: "", palette_id: "negro", hex: o.colors[0].hex }); renderColors();
      } }, "＋ Añadir color"));
    renderColors();

    // Composición
    const total = h("span", { class: "total" });
    const updateTotal = () => {
      const sum = d.materials.reduce((s, m) => s + (Number(m.percent) || 0), 0);
      const known = d.materials.length && d.materials.every((m) => m.percent);
      total.textContent = d.materials.length ? `Total: ${Math.round(sum * 10) / 10} %` : "";
      total.className = `total ${known && Math.abs(sum - 100) <= 1 ? "ok" : d.materials.length ? "warn" : ""}`;
      total.title = known && Math.abs(sum - 100) <= 1 ? "Composición completa" : "Si conoces todos los porcentajes, deberían sumar 100 %";
    };
    const matBox = h("div", { class: "rows" });
    const renderMaterials = () => {
      matBox.replaceChildren(
        ...d.materials.map((m, i) => {
          const fiber = h("input", { type: "text", value: m.fiber, "aria-label": "Material", placeholder: "algodón, lana, poliéster…", list: "fibers" });
          fiber.addEventListener("input", () => { m.fiber = fiber.value; });
          const percent = h("input", { type: "number", min: 1, max: 100, step: 0.1, value: m.percent ?? "", "aria-label": "Porcentaje", placeholder: "%", class: "pct" });
          percent.addEventListener("input", () => { m.percent = percent.value === "" ? null : Number(percent.value); updateTotal(); });
          return h("div", { class: "row-line" }, fiber, percent, h("span", { class: "unit" }, "%"),
            h("button", { type: "button", class: "icon-btn", "aria-label": "Quitar material", onclick: () => { d.materials.splice(i, 1); renderMaterials(); } }, "✕"));
        }),
        h("div", { class: "row-foot" },
          h("button", { type: "button", class: "link-btn", onclick: () => { d.materials.push({ fiber: "", percent: null }); renderMaterials(); } }, "＋ Añadir material"),
          total));
      updateTotal();
    };
    renderMaterials();

    // Elección múltiple con chips
    const multi = (values, items, label) => h("fieldset", { class: "field" },
      h("legend", {}, label),
      h("div", { class: "chips" }, items.map((it) => {
        const btn = h("button", { type: "button", class: "chip", "aria-pressed": String(values.includes(it.id)) }, it.label);
        btn.addEventListener("click", () => {
          const i = values.indexOf(it.id);
          i >= 0 ? values.splice(i, 1) : values.push(it.id);
          btn.setAttribute("aria-pressed", String(i < 0));
        });
        return btn;
      })));

    const check = (key, label) => {
      const input = h("input", { type: "checkbox", checked: d[key] });
      input.addEventListener("change", () => { d[key] = input.checked; });
      return h("label", { class: "check" }, input, h("span", {}, label));
    };

    const patternSel = h("select", {}, o.patterns.map((p) => h("option", { value: p, selected: p === d.pattern }, PATTERN_LABELS[p] || p)));
    patternSel.addEventListener("change", () => { d.pattern = patternSel.value; });

    const notes = h("textarea", { rows: 2, placeholder: "Talla, cómo te queda, cuidados…" }, d.notes || "");
    notes.addEventListener("input", () => { d.notes = notes.value.trim() || null; });

    const submit = h("button", { type: "submit", class: "btn btn-primary" }, submitLabel);
    const form = h("form", { class: "details-form", novalidate: true },
      h("datalist", { id: "fibers" }, ["algodón", "algodón orgánico", "poliéster", "poliéster reciclado", "elastano", "lana", "lana merino",
        "cachemira", "lino", "viscosa", "lyocell", "modal", "nailon", "poliamida", "acrílico", "seda", "cuero", "plumón", "pluma"].map((v) => h("option", { value: v }))),
      h("div", { class: "form-grid two" },
        text("name", "Nombre", { required: true, placeholder: "p. ej. Jersey de merino verde" }),
        h("label", { class: "field" }, h("span", {}, "Tipo de prenda"), typeSel),
        text("brand", "Marca"),
        text("model", "Modelo"),
        text("reference", "Referencia"),
        h("label", { class: "field" }, h("span", {}, "Estampado"), patternSel)),
      h("fieldset", { class: "field" }, h("legend", {}, "Colores"), colorsBox),
      h("fieldset", { class: "field" }, h("legend", {}, "Composición"), matBox),
      multi(d.levels, LEVELS.map((l) => ({ id: l.id, label: `${l.label} (${l.hint})` })), "¿Con qué tiempo te la pondrías?"),
      h("div", { class: "checks-row" }, check("waterproof", "Impermeable"), check("windproof", "Cortavientos")),
      multi(d.occasions, o.occasions.map((x) => ({ id: x.id, label: `${x.icon} ${x.label}` })), "Ocasiones"),
      text("product_url", "Enlace del producto", { type: "url", placeholder: "https://…" }),
      h("label", { class: "field" }, h("span", {}, "Notas"), notes),
      err,
      h("div", { class: "flow-actions" }, submit,
        h("button", { type: "button", class: "btn btn-ghost", onclick: onCancel }, "Cancelar")));

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      err.hidden = true;
      const problem = !d.name?.trim() ? "Ponle un nombre a la prenda."
        : !d.base_type ? "Elige qué tipo de prenda es."
          : !d.colors.length ? "Añade al menos un color: lo usamos para combinar tus prendas."
          : d.materials.some((m) => !m.fiber?.trim()) ? "Escribe el nombre de cada material o quita las filas vacías."
            : d.materials.reduce((s, m) => s + (Number(m.percent) || 0), 0) > 101 ? "La composición suma más del 100 %."
              : null;
      if (problem) { err.textContent = problem; err.hidden = false; return; }
      d.colors = d.colors.filter((c) => c.name.trim() || c.palette_id).map((c) => ({ ...c, name: c.name.trim() }));
      submit.disabled = true;
      try {
        await onSubmit(d);
      } catch (e2) {
        err.textContent = e2.message;
        err.hidden = false;
      } finally {
        submit.disabled = false;
      }
    });
    return form;
  },
};
