# Vestia (Bot Ropa)

Asistente que mira el tiempo de tu zona y te recomienda qué ponerte.

## Secciones

| Sección | Estado |
|---|---|
| Portada con todas las funciones | ✅ |
| **¿Qué me pongo?**: outfit según el tiempo, el ánimo, las horas fuera, el cambio de zona, el color, la ocasión y el tipo de prenda | ✅ |
| **Mi armario**: alta por foto, enlace o descripción con identificación automática (marca, modelo, colores y composición), confirmación y edición | ✅ |
| Explorar outfits | Próximamente |

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
│   └── identification.py    # une todas las pistas en un borrador de prenda
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

## Tests

```bash
pytest
```

## API

- `GET /api/options`: ánimos, ocasiones, colores y tipos de prenda
- `GET /api/locations?q=Madrid`: buscador de zonas
- `POST /api/outfit`: recomendación (ver `adapters/web/schemas.py`)
- `POST /api/wardrobe/analyze`: analizar una prenda (JSON: `label_text`, `brand_lines`, `photo_colors`, `product_url`, `description`)
- `GET|POST /api/wardrobe/items`, `PUT|DELETE /api/wardrobe/items/{id}`, `GET /api/wardrobe/items/{id}/photos/{n}`

## Aviso de licencias

El plan gratuito de Open-Meteo es **solo para uso no comercial**. Antes de cobrar hay que contratar su plan comercial (`OPEN_METEO_API_KEY`) o usar otro proveedor. Los datos están bajo licencia CC BY 4.0, y la fuente se muestra en el pie de página.
