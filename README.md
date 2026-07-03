# Asistente RAG sobre sitio web bancario (BBVA)

Sistema de Retrieval-Augmented Generation que permite consultar, mediante una interfaz
conversacional, el contenido publicado en el sitio web institucional de un banco.

> Este README se irá completando a medida que avanzan las fases del proyecto. Al cierre
> incluirá: requisitos previos, instrucciones de arranque con Docker, uso de la interfaz,
> patrones de diseño aplicados, stack tecnológico y justificación, limitaciones y mejoras futuras.

## Estado actual

- [x] Fase 1 — Estructura base del repositorio
- [x] Fase 2 — Web scraping (captura de datos crudos)
- [ ] Fase 3 — Limpieza y normalización de datos
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
│   ├── raw/            # HTML crudo descargado por el scraper (gitignored)
│   └── processed/      # Texto limpio (Fase 3, gitignored)
├── scraper/             # Módulo de web scraping (Fase 2)
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
- **Limitación conocida:** el WAF de bbva.com.co puede bloquear temporalmente (HTTP 403) toda
  una IP si detecta muchas requests en poco tiempo — algo fácil de gatillar durante desarrollo
  iterativo/pruebas. Si al ejecutar `python -m scraper.run_scraper` la mayoría de páginas
  devuelven error 403 en el manifiesto, es ese bloqueo temporal: esperar 30-60 minutos sin
  hacer más requests al dominio y volver a correr el comando (usa `_sitemap_cache.xml` /
  `_robots_cache.txt` si ya existen, así que no vuelve a golpear esos endpoints).
