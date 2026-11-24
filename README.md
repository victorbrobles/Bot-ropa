# Vestia (Bot Ropa)

Asistente que mira el tiempo de tu zona y te recomienda qué ponerte.

## Secciones

| Sección | Estado |
|---|---|
| Portada con todas las funciones | ✅ |
| **¿Qué me pongo?**: outfit según el tiempo, el ánimo, las horas fuera, el cambio de zona, el color, la ocasión y el tipo de prenda | ✅ |
| Mi armario | Próximamente |
| Explorar outfits | Próximamente |

## Arquitectura (hexagonal)

```
src/bot_ropa/
├── domain/            # Python puro, sin dependencias externas
│   ├── weather.py     # previsión horaria y resumen del periodo
│   ├── catalog.py     # prendas genéricas (hasta que exista "Mi armario")
│   ├── options.py     # ánimos, ocasiones, colores y combinaciones
│   └── recommender.py # motor de reglas que arma el outfit
├── application/
│   └── recommend_outfit.py  # caso de uso: ventana horaria, origen + destino
├── ports/weather.py   # interfaces WeatherProvider / Geocoder
├── adapters/
│   ├── weather/       # open_meteo.py, demo.py (sin red), cache.py
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

## Tests

```bash
pytest
```

## API

- `GET /api/options`: ánimos, ocasiones, colores y tipos de prenda
- `GET /api/locations?q=Madrid`: buscador de zonas
- `POST /api/outfit`: recomendación (ver `adapters/web/schemas.py`)

## Aviso de licencias

El plan gratuito de Open-Meteo es **solo para uso no comercial**. Antes de cobrar hay que contratar su plan comercial (`OPEN_METEO_API_KEY`) o usar otro proveedor. Los datos están bajo licencia CC BY 4.0, y la fuente se muestra en el pie de página.
