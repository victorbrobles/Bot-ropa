// Sección "Explorar outfits": ideas, completar un look, marcas, básicos y perfil de estilo.

import { $, api, getOptions, h, storage, toast } from "./core.js";

const TABS = [
  { id: "para_ti", label: "Para ti", icon: "✨" },
  { id: "completar", label: "Completar un look", icon: "🧩" },
  { id: "marcas", label: "Marcas", icon: "🏷️" },
  { id: "faltan", label: "Lo que te falta", icon: "📋" },
  { id: "estilo", label: "Mi estilo", icon: "🎨" },
];

// ------------------------------------------------------------ piezas comunes
function linksRow(links) {
  if (!links?.length) return null;
  const pill = (l) => h("a", { class: "shop-link", href: l.url, target: "_blank", rel: "noopener noreferrer" }, l.label, " ↗");
  const first = links.slice(0, 3);
  const rest = links.slice(3);
  return h("div", { class: "shop-links" }, h("span", { class: "muted small" }, "Buscar en:"), first.map(pill),
    rest.length ? h("details", { class: "more-links" }, h("summary", {}, `+${rest.length}`), h("div", {}, rest.map(pill))) : null);
}

function swatch(color, icon) {
  return h("span", { class: "item-swatch small", vars: { "--c": color?.hex || "#ddd" }, "aria-hidden": "true" }, icon);
}

function ownedThumb(item) {
  const d = item.details;
  return h("span", { class: "owned-thumb", vars: { "--c": d.colors[0]?.hex || "#ddd" } },
    item.photos?.length ? h("img", { src: item.photos[0], alt: "" }) : d.icon);
}

/** Tarjeta de un look: lo que ya llevas + lo que te proponemos. */
function lookCard(plan, { title, reason } = {}) {
  const pieces = [
    ...plan.base.map((b) => h("li", { class: "look-piece mine" },
      b.photo ? h("span", { class: "owned-thumb", vars: { "--c": b.color?.hex || "#ddd" } }, h("img", { src: b.photo, alt: "" })) : swatch(b.color, b.icon),
      h("div", {},
        h("span", { class: "item-slot" }, b.slot_label),
        h("strong", {}, b.name),
        h("span", { class: "badge badge-live" }, b.item_id ? "Tu prenda" : "Tu elección")))),
    ...plan.suggestions.map((s) => h("li", { class: `look-piece ${s.use_owned ? "mine" : ""}` },
      s.use_owned && s.owned[0] ? ownedThumb(s.owned[0]) : swatch(s.color, s.icon),
      h("div", {},
        h("span", { class: "item-slot" }, s.slot_label),
        h("strong", {}, s.use_owned ? s.owned[0].details.name : s.article),
        s.use_owned
          ? h("span", { class: "badge badge-live" }, "Ya la tienes")
          : s.owned.length
            ? h("span", { class: "owned-hint" }, "O usa tu ", h("strong", {}, s.owned[0].details.name.toLowerCase()))
            : null,
        h("p", { class: "muted small" }, s.reason),
        s.use_owned ? null : linksRow(s.links)))),
  ];
  return h("article", { class: "card look-card" },
    h("div", { class: "look-head" },
      h("span", { class: "look-emoji", "aria-hidden": "true" }, plan.style.emoji),
      h("div", {},
        h("h3", {}, title || `Look ${plan.style.label.toLowerCase()}`),
        reason ? h("p", { class: "muted small" }, reason) : null)),
    h("ul", { class: "look-pieces" }, pieces),
    plan.accessories.length ? h("p", { class: "look-acc" }, "👜 Complementos: ", plan.accessories.join(" · ")) : null,
    plan.palette.length ? h("div", { class: "palette mini", role: "img", "aria-label": `Colores: ${plan.palette.map((c) => c.label).join(", ")}` },
      plan.palette.map((c) => h("i", { vars: { "--c": c.hex }, title: c.label }))) : null,
    plan.tips.length ? h("p", { class: "muted small" }, "💡 ", plan.tips.join(" ")) : null);
}

// ================================================================== vista
export const exploreView = {
  started: false,
  catalog: null,
  options: null,
  profile: null,
  feed: null,
  wardrobe: [],
  brands: null,
  tab: storage.get("exploreTab", "para_ti"),
  error: null,
  loading: true,
  builder: { pieces: [], style: "", occasion: null, result: null, busy: false },
  brandFilter: { price: null, sustainable: false },

  async enter() {
    if (!this.started) {
      this.started = true;
      this.renderTabs();
    }
    this.loading = true;
    this.render();
    try {
      const [catalog, options, profile, feed, wardrobe] = await Promise.all([
        this.catalog || api("/explore/catalog"), getOptions(), api("/explore/profile"),
        api("/explore/feed"), api("/wardrobe/items").then((d) => d.items),
      ]);
      Object.assign(this, { catalog, options, profile, feed, wardrobe, error: null, brands: null });
      if (feed.profile_empty && !storage.get("exploreSeen", false)) {
        storage.set("exploreSeen", true);
        this.tab = "estilo";
      }
    } catch (err) {
      this.error = err.message;
    }
    this.loading = false;
    this.renderTabs();
    this.render();
  },

  setTab(id) {
    this.tab = id;
    storage.set("exploreTab", id);
    this.renderTabs();
    this.render();
  },

  renderTabs() {
    $("#ex-tabs").replaceChildren(...TABS.map((t) => h("button", {
      type: "button", role: "tab", class: "tab", "aria-selected": String(this.tab === t.id),
      onclick: () => this.setTab(t.id),
    }, h("span", { "aria-hidden": "true" }, t.icon), t.label)));
  },

  render() {
    const main = $("#ex-main");
    if (this.error) {
      return main.replaceChildren(h("div", { class: "card error-card", role: "alert" }, h("span", {}, "⚠️"), h("p", {}, this.error)));
    }
    if (this.loading && !this.feed) {
      return main.replaceChildren(h("div", { class: "skeleton", style: { height: "320px" } }));
    }
    const views = { para_ti: () => this.paraTi(), completar: () => this.completar(), marcas: () => this.marcas(),
      faltan: () => this.faltan(), estilo: () => this.estilo() };
    main.replaceChildren(views[this.tab]());
  },

  // ---------------------------------------------------------- Para ti
  paraTi() {
    const f = this.feed;
    return h("div", { class: "ex-stack" },
      f.profile_empty ? h("div", { class: "card onboard" },
        h("span", { class: "big", "aria-hidden": "true" }, "🎨"),
        h("div", {}, h("h2", {}, "Cuéntanos tu estilo"),
          h("p", { class: "muted" }, "Elige tus estilos, marcas y referentes favoritos para afinar las recomendaciones. Mientras tanto, te enseñamos ideas generales.")),
        h("button", { type: "button", class: "btn btn-primary", onclick: () => this.setTab("estilo") }, "Configurar mi estilo")) : null,
      h("div", { class: "affinity" }, h("span", { class: "muted small" }, "Tu estilo:"),
        f.affinity.slice(0, 4).map((a) => h("span", { class: "chip static" }, a.emoji, " ", a.label))),
      f.wardrobe_count === 0 ? h("p", { class: "warn-line" }, "💡 Añade prendas a ",
        h("a", { href: "#/armario" }, "Mi armario"), " y construiremos los looks alrededor de tu propia ropa.") : null,
      h("h2", { class: "ex-title" }, "Looks para ti"),
      h("div", { class: "look-grid" }, f.ideas.map((i) => lookCard(i, i))),
      f.news.length ? h("section", {},
        h("h2", { class: "ex-title" }, "Novedades de tus marcas"),
        h("div", { class: "news-row" }, f.news.map((n) => h("div", { class: "news-card" },
          h("strong", {}, n.name), n.favorite ? h("span", { class: "badge" }, "Favorita") : h("span", { class: "badge badge-live" }, "Para ti"),
          h("div", { class: "news-links" },
            h("a", { href: n.url, target: "_blank", rel: "noopener noreferrer" }, "Web ↗"),
            h("a", { href: n.search, target: "_blank", rel: "noopener noreferrer" }, "Nueva colección ↗")))))) : null,
      f.brands.length ? h("section", {},
        h("div", { class: "row-between" }, h("h2", { class: "ex-title" }, "Marcas que podrían gustarte"),
          h("button", { type: "button", class: "link-btn", onclick: () => this.setTab("marcas") }, "Ver todas")),
        h("div", { class: "brand-grid" }, f.brands.slice(0, 4).map((b) => this.brandCard(b)))) : null);
  },

  // ---------------------------------------------------- Completar un look
  completar() {
    const b = this.builder;
    const o = this.options;
    const selectedIds = new Set(b.pieces.filter((p) => p.item_id).map((p) => p.item_id));
    const slotOf = (baseType) => o.garment_types.find((g) => g.id === baseType)?.slot;
    const add = (piece) => {
      const slot = slotOf(piece.base_type);
      b.pieces = b.pieces.filter((p) => slotOf(p.base_type) !== slot); // una prenda por parte del cuerpo
      b.pieces.push(piece);
      b.result = null;
      this.render();
    };
    const typeSel = h("select", { "aria-label": "Tipo de prenda" }, h("option", { value: "" }, "Tipo de prenda…"),
      o.slots.map((s) => h("optgroup", { label: s.label },
        o.garment_types.filter((g) => g.slot === s.id).map((g) => h("option", { value: g.id }, `${g.icon} ${g.name}`)))));
    const colorSel = h("select", { "aria-label": "Color" }, h("option", { value: "" }, "Color…"),
      o.colors.map((c) => h("option", { value: c.id }, c.label)));
    const styleSel = h("select", { "aria-label": "Estilo" },
      h("option", { value: "" }, "El que más encaja contigo"),
      this.catalog.styles.map((s) => h("option", { value: s.id, selected: s.id === b.style }, `${s.emoji} ${s.label}`)));
    styleSel.addEventListener("change", () => { b.style = styleSel.value; b.result = null; });

    return h("div", { class: "ex-stack" },
      h("section", { class: "card ex-card" },
        h("h2", {}, "¿Qué tienes pensado ponerte?"),
        h("p", { class: "muted" }, "Elige una o varias prendas y te decimos qué combina con ellas: de tu armario o para comprar."),
        this.wardrobe.length
          ? h("ul", { class: "pick-grid" }, this.wardrobe.map((item) => h("li", {},
            h("button", { type: "button", class: "pick", "aria-pressed": String(selectedIds.has(item.id)),
              onclick: () => {
                if (selectedIds.has(item.id)) { b.pieces = b.pieces.filter((p) => p.item_id !== item.id); b.result = null; this.render(); }
                else add({ item_id: item.id, base_type: item.details.base_type, label: item.details.name });
              } },
            ownedThumb(item), h("span", {}, item.details.name)))))
          : h("p", { class: "muted small" }, "Tu armario está vacío: usa una prenda genérica."),
        h("div", { class: "generic-add" },
          h("span", { class: "small" }, "O una prenda genérica:"), typeSel, colorSel,
          h("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => {
            if (!typeSel.value) return toast("Elige el tipo de prenda");
            const type = o.garment_types.find((g) => g.id === typeSel.value);
            const color = o.colors.find((c) => c.id === colorSel.value);
            add({ base_type: type.id, color: color?.id || null, label: [type.name, color?.label.toLowerCase()].filter(Boolean).join(" ") });
          } }, "Añadir")),
        b.pieces.length ? h("div", { class: "chips selected" }, b.pieces.map((p) =>
          h("span", { class: "chip static" }, p.label, h("button", { type: "button", class: "chip-x", "aria-label": `Quitar ${p.label}`,
            onclick: () => { b.pieces = b.pieces.filter((x) => x !== p); b.result = null; this.render(); } }, "✕")))) : null,
        h("div", { class: "form-grid two" },
          h("label", { class: "field" }, h("span", {}, "Estilo"), styleSel),
          h("fieldset", { class: "field" }, h("legend", {}, "Ocasión (opcional)"),
            h("div", { class: "chips" }, o.occasions.map((oc) => h("button", { type: "button", class: "chip",
              "aria-pressed": String(b.occasion === oc.id),
              onclick: () => { b.occasion = b.occasion === oc.id ? null : oc.id; b.result = null; this.render(); } }, oc.icon, " ", oc.label))))),
        h("button", { type: "button", class: "btn btn-primary", disabled: !b.pieces.length || b.busy, onclick: () => this.runComplete() },
          b.busy ? "Pensando…" : "¿Qué me pongo con esto?")),
      b.result ? h("div", { id: "ex-result" }, lookCard(b.result, { title: "Tu look completo", reason: `Estilo ${b.result.style.label.toLowerCase()} · ${b.result.season}` })) : null);
  },

  async runComplete() {
    const b = this.builder;
    b.busy = true;
    this.render();
    try {
      b.result = await api("/explore/complete", { method: "POST", body: JSON.stringify({
        pieces: b.pieces.map((p) => (p.item_id ? { item_id: p.item_id } : { base_type: p.base_type, color: p.color })),
        style: b.style || null, occasion: b.occasion,
      }) });
    } catch (err) {
      toast(err.message);
    }
    b.busy = false;
    this.render();
    $("#ex-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
  },

  // ---------------------------------------------------------------- Marcas
  brandCard(b) {
    const fav = this.profile.brands.includes(b.id);
    return h("article", { class: "card brand-card" },
      h("div", { class: "brand-head" },
        h("span", { class: "brand-logo", "aria-hidden": "true" }, b.name.replace(/[^A-Za-z0-9&]/g, "").slice(0, 2).toUpperCase()),
        h("div", {}, h("strong", {}, b.name), h("span", { class: "muted small" }, ` ${b.price_label}`, b.sustainable ? " · 🌱 Sostenible" : ""))),
      h("div", { class: "chips" }, b.styles.map((s) => h("span", { class: "chip static small-chip" }, s.label))),
      b.reasons ? h("ul", { class: "reasons" }, b.reasons.map((r) => h("li", {}, r))) : null,
      h("div", { class: "brand-actions" },
        h("a", { class: "btn btn-ghost btn-small", href: b.url, target: "_blank", rel: "noopener noreferrer" }, "Visitar web ↗"),
        h("button", { type: "button", class: "btn btn-small " + (fav ? "btn-ghost" : "btn-primary"),
          onclick: () => this.toggleBrand(b.id) }, fav ? "♥ En tus marcas" : "♡ Me gusta")));
  },

  async toggleBrand(id) {
    const brands = this.profile.brands.includes(id) ? this.profile.brands.filter((b) => b !== id) : [...this.profile.brands, id];
    await this.saveProfile({ ...this.profile, brands }, { quiet: true });
    toast(brands.includes(id) ? "Añadida a tus marcas" : "Quitada de tus marcas");
  },

  marcas() {
    if (!this.brands) {
      api("/explore/brands").then((d) => { this.brands = d.brands; this.render(); }).catch((e) => toast(e.message));
      return h("div", { class: "skeleton", style: { height: "240px" } });
    }
    const f = this.brandFilter;
    const list = this.brands.filter((b) => (!f.price || b.price === f.price) && (!f.sustainable || b.sustainable));
    const shops = this.catalog.brands.filter((b) => b.kind !== "marca");
    const favs = this.catalog.brands.filter((b) => this.profile.brands.includes(b.id));
    return h("div", { class: "ex-stack" },
      h("div", { class: "filters-row" },
        h("div", { class: "chips" }, [null, 1, 2, 3].map((p) => h("button", { type: "button", class: "chip", "aria-pressed": String(f.price === p),
          onclick: () => { f.price = p; this.render(); } }, p ? "€".repeat(p) : "Cualquier precio"))),
        h("label", { class: "check" }, h("input", { type: "checkbox", checked: f.sustainable,
          onchange: (e) => { f.sustainable = e.target.checked; this.render(); } }), h("span", {}, "Solo sostenibles"))),
      h("h2", { class: "ex-title" }, "Descubre marcas nuevas"),
      h("p", { class: "muted small" }, "Marcas que no tienes en tu armario ni en tus favoritas y que encajan con tu estilo. Precios orientativos."),
      list.length ? h("div", { class: "brand-grid" }, list.map((b) => this.brandCard(b)))
        : h("p", { class: "muted" }, "No hay marcas con esos filtros. Prueba a cambiarlos o a elegir más estilos en «Mi estilo»."),
      favs.length ? h("section", {}, h("h2", { class: "ex-title" }, "Tus marcas"),
        h("div", { class: "brand-grid" }, favs.map((b) => this.brandCard(b)))) : null,
      h("section", {}, h("h2", { class: "ex-title" }, "Tiendas con de todo"),
        h("div", { class: "news-row" }, shops.map((s) => h("a", { class: "news-card", href: s.url, target: "_blank", rel: "noopener noreferrer" },
          h("strong", {}, s.name), h("span", { class: "muted small" }, s.kind === "segunda_mano" ? "♻️ Segunda mano" : "Multimarca"))))));
  },

  // ------------------------------------------------------- Lo que te falta
  faltan() {
    const gaps = this.feed.gaps;
    const byStyle = {};
    gaps.forEach((g) => { (byStyle[g.style] ||= []).push(g); });
    const owned = gaps.filter((g) => g.owned).length;
    return h("div", { class: "ex-stack" },
      h("div", { class: "card ex-card" },
        h("h2", {}, "Los básicos de tu estilo"),
        h("p", { class: "muted" }, `Tienes ${owned} de ${gaps.length} prendas clave. Con ellas podrás montar muchos looks combinándolas entre sí.`),
        h("span", { class: "meter wide" }, h("i", { style: { width: `${gaps.length ? Math.round((owned / gaps.length) * 100) : 0}%` } }))),
      Object.entries(byStyle).map(([style, items]) => h("section", { class: "card ex-card" },
        h("h3", {}, style),
        h("ul", { class: "gap-list" }, items.map((g) => h("li", { class: g.owned ? "have" : "" },
          h("span", { class: "gap-status", "aria-label": g.owned ? "La tienes" : "Te falta" }, g.owned ? "✓" : "＋"),
          h("div", {},
            h("strong", {}, g.article), " ", h("span", { class: "muted small" }, g.slot_label),
            g.owned ? h("p", { class: "small" }, "Tienes: ", g.owned.details.name) : linksRow(g.links))))))));
  },

  // ------------------------------------------------------------ Mi estilo
  estilo() {
    const draft = structuredClone(this.profile);
    const c = this.catalog;
    const toggle = (list, value, btn) => {
      const i = list.indexOf(value);
      i >= 0 ? list.splice(i, 1) : list.push(value);
      btn.setAttribute("aria-pressed", String(i < 0));
    };

    const styleCards = h("div", { class: "style-grid" }, c.styles.map((s) => {
      const btn = h("button", { type: "button", class: "style-card", "aria-pressed": String(draft.styles.includes(s.id)) },
        h("span", { class: "style-emoji", "aria-hidden": "true" }, s.emoji),
        h("strong", {}, s.label),
        h("span", { class: "small muted" }, s.description),
        h("span", { class: "dots" }, s.palette.slice(0, 5).map((hex) => h("i", { vars: { "--c": hex } }))));
      btn.addEventListener("click", () => toggle(draft.styles, s.id, btn));
      return btn;
    }));

    // Marcas: buscador + chips
    const brandList = c.brands.filter((b) => b.kind === "marca");
    const brandChips = h("div", { class: "chips" });
    const search = h("input", { type: "search", placeholder: "Buscar marca…", "aria-label": "Buscar marca" });
    const renderBrands = () => {
      const q = search.value.trim().toLowerCase();
      brandChips.replaceChildren(...brandList
        .filter((b) => !q || b.name.toLowerCase().includes(q))
        .sort((a, b) => draft.brands.includes(b.id) - draft.brands.includes(a.id))
        .map((b) => {
          const btn = h("button", { type: "button", class: "chip", "aria-pressed": String(draft.brands.includes(b.id)) }, b.name);
          btn.addEventListener("click", () => toggle(draft.brands, b.id, btn));
          return btn;
        }),
        ...draft.custom_brands.map((name) => h("span", { class: "chip static", "aria-pressed": "true" }, name,
          h("button", { type: "button", class: "chip-x", "aria-label": `Quitar ${name}`,
            onclick: () => { draft.custom_brands = draft.custom_brands.filter((n) => n !== name); renderBrands(); } }, "✕"))));
    };
    search.addEventListener("input", renderBrands);
    const customBrand = h("input", { type: "text", placeholder: "¿No está? Escríbela", "aria-label": "Otra marca" });
    renderBrands();

    // Referentes
    const iconChips = h("div", { class: "chips" });
    const renderIcons = () => iconChips.replaceChildren(
      ...c.icons.map((i) => {
        const btn = h("button", { type: "button", class: "chip", "aria-pressed": String(draft.icons.includes(i.id)),
          title: i.styles.map((s) => c.styles.find((x) => x.id === s).label).join(" · ") }, i.name);
        btn.addEventListener("click", () => toggle(draft.icons, i.id, btn));
        return btn;
      }),
      ...draft.custom_icons.map((ci) => h("span", { class: "chip static", "aria-pressed": "true" }, ci.name,
        h("span", { class: "muted small" }, ci.styles.length ? ` · ${ci.styles.map((s) => c.styles.find((x) => x.id === s).label).join(", ")}` : ""),
        h("button", { type: "button", class: "chip-x", "aria-label": `Quitar ${ci.name}`,
          onclick: () => { draft.custom_icons = draft.custom_icons.filter((x) => x !== ci); renderIcons(); } }, "✕"))));
    renderIcons();
    const iconName = h("input", { type: "text", placeholder: "Otra persona (nombre)", "aria-label": "Nombre del referente" });
    const iconStyle = h("select", { "aria-label": "Su estilo" }, h("option", { value: "" }, "Su estilo…"),
      c.styles.map((s) => h("option", { value: s.id }, s.label)));

    const multi = (values, items) => h("div", { class: "chips" }, items.map((it) => {
      const btn = h("button", { type: "button", class: "chip", "aria-pressed": String(values.includes(it.id)) }, it.label);
      btn.addEventListener("click", () => toggle(values, it.id, btn));
      return btn;
    }));
    const fitSeg = h("div", { class: "segmented", role: "radiogroup", "aria-label": "Tipo de prendas" },
      this.options.fits.map((f) => {
        const btn = h("button", { type: "button", role: "radio", "aria-checked": String(draft.fit === f.id) }, f.label);
        btn.addEventListener("click", () => {
          draft.fit = f.id;
          fitSeg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-checked", String(x === btn)));
        });
        return btn;
      }));
    const check = (key, label) => h("label", { class: "check" },
      h("input", { type: "checkbox", checked: draft[key], onchange: (e) => { draft[key] = e.target.checked; } }), h("span", {}, label));

    return h("div", { class: "ex-stack" },
      h("section", { class: "card ex-card" },
        h("h2", {}, "¿Qué estilos te gustan?"), h("p", { class: "muted small" }, "Elige todos los que quieras."), styleCards),
      h("section", { class: "card ex-card" },
        h("h2", {}, "Tus marcas favoritas"), search, brandChips,
        h("div", { class: "inline-add" }, customBrand, h("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => {
          const name = customBrand.value.trim();
          if (name && !draft.custom_brands.includes(name)) draft.custom_brands.push(name);
          customBrand.value = "";
          renderBrands();
        } }, "Añadir"))),
      h("section", { class: "card ex-card" },
        h("h2", {}, "Referentes de estilo"),
        h("p", { class: "muted small" }, "Personas cuyo estilo te inspira. Si no está quien buscas, añádelo y dinos su estilo."),
        iconChips,
        h("div", { class: "inline-add" }, iconName, iconStyle, h("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => {
          const name = iconName.value.trim();
          if (!name) return;
          draft.custom_icons.push({ name, styles: iconStyle.value ? [iconStyle.value] : [] });
          iconName.value = "";
          renderIcons();
        } }, "Añadir"))),
      h("section", { class: "card ex-card" },
        h("h2", {}, "Preferencias"),
        h("fieldset", { class: "field" }, h("legend", {}, "Presupuesto"), multi(draft.budget, c.prices)),
        h("fieldset", { class: "field" }, h("legend", {}, "Tipo de prendas"), fitSeg),
        h("div", { class: "checks-row" }, check("sustainable", "🌱 Prefiero marcas sostenibles"), check("secondhand", "♻️ Me interesa la segunda mano"))),
      h("div", { class: "sticky-save" },
        h("button", { type: "button", class: "btn btn-primary btn-block", onclick: () => this.saveProfile(draft) }, "Guardar mi estilo")));
  },

  async saveProfile(profile, { quiet = false } = {}) {
    try {
      this.profile = await api("/explore/profile", { method: "PUT", body: JSON.stringify(profile) });
      this.feed = await api("/explore/feed");
      this.brands = null;
      if (!quiet) {
        toast("Estilo guardado");
        this.setTab("para_ti");
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else {
        this.render();
      }
    } catch (err) {
      toast(err.message);
    }
  },
};
