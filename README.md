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

El enunciado propone `https://www.bbva.com.co/`, permitiendo explícitamente usar otro banco
si es necesario. Se verificó que **BBVA Colombia bloquea el acceso mediante un WAF**: tanto
la home como `/robots.txt` devuelven `HTTP 403` con una página de error genérica ("Algo salió
mal"), de forma consistente sin importar el User-Agent utilizado.

Por esto se optó por **BBVA México (`https://www.bbva.mx`)** como sitio objetivo:

- Mismo grupo corporativo (BBVA), contenido institucional en español y de naturaleza
  equivalente (productos para personas/empresas, educación financiera, etc.).
- Responde `HTTP 200` de forma estable y su `robots.txt` es permisivo (solo excluye rutas
  puntuales como `/icons/`, `/illustrations/`, `/sala-de-prensa/`, variantes de archivo por
  plataforma, etc.), además de declarar `Sitemap: https://www.bbva.mx/sitemap.xml`.
- El contenido se sirve como HTML estático/SSR, por lo que no requiere un navegador headless
  (Playwright/Selenium) para extraerlo — basta con `requests` + `BeautifulSoup`.

El sitemap contiene ~3750 URLs. Para acotar el alcance a un tiempo de entrega razonable, el
scraper prioriza por secciones (configurable vía `.env`):

1. `/personas/` (~936 páginas) — productos y servicios para personas físicas.
2. `/empresas/` (~253 páginas) — productos y servicios para empresas.
3. `/educacion-financiera/` (~2527 páginas, glosario financiero) — **no incluida por defecto**
   en esta prueba técnica por volumen; puede habilitarse agregando el prefijo a
   `SCRAPER_SECTIONS` en `.env`.

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
- `sitemap_crawler.py`: descarga y parsea el/los sitemap(s) XML, filtra las URLs según las
  secciones priorizadas y las reglas de `robots.txt`, y devuelve la lista final a scrapear
  (respetando el límite `SCRAPER_MAX_PAGES`).
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

- Se respetan las reglas de `Disallow` declaradas en `robots.txt` de bbva.mx.
- No se realiza scraping recursivo por enlaces (crawling); las URLs se obtienen únicamente
  del sitemap oficial del sitio, lo cual es suficiente para este alcance y evita generar
  tráfico innecesario.
- El almacenamiento de datos **limpios** (texto normalizado, sin boilerplate de navegación/
  cookies) se implementa en la Fase 3; en esta fase solo se persiste el HTML crudo tal como
  se recibió del servidor.
