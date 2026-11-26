# Vestia (Bot Ropa)

Asistente que mira el tiempo de tu zona y te recomienda qué ponerte.

## Secciones

| Sección | Estado |
|---|---|
| Portada con todas las funciones | ✅ |
| **¿Qué me pongo?**: outfit según el tiempo, el ánimo, las horas fuera, el cambio de zona, el color, la ocasión y el tipo de prenda | ✅ |
| **Mi armario**: alta por foto, enlace o descripción con identificación automática (marca, modelo, colores y composición), confirmación y edición | ✅ |
| **Mis outfits**: guarda looks con foto y descripción; describe tu plan y te recomienda cuál ponerte (búsqueda con sinónimos) | ✅ |
| **Explorar outfits**: perfil de estilo (estilos, marcas, referentes, presupuesto), looks para ti con tu ropa, completar un look, descubrir marcas, básicos que te faltan y novedades | ✅ |

## Arquitectura (hexagonal)

```
src/bot_ropa/
├── domain/            # Python puro, sin dependencias externas
│   ├── weather.py     # previsión horaria y resumen del periodo
│   ├── catalog.py     # prendas genéricas (hasta que exista "Mi armario")
│   ├── options.py     # ánimos, ocasiones, colores y combinaciones
│   ├── recommender.py # motor de reglas que arma el outfit
│   ├── wardrobe.py    # prendas del usuario y validación de sus datos
│   ├── garment_analysis.py  # composición, marca, tipo y colores a partir de texto
│   ├── identification.py    # une todas las pistas en un borrador de prenda
│   ├── style_catalog.py     # estilos, marcas y referentes (datos curados)
│   ├── explore.py           # recomendaciones: looks, completar, marcas y básicos
│   ├── outfits.py           # outfits guardados y su recomendación
│   └── text_search.py       # buscador en español (BM25 + sinónimos)
├── application/
│   ├── recommend_outfit.py  # caso de uso: ventana horaria, origen + destino
│   └── wardrobe.py          # identificar, guardar, editar y borrar prendas
├── ports/             # interfaces: WeatherProvider, Geocoder, ProductPageReader, repositorios
├── adapters/
│   ├── weather/       # open_meteo.py, demo.py (sin red), cache.py
│   ├── product_page/  # lectura de fichas de producto (JSON-LD / Open Graph)
│   ├── persistence/   # SQLite y fotos en disco
│   └── web/           # API HTTP (FastAPI)
├── web/static/        # interfaz web (HTML/CSS/JS sin build)
└── main.py            # conecta todo
```

Para cambiar de proveedor del tiempo (por ejemplo, AEMET o el plan comercial de Open-Meteo) basta con añadir un adaptador nuevo.

## Arrancar en local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env              # WEATHER_PROVIDER=demo para trabajar sin red
uvicorn bot_ropa.main:app --reload --app-dir src
# abre http://localhost:8000
```

La geolocalización del navegador solo funciona en `localhost` o con HTTPS.

## Mi armario: cómo se identifica una prenda (sin coste)

Todo el proceso es gratuito: no se usa ninguna API de pago.

1. El usuario sube hasta 3 fotos: la prenda, la etiqueta de marca y la etiqueta de composición.
   El navegador las reduce y quita los metadatos EXIF (incluida la ubicación GPS).
2. **En el navegador** (en el dispositivo del usuario):
   - los **colores** se calculan a partir de los píxeles de la foto de la prenda, ignorando el fondo;
   - las **etiquetas** se leen con OCR ([Tesseract.js](https://github.com/naptha/tesseract.js), Apache 2.0).
     La primera vez se descargan unos 8 MB del CDN jsdelivr; después quedan en caché.
3. **En el servidor**, con reglas (`domain/garment_analysis.py`):
   - la composición se extrae del texto de la etiqueta: entiende varios idiomas, códigos como "CO/PES"
     y secciones como forro o relleno;
   - el tipo de prenda se deduce del nombre o la descripción;
   - si hay **enlace del producto**, se lee la ficha de la tienda (datos estructurados JSON-LD / Open
     Graph) para sacar el nombre, la marca, la referencia, el color y el material. Algunas tiendas bloquean
     las lecturas automáticas; entonces se pide completar los datos a mano.
4. Cada dato indica de dónde sale (etiqueta, foto, ficha web o descripción) y el usuario confirma o
   corrige antes de guardar.

Lo que **no** hace: reconocer el modelo exacto solo mirando la foto de la prenda. Para eso haría falta IA
de pago. El modelo exacto viene del enlace del producto.

De momento cada armario va ligado a una cookie anónima del navegador. Si se borra la cookie, se pierde
el acceso al armario. Cuando haya cuentas de usuario se asociará a la cuenta.

## Explorar outfits: cómo recomienda (sin coste)

- **Perfil de estilo:** estilos favoritos, marcas (del catálogo o escritas a mano), referentes de estilo,
  presupuesto, preferencia por marcas sostenibles o por la segunda mano, y tipo de prenda.
- **Afinidad:** cada estilo suma puntos según lo que eliges (lo que más pesa), tus referentes, tus marcas
  y la ropa que ya tienes en el armario.
- **Looks para ti:** looks de temporada para tus estilos principales, construidos alrededor de tus
  propias prendas.
- **Completar un look:** eliges prendas (tuyas o genéricas) y te propone el resto con colores que
  combinan. Si ya tienes algo que sirve, te lo propone antes que comprar.
- **Marcas y básicos:** marcas nuevas que encajan contigo (con el motivo) y los básicos de tu estilo que
  aún no tienes.
- **Dónde comprar:** son enlaces de búsqueda en la web de cada marca (vía Google), en Google Shopping y,
  si te interesa, en Vinted. No se extraen datos de las tiendas. En el futuro estos enlaces podrían ser
  de afiliado.

Los datos de estilos, marcas y referentes están en `domain/style_catalog.py` y son orientativos.

## Mis outfits: cómo elige qué ponerte (sin coste)

Guardas outfits con fotos y una descripción (más ocasión, temporada y prendas del armario, si quieres).
Cuando describes tu plan, `domain/text_search.py` lo compara con tus outfits:

- normaliza el texto (minúsculas, sin acentos, sin plurales, sin palabras vacías);
- agrupa sinónimos en conceptos: «boda», «ceremonia» y «gala» cuentan como `#etiqueta`; «julio» y
  «playa» como `#verano`; «gym» y «correr» como `#deporte`…;
- puntúa con BM25, el algoritmo clásico de los buscadores;
- ajusta el resultado: favorece los outfits de la temporada actual y penaliza los que te pusiste hace
  menos de una semana, para variar.

Para añadir sinónimos, amplía `CONCEPTS` en `text_search.py`.

## Tests

```bash
pytest
```

## API

- `GET /api/options`: ánimos, ocasiones, colores y tipos de prenda
- `GET /api/locations?q=Madrid`: buscador de zonas
- `POST /api/outfit`: recomendación (ver `adapters/web/schemas.py`)
- `POST /api/wardrobe/analyze`: analizar una prenda (JSON: `label_text`, `brand_lines`, `photo_colors`, `product_url`, `description`)
- `GET /api/explore/catalog`, `GET|PUT /api/explore/profile`, `GET /api/explore/feed`, `GET /api/explore/brands`, `POST /api/explore/complete`
- `GET|POST /api/outfits`, `PUT|DELETE /api/outfits/{id}`, `POST /api/outfits/{id}/worn`, `POST /api/outfits/search`
- `GET|POST /api/wardrobe/items`, `PUT|DELETE /api/wardrobe/items/{id}`, `GET /api/wardrobe/items/{id}/photos/{n}`

## Aviso de licencias

El plan gratuito de Open-Meteo es **solo para uso no comercial**. Antes de cobrar hay que contratar su plan comercial (`OPEN_METEO_API_KEY`) o usar otro proveedor. Los datos están bajo licencia CC BY 4.0, y la fuente se muestra en el pie de página.
