# Asistente RAG sobre sitio web bancario (BBVA)

Sistema de Retrieval-Augmented Generation que permite consultar, mediante una interfaz
conversacional, el contenido publicado en el sitio web institucional de un banco.

> Este README se irá completando a medida que avanzan las fases del proyecto. Al cierre
> incluirá: requisitos previos, instrucciones de arranque con Docker, uso de la interfaz,
> patrones de diseño aplicados, stack tecnológico y justificación, limitaciones y mejoras futuras.

## Estado actual

- [x] Fase 1 — Estructura base del repositorio
- [x] Fase 2 — Web scraping (149/150 páginas reales descargadas de bbva.mx, ver decisión abajo)
- [x] Fase 3 — Limpieza y normalización de datos (146 páginas limpias en `data/processed/`)
- [ ] Fase 4 — Chunking, embeddings e indexación vectorial
- [ ] Fase 5 — Pipeline RAG base
- [ ] Fase 6 — API de chat (FastAPI)
- [ ] Fase 7 — Historial de conversación persistente
- [ ] Fase 8 — Interfaz web mínima
- [ ] Fase 9 — Retrieval híbrido (dense + BM25) y MMR
- [ ] Fase 10 — Reranker
- [ ] Fase 11 — Observabilidad con Langfuse
- [ ] Fase 12 — Dockerización completa
- [ ] Fase 13 — Evaluación con RAGAS
- [ ] Fase 14 — Analítica del histórico de conversaciones
- [ ] Fase 15 — Manejo de errores y endurecimiento
- [ ] Fase 16 — README final

## Decisión sobre el sitio objetivo

El enunciado pide `https://www.bbva.com.co/`, permitiendo explícitamente usar otro banco si
es necesario ("Puede ser de otro banco"). Se intentó primero con BBVA Colombia; el resultado
final fue usar **BBVA México (`https://www.bbva.mx`)**. Documento el proceso completo porque
fue una decisión forzada por un obstáculo técnico real, no una elección arbitraria:

1. **Primer bloqueo (headers):** requests simples (solo `User-Agent`) recibían `HTTP 403`
   de un WAF (Akamai) tanto en la home de bbva.com.co como en `/robots.txt`. Se confirmó que
   no era un bloqueo geográfico ni permanente: agregando las cabeceras propias de un
   navegador real (`Accept`, `Accept-Language`, `Accept-Encoding`, `Sec-Fetch-*`,
   `Upgrade-Insecure-Requests`) el sitio respondía `HTTP 200` con normalidad, y su
   `robots.txt` resultó ser permisivo (`Allow: /`).
2. **Segundo bloqueo (velocidad/volumen):** el mismo WAF penaliza además la *frecuencia* de
   requests desde una misma IP. Iterar y probar el punto anterior (múltiples corridas de
   diagnóstico en poco tiempo) escaló el bloqueo de "puntual en `/sitemap.xml`" a un `403`
   sostenido en **todo el dominio para esa IP**, incluso tras esperar varias horas sin hacer
   ninguna otra request. El usuario confirmó el bloqueo probando desde la misma máquina de
   desarrollo (misma IP pública), descartando que fuera un problema del código.
3. **Decisión final:** en vista de que el bloqueo persistía y el enunciado permite
   explícitamente otro banco, se optó por **BBVA México**, mismo grupo corporativo y
   contenido institucional equivalente (productos para personas/empresas en español), sin el
   bloqueo de bbva.com.co. El scraper se ejecutó sin problemas: **149/150 páginas descargadas
   correctamente** (el único error es un `404` real del sitio, una landing dada de baja, no un
   bloqueo).

El código sigue siendo agnóstico al sitio (todo vía `.env`): si en el futuro el bloqueo de
bbva.com.co se disipa, basta con cambiar `SCRAPER_BASE_URL`/`SCRAPER_SITEMAP_URL` de vuelta.
El módulo conserva además las mitigaciones desarrolladas durante el diagnóstico (útiles para
cualquier sitio con WAF similar):

1. **Cabeceras de navegador completas** en cada request (`scraper/http_headers.py`).
2. **Caché local de `sitemap.xml` y `robots.txt`** (`scraper/sitemap_crawler.py`,
   `scraper/robots.py`) para no golpear repetidamente paths poco visitados por usuarios reales.
3. **Reintentos con backoff** (`scraper/http_client.py`) para absorber bloqueos puntuales.
4. **Ritmo configurable entre páginas** (`SCRAPER_DELAY_SECONDS`, 1s por defecto).

El sitemap de bbva.mx contiene ~3750 URLs. Para acotar el alcance a un tiempo de entrega
razonable, el scraper prioriza por secciones (configurable vía `.env`):

1. `/personas/` (~936 páginas) — productos y servicios para personas físicas.
2. `/empresas/` (~253 páginas) — productos y servicios para empresas.
3. `/educacion-financiera/` (~2527 páginas, glosario financiero) — no incluida por defecto por
   volumen; puede habilitarse agregando el prefijo a `SCRAPER_SECTIONS` en `.env`.

El número máximo de páginas por corrida es configurable (`SCRAPER_MAX_PAGES`, por defecto 150)
para mantener tiempos de scraping/indexado acotados en un entorno de solo CPU.

## Fase 1 — Estructura del repositorio

```
.
├── data/
│   ├── raw/            # HTML crudo + manifest.json descargado por el scraper (gitignored)
│   └── processed/      # JSON con texto limpio por página (Fase 3, gitignored)
├── scraper/             # Módulo de web scraping (Fase 2)
├── cleaning/             # Módulo de limpieza/normalización (Fase 3)
├── requirements.txt
├── .env.example
└── README.md
```

Las carpetas `app/`, `eval/`, `analytics/` y `docker/` se agregarán en las fases
correspondientes, para no crear estructura vacía por adelantado.

## Fase 2 — Web scraping

Módulo `scraper/`:

- `config.py`: carga la configuración desde variables de entorno (`.env`).
- `http_headers.py`: cabeceras HTTP tipo navegador (ver sección anterior sobre el WAF).
- `http_client.py`: GET con reintentos/backoff, usado para sitemap y robots.txt.
- `robots.py`: parsea `robots.txt` (reglas `Disallow` con y sin comodines) y cachea el
  resultado en `data/raw/_robots_cache.txt`.
- `sitemap_crawler.py`: descarga y parsea el sitemap XML (con caché en
  `data/raw/_sitemap_cache.xml`), filtra las URLs según las secciones priorizadas y las
  reglas de `robots.txt`, y devuelve la lista final a scrapear (respetando el límite
  `SCRAPER_MAX_PAGES`).
- `fetcher.py`: descarga cada página con reintentos/backoff, límite de tiempo (timeout),
  espera entre requests (rate limiting) y un User-Agent identificable con datos de contacto.
- `run_scraper.py`: script orquestador (CLI). Guarda el HTML crudo en `data/raw/<slug>.html`
  y un manifiesto `data/raw/manifest.json` con metadata de cada página (URL, sección, estado
  HTTP, tamaño, fecha de descarga).

### Cómo ejecutar el scraper

```bash
pip install -r requirements.txt
cp .env.example .env
python -m scraper.run_scraper
```

### Resultado de la corrida

149/150 páginas descargadas correctamente (~36 MB de HTML crudo). El único error es un
`404` real de una landing dada de baja (`/personas/landings/apoyos/Consejeria_CIFEM.html`).

### Supuestos y limitaciones de esta fase

- Se respetan las reglas de `Disallow` declaradas en `robots.txt` de bbva.mx.
- No se realiza scraping recursivo por enlaces (crawling); las URLs se obtienen únicamente
  del sitemap oficial del sitio, lo cual es suficiente para este alcance y evita generar
  tráfico innecesario.
- El almacenamiento de datos **limpios** (texto normalizado, sin boilerplate de navegación/
  cookies) se implementa en la Fase 3; en esta fase solo se persiste el HTML crudo tal como
  se recibió del servidor.
- Ver la sección "Decisión sobre el sitio objetivo" arriba para el detalle del bloqueo de
  bbva.com.co que motivó el cambio a bbva.mx.

## Fase 3 — Limpieza y normalización de datos

Módulo `cleaning/`:

- `config.py`: configuración (directorio de entrada/salida, umbral mínimo de texto).
- `html_cleaner.py`: quita etiquetas estructurales (`script`, `style`, `nav`, `header`,
  `footer`, etc.), prioriza el contenido dentro de `<main>` si existe, y descarta líneas de
  boilerplate conocido del sitio (banner de cookies, textos de accesibilidad del menú como
  "Ir al contenido principal" o "Pulsa enter") observadas al inspeccionar páginas reales del
  grupo BBVA durante el desarrollo. Es un heurístico: se validó sin residuos de boilerplate
  en las 146 páginas reales procesadas, pero podría necesitar ajuste fino con más contenido.
- `run_cleaner.py`: script orquestador (CLI). Lee `data/raw/manifest.json`, limpia cada página
  descargada con éxito y guarda un JSON por página en `data/processed/<slug>.json` con
  `url`, `sección`, `title`, `fetched_at` y `text`. Páginas cuyo texto limpio quede por debajo
  de `CLEANING_MIN_TEXT_LENGTH` (ruido/errores de parseo) se descartan.

### Cómo ejecutar la limpieza

```bash
python -m cleaning.run_cleaner
```

### Resultado de la corrida

Sobre las 149 páginas descargadas: **146 limpiadas** y guardadas en `data/processed/`
(promedio ~4150 caracteres de texto útil por página), **3 omitidas** por quedar con muy poco
texto tras la limpieza (páginas de organigrama/video/widget de tipo de cambio, con casi todo
el contenido en imágenes — correctamente descartadas por no aportar texto indexable), y
**1 omitida** por el error de descarga (404) de la Fase 2. Se verificó manualmente que no
queda boilerplate residual (cookies, nav, menú) en el texto limpio.
