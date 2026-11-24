"""Opciones de personalización: ánimo, ocasión, colores y tipo de prenda."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mood:
    id: str
    label: str
    icon: str
    tags: frozenset[str]  # estilos de prenda que favorece
    palette: tuple[str, ...]  # colores que encajan con el ánimo
    note: str


MOODS: dict[str, Mood] = {m.id: m for m in [
    Mood("feliz", "Feliz", "😄", frozenset({"alegre", "atrevido"}),
         ("amarillo", "azul", "naranja"), "Colores vivos para acompañar tu buen humor."),
    Mood("energia", "Con energía", "⚡", frozenset({"deportivo", "atrevido"}),
         ("rojo", "azul", "blanco"), "Prendas dinámicas y algún toque de color intenso."),
    Mood("tranquilo", "Tranquilo", "😌", frozenset({"tranquilo", "relajado"}),
         ("beige", "verde", "azul_marino"), "Tonos suaves y prendas sin complicaciones."),
    Mood("cansado", "Cansado", "😴", frozenset({"comodo", "relajado"}),
         ("gris", "azul_marino", "beige"), "Lo más cómodo posible: tejidos suaves y calzado amable."),
    Mood("triste", "Bajo de ánimo", "🌧️", frozenset({"comodo", "alegre"}),
         ("amarillo", "rosa", "naranja"), "Comodidad y un color cálido que te levante el día."),
    Mood("seguro", "Seguro de mí", "😎", frozenset({"seguro", "elegante"}),
         ("negro", "rojo", "blanco"), "Una prenda protagonista para comerte el día."),
    Mood("creativo", "Creativo", "🎨", frozenset({"creativo", "atrevido"}),
         ("morado", "verde", "naranja"), "Combinaciones con personalidad y algo inesperado."),
]}


@dataclass(frozen=True)
class Occasion:
    id: str
    label: str
    icon: str


OCCASIONS: dict[str, Occasion] = {o.id: o for o in [
    Occasion("diario", "Día a día", "🚶"),
    Occasion("trabajo", "Trabajo", "💼"),
    Occasion("deporte", "Deporte", "🏃"),
    Occasion("fiesta", "Fiesta", "🎉"),
    Occasion("etiqueta", "Etiqueta", "🎩"),
]}


@dataclass(frozen=True)
class Color:
    id: str
    label: str
    hex: str
    neutral: bool
    light: bool = False  # útil con calor: refleja el sol


COLORS: dict[str, Color] = {c.id: c for c in [
    Color("negro", "Negro", "#1f1f24", True),
    Color("blanco", "Blanco", "#f7f7f2", True, light=True),
    Color("gris", "Gris", "#8d9099", True),
    Color("beige", "Beige", "#d9c7a7", True, light=True),
    Color("marron", "Marrón", "#7a5134", True),
    Color("azul_marino", "Azul marino", "#1f2f55", True),
    Color("azul", "Azul", "#3f7fd9", False),
    Color("celeste", "Celeste", "#9cc9ef", False, light=True),
    Color("verde", "Verde", "#3f8f5b", False),
    Color("rojo", "Rojo", "#d23b3b", False),
    Color("burdeos", "Burdeos", "#7b1e34", False),
    Color("rosa", "Rosa", "#ec8fb4", False, light=True),
    Color("amarillo", "Amarillo", "#f3c637", False, light=True),
    Color("naranja", "Naranja", "#ee8236", False),
    Color("morado", "Morado", "#7d55c7", False),
]}

# Color fijo de algunas prendas (no se elige: el vaquero es vaquero).
DENIM = Color("vaquero", "Vaquero", "#4a6d9c", True)

# Neutros que combinan con cada color, por orden de preferencia.
NEUTRAL_PAIRINGS: dict[str, tuple[str, ...]] = {
    "negro": ("blanco", "gris", "negro"),
    "blanco": ("azul_marino", "beige", "negro"),
    "gris": ("blanco", "negro", "azul_marino"),
    "beige": ("blanco", "marron", "azul_marino"),
    "marron": ("beige", "blanco", "azul_marino"),
    "azul_marino": ("blanco", "beige", "gris"),
    "azul": ("blanco", "beige", "azul_marino"),
    "celeste": ("blanco", "beige", "azul_marino"),
    "verde": ("beige", "blanco", "marron"),
    "rojo": ("azul_marino", "blanco", "negro"),
    "burdeos": ("gris", "beige", "azul_marino"),
    "rosa": ("blanco", "gris", "azul_marino"),
    "amarillo": ("azul_marino", "blanco", "gris"),
    "naranja": ("azul_marino", "blanco", "beige"),
    "morado": ("gris", "negro", "blanco"),
}

FITS = {
    "cualquiera": "Cualquiera",
    "masculino": "Masculinas",
    "femenino": "Femeninas",
}
