// Sección "Mis outfits": guarda looks con foto y descripción y te recomienda cuál ponerte.

import { $, api, getOptions, h, toast } from "./core.js";
import { prepareImage } from "./wardrobe.js";

const MAX_PHOTOS = 4;
const SEASONS = [
  { id: "primavera", label: "🌸 Primavera" }, { id: "verano", label: "☀️ Verano" },
  { id: "otoño", label: "🍂 Otoño" }, { id: "invierno", label: "❄️ Invierno" },
];
const EXAMPLES = ["Una boda en verano", "Cena con amigos", "Reunión de trabajo", "Plan tranquilo de domingo", "Salir de fiesta"];

const seasonLabel = (id) => SEASONS.find((s) => s.id === id)?.label || id;
const fmtDate = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString("es-ES", { day: "numeric", month: "long" });

function wornText(o) {
  if (!o.worn_count) return "Aún no te lo has puesto";
  return `Te lo has puesto ${o.worn_count === 1 ? "1 vez" : `${o.worn_count} veces`} · la última, el ${fmtDate(o.last_worn)}`;
}

function tags(o) {
  return h("div", { class: "chips" },
    o.occasion_label ? h("span", { class: "chip static small-chip" }, o.occasion_label) : null,
    o.seasons.map((s) => h("span", { class: "chip static small-chip" }, seasonLabel(s))));
}

export const outfitsView = {
  started: false,
  options: null,
  outfits: [],
  wardrobe: [],
  loading: true,
  error: null,
  query: "",
  results: null, // null = sin búsqueda
  searching: false,
  form: null, // alta de un outfit

  async enter() {
    if (!this.started) {
      this.started = true;
      $("#of-add-btn").addEventListener("click", () => this.startForm());
      $("#of-dialog").addEventListener("click", (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); });
    }
    this.render();
    try {
      const [options, outfits, wardrobe] = await Promise.all([
        getOptions(), api("/outfits").then((d) => d.outfits), api("/wardrobe/items").then((d) => d.items),
      ]);
      Object.assign(this, { options, outfits, wardrobe, error: null });
    } catch (err) {
      this.error = err.message;
    }
    this.loading = false;
    this.render();
  },

  render() {
    const main = $("#of-main");
    $("#of-add-btn").hidden = Boolean(this.form);
    $("#of-count").textContent = this.loading ? "" : this.outfits.length === 1 ? "1 outfit guardado" : `${this.outfits.length} outfits guardados`;
    if (this.error) return main.replaceChildren(h("div", { class: "card error-card", role: "alert" }, h("span", {}, "⚠️"), h("p", {}, this.error)));
    if (this.loading) return main.replaceChildren(h("div", { class: "skeleton", style: { height: "300px" } }));
    if (this.form) return main.replaceChildren(this.renderForm());
    if (!this.outfits.length) {
      return main.replaceChildren(h("div", { class: "card wd-empty" },
        h("span", { class: "big", "aria-hidden": "true" }, "📸"),
        h("h2", {}, "Guarda tus looks favoritos"),
        h("p", {}, "Haz una foto a los outfits que te gustan y descríbelos («boda de verano», «oficina los viernes»…). Cuando no sepas qué ponerte, describe tu plan y te diremos cuál elegir."),
        h("button", { type: "button", class: "btn btn-primary", onclick: () => this.startForm() }, "Añadir mi primer outfit")));
    }
    main.replaceChildren(this.renderSearch(), this.renderResults(), this.renderGallery());
  },

  // ------------------------------------------------------------ búsqueda
  renderSearch() {
    const input = h("input", { type: "search", id: "of-query", value: this.query, placeholder: "p. ej. cena con amigos el sábado",
      enterkeyhint: "search", "aria-label": "Describe tu plan" });
    const run = () => this.search(input.value);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); run(); } });
    return h("section", { class: "card of-search" },
      h("h2", {}, "¿Qué me pongo para…?"),
      h("p", { class: "muted small" }, "Describe tu plan y te recomendamos el outfit que mejor encaja de los que has guardado."),
      h("div", { class: "search-line" }, h("div", { class: "search-box grow" }, input),
        h("button", { type: "button", class: "btn btn-primary", onclick: run, disabled: this.searching }, this.searching ? "Buscando…" : "Buscar")),
      h("div", { class: "chips" }, EXAMPLES.map((ex) => h("button", { type: "button", class: "chip small-chip",
        onclick: () => this.search(ex) }, ex))));
  },

  async search(query) {
    query = query.trim();
    if (query.length < 2) return toast("Describe un poco tu plan");
    this.query = query;
    this.searching = true;
    this.render();
    try {
      this.results = (await api("/outfits/search", { method: "POST", body: JSON.stringify({ query }) })).results;
    } catch (err) {
      toast(err.message);
    }
    this.searching = false;
    this.render();
    $("#of-results")?.scrollIntoView({ behavior: "smooth", block: "start" });
  },

  renderResults() {
    if (this.results === null) return null;
    if (!this.results.length) {
      return h("section", { class: "card", id: "of-results" },
        h("p", {}, `Ninguno de tus outfits encaja con «${this.query}».`),
        h("p", { class: "muted small" }, "Prueba con otras palabras (la ocasión, la temporada, un color…) o guarda un outfit nuevo para este plan."),
        h("div", { class: "flow-actions" },
          h("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => { this.results = null; this.render(); } }, "Borrar búsqueda"),
          h("a", { class: "btn btn-ghost btn-small", href: "#/explorar" }, "Buscar ideas en Explorar")));
    }
    const [best, ...rest] = this.results;
    const o = best.outfit;
    return h("section", { id: "of-results", class: "ex-stack" },
      h("article", { class: "card of-best" },
        h("div", { class: "of-best-photos" }, o.photos.map((src) => h("img", { src, alt: `Foto del outfit: ${o.description}` }))),
        h("div", { class: "of-best-info" },
          h("p", { class: "eyebrow" }, `Para «${this.query}» te recomendamos`),
          h("h2", {}, o.description),
          tags(o),
          h("ul", { class: "reasons" }, best.reasons.map((r) => h("li", {}, r))),
          h("p", { class: "muted small" }, wornText(o)),
          h("div", { class: "flow-actions" },
            h("button", { type: "button", class: "btn btn-primary", onclick: () => this.markWorn(o) }, "✓ Me lo pongo hoy"),
            h("button", { type: "button", class: "btn btn-ghost", onclick: () => this.openOutfit(o) }, "Ver detalles")))),
      rest.length ? h("div", {},
        h("h3", { class: "ex-title" }, "Otras opciones"),
        h("ul", { class: "wd-grid" }, rest.map((r) => h("li", {}, this.card(r.outfit, r.matched))))) : null,
      h("button", { type: "button", class: "link-btn", onclick: () => { this.results = null; this.query = ""; this.render(); } }, "Borrar búsqueda"));
  },

  async markWorn(o) {
    try {
      const updated = await api(`/outfits/${o.id}/worn`, { method: "POST" });
      this.replace(updated);
      toast("¡Anotado! Que lo disfrutes");
      this.render();
    } catch (err) {
      toast(err.message);
    }
  },

  replace(updated) {
    this.outfits = this.outfits.map((x) => (x.id === updated.id ? updated : x));
    if (this.results) this.results = this.results.map((r) => (r.outfit.id === updated.id ? { ...r, outfit: updated } : r));
  },

  // ------------------------------------------------------------ galería
  card(o, matched) {
    return h("button", { type: "button", class: "wd-card", onclick: () => this.openOutfit(o) },
      h("div", { class: "wd-photo" }, h("img", { src: o.photos[0], alt: "", loading: "lazy" }),
        o.photos.length > 1 ? h("span", { class: "photo-count" }, `${o.photos.length} 📷`) : null),
      h("div", { class: "wd-card-body" },
        h("strong", { class: "wd-name clamp-2" }, o.description),
        o.occasion_label || o.seasons.length
          ? h("span", { class: "wd-type" }, [o.occasion_label, ...o.seasons].filter(Boolean).join(" · ")) : null,
        matched?.length ? h("span", { class: "small muted" }, "Coincide: ", matched.join(", ")) : null,
        h("span", { class: "small muted" }, o.worn_count ? `👗 ${o.worn_count}×` : "Sin estrenar")));
  },

  renderGallery() {
    return h("section", {},
      h("h2", { class: "ex-title" }, "Todos tus outfits"),
      h("ul", { class: "wd-grid" }, this.outfits.map((o) => h("li", {}, this.card(o)))));
  },

  // ------------------------------------------------------------ detalle
  openOutfit(o) {
    const dialog = $("#of-dialog");
    const items = this.wardrobe.filter((i) => o.item_ids.includes(i.id));
    dialog.replaceChildren(h("div", { class: "sheet-inner" },
      h("div", { class: "sheet-head" },
        h("div", {}, h("p", { class: "eyebrow" }, "Outfit"), h("h2", {}, o.description)),
        h("button", { type: "button", class: "icon-btn", "aria-label": "Cerrar", onclick: () => dialog.close() }, "✕")),
      h("div", { class: "gallery" }, o.photos.map((src) => h("img", { src, alt: `Foto del outfit: ${o.description}` }))),
      tags(o),
      items.length ? h("div", {}, h("h3", { class: "subhead" }, "Prendas de tu armario"),
        h("div", { class: "chips" }, items.map((i) => h("span", { class: "chip static" }, i.details.icon, " ", i.details.name)))) : null,
      h("p", { class: "muted small" }, wornText(o)),
      h("div", { class: "sheet-actions" },
        h("button", { type: "button", class: "btn btn-ghost btn-small danger", onclick: () => this.deleteOutfit(o) }, "Eliminar"),
        h("div", { class: "flow-actions" },
          h("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => this.startForm(o) }, "Editar"),
          h("button", { type: "button", class: "btn btn-primary btn-small", onclick: async () => {
            await this.markWorn(o);
            dialog.close();
          } }, "✓ Me lo pongo hoy")))));
    if (!dialog.open) dialog.showModal();
  },

  async deleteOutfit(o) {
    if (!confirm("¿Eliminar este outfit y sus fotos?")) return;
    try {
      await api(`/outfits/${o.id}`, { method: "DELETE" });
      this.outfits = this.outfits.filter((x) => x.id !== o.id);
      if (this.results) this.results = this.results.filter((r) => r.outfit.id !== o.id);
      $("#of-dialog").close();
      this.render();
      toast("Outfit eliminado");
    } catch (err) {
      toast(err.message);
    }
  },

  // ------------------------------------------------------------ alta / edición
  startForm(existing = null) {
    $("#of-dialog").close();
    this.form = existing
      ? { id: existing.id, photos: [], description: existing.description, occasion: existing.occasion,
          seasons: [...existing.seasons], item_ids: [...existing.item_ids], existingPhotos: existing.photos }
      : { id: null, photos: [], description: "", occasion: null, seasons: [], item_ids: [] };
    this.render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  },

  closeForm() {
    this.form?.photos.forEach((p) => URL.revokeObjectURL(p.url));
    this.form = null;
    this.render();
  },

  renderForm() {
    const f = this.form;
    const editing = Boolean(f.id);
    const err = h("p", { class: "form-error", role: "alert", hidden: true });

    const input = h("input", { type: "file", accept: "image/*", multiple: true, class: "sr-only", id: "of-file" });
    input.addEventListener("change", async () => {
      for (const file of [...input.files].slice(0, MAX_PHOTOS - f.photos.length)) {
        try { f.photos.push(await prepareImage(file)); } catch (e) { toast(e.message); }
      }
      this.render();
    });
    const photos = editing
      ? h("div", { class: "of-photo-row" }, f.existingPhotos.map((src) => h("img", { src, alt: "" })))
      : h("div", { class: "ph-grid four" },
        f.photos.map((p, i) => h("div", { class: "ph-tile filled" }, h("img", { src: p.url, alt: `Foto ${i + 1}` }),
          h("button", { type: "button", class: "ph-remove", "aria-label": `Quitar foto ${i + 1}`,
            onclick: () => { URL.revokeObjectURL(p.url); f.photos.splice(i, 1); this.render(); } }, "✕"))),
        f.photos.length < MAX_PHOTOS ? h("label", { class: "ph-tile next", for: "of-file" }, input,
          h("span", { class: "ph-icon", "aria-hidden": "true" }, "📸"),
          h("strong", {}, f.photos.length ? "Otra foto" : "Foto del outfit"),
          h("small", {}, "De cuerpo entero, con buena luz"),
          h("span", { class: "ph-cta" }, "＋ Añadir")) : null);

    const desc = h("textarea", { rows: 3, placeholder: "¿Para qué es y cómo es? p. ej. «Boda de tarde en verano: vestido verde largo y sandalias doradas»" }, f.description);
    desc.addEventListener("input", () => { f.description = desc.value; });

    const single = h("div", { class: "chips" }, this.options.occasions.map((oc) => {
      const btn = h("button", { type: "button", class: "chip", "aria-pressed": String(f.occasion === oc.id) }, oc.icon, " ", oc.label);
      btn.addEventListener("click", () => {
        f.occasion = f.occasion === oc.id ? null : oc.id;
        single.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === btn && f.occasion === oc.id)));
      });
      return btn;
    }));
    const seasons = h("div", { class: "chips" }, SEASONS.map((s) => {
      const btn = h("button", { type: "button", class: "chip", "aria-pressed": String(f.seasons.includes(s.id)) }, s.label);
      btn.addEventListener("click", () => {
        const i = f.seasons.indexOf(s.id);
        i >= 0 ? f.seasons.splice(i, 1) : f.seasons.push(s.id);
        btn.setAttribute("aria-pressed", String(i < 0));
      });
      return btn;
    }));
    const items = this.wardrobe.length ? h("ul", { class: "pick-grid" }, this.wardrobe.map((item) => {
      const btn = h("button", { type: "button", class: "pick", "aria-pressed": String(f.item_ids.includes(item.id)) },
        h("span", { class: "owned-thumb", vars: { "--c": item.details.colors[0]?.hex || "#ddd" } },
          item.photos.length ? h("img", { src: item.photos[0], alt: "" }) : item.details.icon),
        h("span", {}, item.details.name));
      btn.addEventListener("click", () => {
        const i = f.item_ids.indexOf(item.id);
        i >= 0 ? f.item_ids.splice(i, 1) : f.item_ids.push(item.id);
        btn.setAttribute("aria-pressed", String(i < 0));
      });
      return h("li", {}, btn);
    })) : h("p", { class: "muted small" }, "Cuando tengas prendas en «Mi armario» podrás marcar cuáles salen en el outfit.");

    const submit = h("button", { type: "button", class: "btn btn-primary" }, editing ? "Guardar cambios" : "Guardar outfit");
    submit.addEventListener("click", async () => {
      err.hidden = true;
      const problem = !editing && !f.photos.length ? "Añade al menos una foto del outfit."
        : f.description.trim().length < 3 ? "Escribe una descripción: es lo que usamos para recomendártelo." : null;
      if (problem) { err.textContent = problem; err.hidden = false; return; }
      const info = { description: f.description.trim(), occasion: f.occasion, seasons: f.seasons, item_ids: f.item_ids };
      submit.disabled = true;
      try {
        if (editing) {
          const updated = await api(`/outfits/${f.id}`, { method: "PUT", body: JSON.stringify(info) });
          this.replace(updated);
          toast("Cambios guardados");
        } else {
          const form = new FormData();
          form.append("info", JSON.stringify(info));
          f.photos.forEach((p, i) => form.append("photos", p.blob, `outfit-${i + 1}.jpg`));
          const created = await api("/outfits", { method: "POST", body: form });
          this.outfits = [created, ...this.outfits];
          toast("Outfit guardado");
        }
        this.closeForm();
      } catch (e) {
        err.textContent = e.message;
        err.hidden = false;
        submit.disabled = false;
      }
    });

    return h("section", { class: "card flow-card" },
      h("button", { type: "button", class: "link-btn back", onclick: () => this.closeForm() }, "← Volver a mis outfits"),
      h("h2", {}, editing ? "Editar outfit" : "Nuevo outfit"),
      photos,
      h("label", { class: "field" }, h("span", {}, "Descripción"), desc,
        h("small", { class: "muted" }, "Cuanto más detalles (ocasión, temporada, colores, prendas), mejor te lo recomendaremos.")),
      h("fieldset", { class: "field" }, h("legend", {}, "Ocasión (opcional)"), single),
      h("fieldset", { class: "field" }, h("legend", {}, "Temporada (opcional)"), seasons),
      h("fieldset", { class: "field" }, h("legend", {}, "Prendas de tu armario que salen (opcional)"), items),
      err,
      h("div", { class: "flow-actions" }, submit, h("button", { type: "button", class: "btn btn-ghost", onclick: () => this.closeForm() }, "Cancelar")));
  },
};
