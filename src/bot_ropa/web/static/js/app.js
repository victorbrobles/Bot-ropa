// Vestia · interfaz web
// Sin dependencias ni build: router por hash, menú y secciones en módulos.

import { $ } from "./core.js";
import { outfitView, setOutfitActive } from "./outfit.js";
import { exploreView } from "./explore.js";
import { wardrobeView } from "./wardrobe.js";

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
  if (path === "/armario") wardrobeView.enter();
  if (path === "/explorar") exploreView.enter();
  setOutfitActive(path === "/que-me-pongo");
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

window.addEventListener("hashchange", navigate);
navigate();
