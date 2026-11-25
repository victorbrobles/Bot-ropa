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
│   └── wardrobe.py    # prendas del usuario y validación de sus datos
├── application/
│   ├── recommend_outfit.py  # caso de uso: ventana horaria, origen + destino
│   └── wardrobe.py          # identificar, guardar, editar y borrar prendas
├── ports/             # interfaces: WeatherProvider, Geocoder, GarmentIdentifier, repositorios
├── adapters/
│   ├── weather/       # open_meteo.py, demo.py (sin red), cache.py
│   ├── identify/      # claude.py (visión + búsqueda web), demo.py
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

## Mi armario: cómo se identifica una prenda

1. El usuario sube hasta 3 fotos: la prenda, la etiqueta de marca y la etiqueta de composición.
   Antes de enviarlas, el navegador las reduce y quita los metadatos EXIF (incluida la ubicación GPS).
2. Claude (`claude-opus-5-5`) analiza las fotos, abre el enlace si lo hay y busca la ficha oficial del
   producto en la web. Devuelve el resultado con un esquema estricto e indica qué ha podido confirmar
   y qué no (marca, modelo, composición...).
3. El usuario confirma ("Sí, es esta"), corrige algún dato o la rechaza y aporta un enlace o una
   descripción para volver a buscar.

Para usarlo hace falta `ANTHROPIC_API_KEY`. Cada usuario tiene un límite diario
(`IDENTIFY_DAILY_LIMIT`) porque cada identificación cuesta dinero. Con `GARMENT_IDENTIFIER=demo`
se puede probar la interfaz sin coste.

De momento cada armario va ligado a una cookie anónima del navegador. Si se borra la cookie, se
pierde el acceso al armario. Cuando haya cuentas de usuario (por ejemplo, con Telegram), se
asociará a la cuenta.

## Tests

```bash
pytest
```

## API

- `GET /api/options`: ánimos, ocasiones, colores y tipos de prenda
- `GET /api/locations?q=Madrid`: buscador de zonas
- `POST /api/outfit`: recomendación (ver `adapters/web/schemas.py`)
- `POST /api/wardrobe/identify`: identificar una prenda (multipart: `photos`, `product_url`, `description`, `rejected`)
- `GET|POST /api/wardrobe/items`, `PUT|DELETE /api/wardrobe/items/{id}`, `GET /api/wardrobe/items/{id}/photos/{n}`

## Aviso de licencias

El plan gratuito de Open-Meteo es **solo para uso no comercial**. Antes de cobrar hay que contratar su plan comercial (`OPEN_METEO_API_KEY`) o usar otro proveedor. Los datos están bajo licencia CC BY 4.0, y la fuente se muestra en el pie de página.
