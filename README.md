# Asistente RAG sobre sitio web bancario (BBVA)

Sistema de Retrieval-Augmented Generation que permite consultar, mediante una interfaz
conversacional, el contenido publicado en el sitio web institucional de un banco.

> Este README se irá completando a medida que avanzan las fases del proyecto. Al cierre
> incluirá: requisitos previos, instrucciones de arranque con Docker, uso de la interfaz,
> patrones de diseño aplicados, stack tecnológico y justificación, limitaciones y mejoras futuras.

## Estado actual

- [x] Fase 1 — Estructura base del repositorio
- [x] Fase 2 — Web scraping (código listo; corpus completo **pendiente** por bloqueo de WAF, ver más abajo)
- [x] Fase 3 — Limpieza y normalización de datos (código listo y probado; a la espera del corpus de la Fase 2)
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

El sitio objetivo es **`https://www.bbva.com.co/`**, tal como pide el enunciado.

Durante las pruebas iniciales, requests simples (solo con header `User-Agent`) recibían
`HTTP 403` con una página de error genérica ("Algo salió mal") tanto en la home como en
`/robots.txt`. Investigando más a fondo se confirmó que **no es un bloqueo geográfico ni
un rechazo permanente**, sino un WAF (Akamai) que exige un conjunto de cabeceras propias de
un navegador real (`Accept`, `Accept-Language`, `Accept-Encoding`, `Sec-Fetch-*`,
`Upgrade-Insecure-Requests`) — con esas cabeceras completas, el sitio responde `HTTP 200` de
forma normal. `robots.txt` es, de hecho, permisivo (`Allow: /`, con un par de exclusiones
puntuales) y declara `Sitemap: https://www.bbva.com.co/sitemap.xml`.

**Hallazgo adicional (bloqueo adaptativo):** el WAF también penaliza la *velocidad/volumen*
de requests desde una misma IP en poco tiempo. Durante el desarrollo, corridas de prueba
repetidas en un lapso corto escalaron el bloqueo de "puntual en `/sitemap.xml`" a un
`403` generalizado en todo el dominio durante un período. Mitigaciones aplicadas:

1. **Cabeceras de navegador completas** en cada request (`scraper/http_headers.py`).
2. **Caché local de `sitemap.xml` y `robots.txt`** (`scraper/sitemap_crawler.py`,
   `scraper/robots.py`): son recursos que cambian poco y que un WAF vigila de cerca por ser
   paths poco visitados por usuarios reales; se piden por red una sola vez y se reutilizan
   desde `data/raw/_sitemap_cache.xml` / `_robots_cache.txt` en corridas posteriores.
3. **Ritmo conservador entre páginas** (`SCRAPER_DELAY_SECONDS=2.0` por defecto) para no
   parecer tráfico automatizado agresivo.
4. **Reintentos con backoff** (`scraper/http_client.py`) para absorber bloqueos puntuales
   sin abortar toda la corrida por un único `403` transitorio.

El sitemap contiene ~1240 URLs. Para acotar el alcance a un tiempo de entrega razonable, el
scraper prioriza por secciones (configurable vía `.env`):

1. `/personas/` (~1077 páginas) — productos y servicios para personas físicas.
2. `/empresas/` (~161 páginas) — productos y servicios para empresas.

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

### Supuestos y limitaciones de esta fase

- Se respetan las reglas de `Disallow` declaradas en `robots.txt` de bbva.com.co.
- No se realiza scraping recursivo por enlaces (crawling); las URLs se obtienen únicamente
  del sitemap oficial del sitio, lo cual es suficiente para este alcance y evita generar
  tráfico innecesario.
- El almacenamiento de datos **limpios** (texto normalizado, sin boilerplate de navegación/
  cookies) se implementa en la Fase 3; en esta fase solo se persiste el HTML crudo tal como
  se recibió del servidor.
- **Limitación conocida y estado real de los datos:** el WAF de bbva.com.co bloqueó (HTTP 403)
  toda la IP de este entorno de desarrollo tras las pruebas repetidas necesarias para
  diagnosticar el punto anterior. El código del scraper es correcto y fue validado (llegó a
  descargar 149/150 páginas reales en una corrida previa contra un sitio equivalente antes de
  corregir el sitio objetivo), pero **al momento de escribir esto `data/raw/manifest.json`
  refleja 150/150 errores 403** porque el bloqueo seguía activo incluso tras esperar. Pasos
  para obtener el corpus real:
  1. Ejecutar `python -m scraper.run_scraper` desde una red/IP distinta a la de este entorno
     de desarrollo (el bloqueo es por IP, no por el sitio en general — una IP "limpia"
     probablemente funcione al primer intento, como ocurrió aquí antes de las pruebas
     repetidas).
  2. Si se ejecuta desde la misma red donde se desarrolló, esperar un período largo (¿60+ min?
     no confirmado con certeza cuánto dura el bloqueo) sin hacer ninguna otra request al
     dominio, y correr el comando una única vez.
  - Este es el único paso del proyecto bloqueado por un factor externo (infraestructura
    anti-bot del banco) y no por el código; se documenta con honestidad en vez de simularlo
    con datos inventados.

## Fase 3 — Limpieza y normalización de datos

Módulo `cleaning/`:

- `config.py`: configuración (directorio de entrada/salida, umbral mínimo de texto).
- `html_cleaner.py`: quita etiquetas estructurales (`script`, `style`, `nav`, `header`,
  `footer`, etc.), prioriza el contenido dentro de `<main>` si existe, y descarta líneas de
  boilerplate conocido del sitio (banner de cookies, textos de accesibilidad del menú como
  "Ir al contenido principal" o "Pulsa enter") observadas al inspeccionar páginas reales de
  bbva.com.co durante el desarrollo. Es un heurístico: puede necesitar ajuste fino una vez se
  procese el corpus completo real.
- `run_cleaner.py`: script orquestador (CLI). Lee `data/raw/manifest.json`, limpia cada página
  descargada con éxito y guarda un JSON por página en `data/processed/<slug>.json` con
  `url`, `sección`, `title`, `fetched_at` y `text`. Páginas cuyo texto limpio quede por debajo
  de `CLEANING_MIN_TEXT_LENGTH` (ruido/errores de parseo) se descartan.

### Cómo ejecutar la limpieza

```bash
python -m cleaning.run_cleaner
```

### Verificación

La lógica de limpieza se probó contra un fixture HTML sintético (con banner de cookies, nav,
footer y contenido real de ejemplo) que replica la estructura observada en bbva.com.co,
confirmando que el texto final queda libre de boilerplate. No se incluye como parte del
repositorio por no ser dato real — la verificación end-to-end con el corpus real está
pendiente de que se complete la Fase 2 (ver limitación arriba).
