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
- [x] Fase 4 — Chunking, embeddings e indexación vectorial (870 chunks en ChromaDB)
- [x] Fase 5 — Pipeline RAG base (retrieval + Ollama, probado por CLI)
- [x] Fase 6 — API de chat (FastAPI, probada en vivo con `POST /chat`)
- [x] Fase 7 — Historial de conversación persistente (SQLite, ventana N configurable)
- [x] Fase 8 — Interfaz web mínima (chat servido por FastAPI en `/`)
- [x] Fase 9 — Retrieval híbrido (dense + BM25 + RRF) y MMR
- [x] Fase 10 — Reranker (cross-encoder multilingüe)
- [x] Fase 11 — Observabilidad con Langfuse (implementada; sin cuenta propia para verificar trazas en vivo, ver limitación)
- [x] Fase 12 — Dockerización completa (probado de punta a punta, stack real corriendo en contenedores)
- [x] Fase 13 — Evaluación con RAGAS (10 preguntas reales, resultados en el README)
- [x] Fase 14 — Analítica del histórico de conversaciones (CLI + API + página web, probado con datos reales)
- [x] Fase 15 — Manejo de errores y endurecimiento
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

## Fase 4 — Chunking, embeddings e indexación vectorial

Módulo `indexing/`:

- `config.py`: tamaño/solape de chunk, modelo de embeddings, directorio y nombre de la
  colección de Chroma (todo configurable vía `.env`).
- `chunker.py`: divide el texto limpio de cada página en chunks de hasta `CHUNK_SIZE`
  caracteres con `CHUNK_OVERLAP` de solape, respetando límites de párrafo cuando es posible
  (evita cortar frases a la mitad salvo que un párrafo individual sea más largo que el chunk).
- `embeddings.py`: **Factory Method** (`build_embedder`) que construye el modelo de
  embeddings a partir de su nombre. Usa `intfloat/multilingual-e5-small`
  (sentence-transformers): multilingüe, corre en CPU, gratuito/self-hosted, y su convención
  de prefijos `query: ` / `passage: ` mejora la calidad del retrieval. El resto del código
  depende solo de la interfaz `Embedder`, no de la librería concreta.
- `vector_store.py`: cliente de **ChromaDB** en modo `PersistentClient` (embebido, sin
  servidor aparte) para desarrollo local; en la Fase 12 se cambia a `HttpClient` apuntando al
  contenedor de Chroma en docker-compose, sin tocar el resto del pipeline.
- `run_indexer.py`: script orquestador (CLI). Lee `data/processed/*.json`, chunkea, calcula
  embeddings en lotes y sube todo a la colección de Chroma. Cada corrida reconstruye la
  colección desde cero (simple y determinístico para el alcance de esta prueba).

### Cómo ejecutar la indexación

```bash
python -m indexing.run_indexer
```

### Resultado de la corrida

**146 documentos → 870 chunks indexados** en la colección `bbva_docs` de ChromaDB
(persistida en `data/chroma/`).

## Fase 5 — Pipeline RAG base

Módulo `rag/`:

- `config.py`: host de Ollama, modelo, temperatura, `top_k` de retrieval (vía `.env`).
- `retriever.py`: **Strategy** — `Retriever` es la interfaz que usa el pipeline;
  `DenseRetriever` es la primera implementación (búsqueda vectorial pura contra Chroma). La
  Fase 9 añadirá `HybridRetriever` (dense + BM25 + RRF) implementando la misma interfaz, sin
  cambiar el pipeline.
- `llm.py`: `OllamaClient`, cliente HTTP mínimo contra `POST /api/chat` del servidor local de
  Ollama (`llama3.2:3b` por defecto — pequeño, corre razonablemente en CPU).
- `prompt.py`: arma el prompt de sistema (instruye a responder solo con el contexto y admitir
  cuando no lo tiene) y el prompt de usuario (contexto recuperado + historial de conversación
  + pregunta). El parámetro `history` ya está soportado aquí para que la Fase 7 solo tenga que
  pasar los mensajes previos, sin modificar esta función.
- `pipeline.py`: **Chain of Responsibility** — `RAGPipeline` ejecuta una lista ordenada de
  `PipelineStep` (`RetrievalStep` → `GenerationStep`) sobre un `RAGContext` compartido. La
  Fase 9 inserta un paso de rerank entre ambos agregando un step a la lista, sin modificar
  `RAGPipeline` ni los steps existentes.
- `cli.py`: CLI de prueba manual (`python -m rag.cli "pregunta"`) para validar retrieval +
  generación antes de exponerlos vía FastAPI en la Fase 6.

### Cómo probar el pipeline

```bash
ollama serve &                      # si no está corriendo ya
ollama pull llama3.2:3b
python -m rag.cli "¿Qué tarjetas de crédito ofrece BBVA?"
```

### Resultado de la prueba

El pipeline retorna respuestas y cita las fuentes (título + URL) usadas. Con el corpus actual
(150 páginas de `/personas/` y `/empresas/`, sin una sección específica de catálogo de
tarjetas), el modelo reconoce honestamente cuando el contexto recuperado no tiene el detalle
exacto pedido, en vez de inventar información — el comportamiento esperado dado el prompt de
sistema. Ampliar `SCRAPER_MAX_PAGES`/secciones mejoraría la cobertura temática.

## Fase 6 — API de chat (FastAPI)

Módulo `app/`:

- `schemas.py`: modelos Pydantic de request/response (`ChatRequest`, `ChatResponse`,
  `SourceItem`).
- `dependencies.py`: **Singleton** vía `lru_cache` — el embedder y el pipeline RAG cargan un
  modelo pesado en memoria, así que se construyen una única vez por proceso y se reutilizan
  en cada request (en vez de recrearse por petición).
- `routers/chat.py`: `POST /chat` — recibe `{session_id, message}`, corre el pipeline RAG y
  devuelve `{answer, sources}`. Incluye manejo de errores: `422` si el mensaje viene vacío,
  `503` si Ollama no responde, `500` para cualquier otro error inesperado (con logging).
- `main.py`: arma la app FastAPI, incluye el router de chat y expone `GET /health`.

`session_id` ya viaja en el request desde esta fase para no tener que romper el contrato de
la API en la Fase 7 (que lo empieza a usar de verdad para persistir/recuperar historial).

### Cómo levantar la API

```bash
ollama serve &                          # si no está corriendo
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Prueba en vivo

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-1", "message": "¿Qué es la banca patrimonial y privada de BBVA?"}'
```

Responde con una respuesta correcta y bien fundamentada en las fuentes reales indexadas
(verificado manualmente contra el corpus de bbva.mx).

## Fase 7 — Historial de conversación persistente

Módulo `history/`:

- `config.py`: ruta de la base SQLite y `HISTORY_WINDOW_N` (mensajes previos usados como
  contexto), ambos configurables vía `.env`.
- `models.py`: modelo ORM `Message` (SQLAlchemy) — `session_id`, `role`, `content`,
  `created_at`.
- `db.py`: engine + fábrica de sesiones; crea las tablas al importarse si no existen.
- `repository.py`: **Repository** — `ConversationRepository` es la única puerta de entrada a
  los datos de conversación para el resto de la app (`add_message`, `get_recent_messages`,
  `get_all_messages`). Cambiar el motor de persistencia (ej. a Postgres) es un cambio
  contenido a este módulo.

`app/routers/chat.py` ahora, en cada request: 1) obtiene los últimos `HISTORY_WINDOW_N`
mensajes de la sesión antes de llamar al pipeline (se pasan como `history` al prompt), y 2)
guarda tanto la pregunta como la respuesta al terminar. `app/routers/history.py` expone
`GET /history/{session_id}` para inspeccionar la conversación completa de una sesión.

### Prueba en vivo

Dos mensajes seguidos en la misma sesión, el segundo con una referencia pronominal al
primero ("¿y a través de qué segmentos se distribuye **eso que mencionaste**?"): la
respuesta entiende correctamente la referencia y retoma el dato de la respuesta anterior,
confirmando que el historial efectivamente entra al contexto del LLM. `GET /history/<id>`
devuelve los 4 mensajes (2 turnos) en orden cronológico.

## Fase 8 — Interfaz web mínima

`app/static/index.html`: página única, autocontenida (HTML + CSS + JS inline, sin
frameworks ni build step), servida directamente por FastAPI en `GET /`. Funcionalidad:

- `session_id` generado con `crypto.randomUUID()` y persistido en `localStorage`, así que
  recargar la página mantiene la misma sesión (y su historial).
- Al cargar, trae el historial previo de la sesión vía `GET /history/{session_id}` y lo
  pinta antes de aceptar mensajes nuevos.
- Cada respuesta muestra sus fuentes (título + link) debajo del mensaje del asistente.
- Errores de la API (503 si Ollama no responde, etc.) se muestran como un mensaje de error
  en el propio chat en vez de fallar silenciosamente.

### Cómo usarla

Con la API corriendo (ver Fase 6), abrir `http://localhost:8000/` en el navegador y escribir
preguntas sobre productos/servicios de BBVA México directamente en el chat.

## Fase 9 — Retrieval híbrido (dense + BM25) y MMR

`rag/hybrid_retriever.py`:

- `BM25Index`: índice BM25 (`rank_bm25`) construido en memoria a partir de todos los chunks
  de la colección de Chroma (tokenización simple por regex + minúsculas). Aporta recall
  léxico (nombres exactos de productos, siglas) que el embedding a veces diluye.
- `HybridRetriever` (implementa `Retriever`, Strategy): combina el ranking denso (Chroma) y
  el ranking BM25 mediante **Reciprocal Rank Fusion** (`RRF_K`, constante estándar 60), que
  fusiona ambos sin necesitar normalizar escalas de score no comparables entre sí.
- Sobre los candidatos fusionados se aplica **MMR** (Maximal Marginal Relevance):
  selecciona iterativamente el siguiente chunk que maximice `MMR_LAMBDA * relevancia -
  (1 - MMR_LAMBDA) * similitud con lo ya elegido`, para no devolver varios chunks casi
  idénticos de una misma página.
- Activable/desactivable con `USE_HYBRID_SEARCH` (si es `false`, se usa `DenseRetriever` de
  la Fase 5). La selección ocurre en `rag/pipeline.py::_build_retriever`, sin tocar
  `RAGPipeline`.

**Nota sobre el campo `score` en las fuentes:** con MMR activo, el orden de salida ya no es
estrictamente monótono por score (por diseño: MMR sacrifica algo de relevancia pura por
diversidad). El primer resultado sigue siendo el más relevante; los siguientes balancean
relevancia y diversidad.

### Cómo probarlo

```bash
python -m rag.cli "¿Qué es la banca patrimonial y privada de BBVA?"
```

## Fase 10 — Reranker

`rag/reranker.py`:

- `RerankStep` (implementa `PipelineStep`, Chain of Responsibility): reordena con un
  **cross-encoder** (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, multilingüe vía mMARCO,
  liviano para CPU) los candidatos recuperados, evaluando el par (pregunta, chunk) de forma
  conjunta — mucho más preciso que comparar embeddings por separado, a costa de ser más
  lento, por lo que solo se aplica sobre un conjunto acotado de candidatos.
- Cuando `USE_RERANKER=true`, `build_default_pipeline` pide `top_k *
  RERANK_CANDIDATE_MULTIPLIER` candidatos en la etapa de retrieval y el reranker los recorta
  de vuelta a `top_k` antes de generar la respuesta. El `score` final de cada fuente pasa a
  ser el score del cross-encoder (reemplaza al de RRF/dense).
- Se inserta entre `RetrievalStep` y `GenerationStep` en la cadena de `rag/pipeline.py` sin
  modificar ninguno de los dos.

### Resultado verificado

Probado en aislado: para la pregunta "¿qué tarjetas de crédito ofrece BBVA?", el
cross-encoder puntuó un chunk relevante sobre tarjetas con **10.8** y uno irrelevante (aviso
de privacidad) con **-4.4** — discriminación clara. Verificado también de punta a punta vía
`POST /chat` con retrieval híbrido + MMR + reranker + generación, todos activos por defecto.

## Fase 11 — Observabilidad con Langfuse

Módulo `observability/`:

- `config.py`: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (por defecto
  `https://cloud.langfuse.com`, el tier gratuito).
- `langfuse_client.py`: construye el cliente y valida credenciales (`auth_check()`) una sola
  vez (cacheado). **Degradación elegante por diseño:** si faltan las keys, o son inválidas,
  o Langfuse no responde, el resto de la app sigue funcionando exactamente igual — solo que
  sin enviar trazas. La observabilidad nunca debe poder tumbar el chat.
- `traced_step.py`: **Decorator** (estructural) — `TracedStep` envuelve cualquier
  `PipelineStep` (retrieval, rerank, generación) agregándole una observación de Langfuse
  (`span`/`retriever`/`generation` según corresponda) alrededor de su ejecución, sin que
  `RetrievalStep`/`RerankStep`/`GenerationStep` sepan que Langfuse existe. `rag/pipeline.py`
  envuelve cada step con `TracedStep` al construir el pipeline.
- `tracing.py`: `traced_chat_request` abre una traza por request en `app/routers/chat.py`,
  usando `propagate_attributes(session_id=...)` del SDK para que las observaciones de los
  steps (hijas, vía OpenTelemetry) queden agrupadas bajo la misma sesión — así se puede ver
  en Langfuse la traza completa de una conversación, no solo de un mensaje suelto.

### Cómo activarlo

1. Crear una cuenta gratuita en [Langfuse Cloud](https://cloud.langfuse.com) (tier free).
2. Copiar las API keys del proyecto a `.env`: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`.
3. Listo — cada request a `/chat` va a generar una traza con sus observaciones de retrieval,
   rerank y generación agrupadas por `session_id`.

### Limitación honesta

No dispongo de una cuenta de Langfuse propia para verificar visualmente las trazas en el
dashboard. Lo que sí verifiqué explícitamente:

1. **Camino sin configurar** (el estado real de este repo): sin keys, `get_langfuse_client()`
   devuelve `None` y toda la instrumentación se vuelve un no-op transparente — probado con
   `python -m rag.cli` y con `POST /chat`, funcionan idénticamente a antes de la Fase 11.
2. **Camino con keys inválidas** (simulando un typo del usuario): `auth_check()` lanza
   `UnauthorizedError`, capturado por `get_langfuse_client()`, logueado, y la respuesta del
   chat se generó con normalidad (mismo resultado que sin keys).
3. La integración sigue la API pública documentada del SDK v3 de Langfuse
   (`start_as_current_observation`, `propagate_attributes`), pero **no pude confirmar que las
   trazas efectivamente aparezcan bien formadas en un dashboard real** con credenciales
   válidas. Si al conectar una cuenta real algo no calza (nombres de campos, jerarquía de
   spans), es el punto más probable de ajuste.

## Fase 12 — Dockerización completa

### Servicios (`docker-compose.yml`)

| Servicio | Imagen | Rol |
|---|---|---|
| `chromadb` | `chromadb/chroma:latest` | Base de datos vectorial, modo servidor (puerto interno 8000, expuesto en `8001` del host) |
| `ollama` | `ollama/ollama:latest` | Sirve el LLM local (puerto `11434`) |
| `ollama-init` | `ollama/ollama:latest` | Contenedor *one-shot*: baja el modelo (`ollama pull`) en el volumen de Ollama y termina |
| `app` | build local (`Dockerfile`) | FastAPI + pipeline RAG completo |
| `ingest` | build local (`Dockerfile`), perfil `ingest` | Pipeline de datos (scraper → cleaner → indexer), a demanda |

`indexing/vector_store.py` soporta modo `persistent` (embebido, desarrollo local) o `http`
(contra el contenedor de Chroma) vía `CHROMA_MODE`; `docker-compose.yml` fija `CHROMA_MODE=http`
para el servicio `app`, sin tocar código.

### Por qué la ingesta de datos no se auto-ejecuta en cada `up`

El scraping depende de acceso a internet a un sitio externo (con el WAF adaptativo que ya
documentamos en la Fase 2) y tarda varios minutos; no tiene sentido dispararlo automáticamente
cada vez que se levanta el stack. Por eso `ingest` es un servicio separado, con su propio
*profile* de Docker Compose, que se corre **una vez** (o cuando se quiera actualizar el
corpus) y no como parte de `docker compose up`.

### Instrucciones paso a paso (desde cero)

```bash
# 1. Clonar y configurar
git clone <url-del-repo> && cd Prueba_Inetum
cp .env.example .env   # ajustar valores si hace falta (modelo, chunk size, N mensajes, etc.)

# 2. Levantar la infraestructura (Chroma + Ollama) y esperar a que estén healthy
docker compose up -d chromadb ollama

# 3. Bajar el modelo de LLM dentro del volumen de Ollama (una sola vez)
docker compose up ollama-init   # corre y termina solo; revisa que loguee "success"

# 4. Poblar los datos: scraping + limpieza + indexación (una sola vez, o cuando se
#    quiera refrescar el corpus)
docker compose --profile ingest run --rm ingest

# 5. Levantar la app
docker compose up -d app

# 6. Usar la interfaz conversacional
# Abrir http://localhost:8000/ en el navegador, o probar directo:
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "¿Qué es la Casa de Bolsa de BBVA?"}'
```

Para arrancadas posteriores (con los datos ya indexados y el modelo ya descargado, ambos
persistidos en volúmenes de Docker), alcanza con:

```bash
docker compose up -d
```

### Verificado en este entorno

Se corrió el stack completo de punta a punta: `chromadb` y `ollama` healthy, `ollama-init`
descargó `llama3.2:3b` (2 GB) dentro del volumen Docker, `ingest` indexó los 146 documentos
reales (870 chunks) contra el Chroma dockerizado vía HTTP, y `POST /chat` respondió
correctamente contra el stack 100% containerizado (misma respuesta y fuentes que en
desarrollo local). También se verificaron `GET /` (interfaz web) y `GET /history/{id}`.

**Nota técnica:** la imagen oficial de `chromadb/chroma` no incluye `curl` ni `wget`, así que
su healthcheck usa `bash -c '</dev/tcp/localhost/8000'` (chequeo TCP) en vez del patrón
`curl -f http://...` más común.

## Fase 13 — Evaluación con RAGAS

### Dataset

`eval/dataset.py`: 10 preguntas con `ground_truth` escritos a mano a partir de contenido
**real** verificado en `data/processed/` (Casa de Bolsa, Banca Patrimonial, seguros de
vida, robo/extravío de tarjeta, cofinanciamiento Infonavit/Fovissste, etc.) — no generadas
sintéticamente ni inventadas, para evaluar contra hechos verdaderos del corpus.

### Por qué dos etapas en dos virtualenvs distintos

`ragas>=0.4` (la versión más reciente) requiere una versión de `langchain-community` que
eliminó el submódulo `langchain_community.chat_models.vertexai` que ragas sigue importando
internamente — es un bug de compatibilidad entre el ragas actual y el langchain actual,
irresoluble por pines de versión sin romper otras dependencias (`instructor` vs
`langchain-openai` piden versiones de `openai` mutuamente excluyentes). La salida estable:
usar `ragas==0.1.21` (misma API de `evaluate()` para las métricas que necesitamos) con su
propia familia de `langchain` 0.2.x, en un **virtualenv separado** (`.venv-eval`,
`requirements-eval.txt`) que no toca las dependencias del venv principal de la app (que no
usa `langchain` en absoluto).

Por eso la evaluación se corre en dos pasos:

```bash
# 1) Generación: corre el pipeline RAG real (venv principal) y guarda
#    pregunta + respuesta + contextos + ground_truth
source .venv/bin/activate
python -m eval.generate_dataset

# 2) Scoring: calcula las métricas de RAGAS (venv aislado)
python3 -m venv .venv-eval && source .venv-eval/bin/activate
pip install -r requirements-eval.txt
python -m eval.run_ragas
```

### Métricas y juez LLM

`faithfulness`, `answer_relevancy`, `context_precision`, `context_recall` — las 4 métricas
"clásicas" de RAGAS. Como juez LLM se usa **el mismo Ollama self-hosted** (`llama3.2:3b` por
defecto, configurable con `RAGAS_JUDGE_MODEL`) en vez de GPT-4, para mantener el stack 100%
gratuito/self-hosted; los embeddings para `answer_relevancy` usan el mismo
`multilingual-e5-small` del resto del proyecto.

### Resultados obtenidos (reales, corpus de bbva.mx)

| Métrica | Promedio |
|---|---|
| faithfulness | 0.685 |
| answer_relevancy | 0.706 |
| context_precision | 1.000 |
| context_recall | 0.630 |

Reporte detallado por pregunta en `eval/output/report.json` (no versionado, se regenera).

### Limitaciones honestas

1. **Juez LLM local y pequeño (3B) en vez de GPT-4.** RAGAS fue diseñado y validado
   originalmente con LLMs mucho más grandes como juez. Un modelo de 3B parámetros puede
   ser inconsistente descomponiendo enunciados o siguiendo el formato estructurado exacto
   que RAGAS espera del juez — de hecho, en la corrida real se registraron 2 warnings
   `"Failed to parse output. Returning None"` (de 40 llamadas), que RAGAS maneja
   devolviendo `None` para esa sub-evaluación en vez de romper toda la corrida. Los
   números son una señal útil y honesta, pero probablemente más ruidosos que con un juez
   más grande.
2. **Concurrencia con Ollama en CPU.** El primer intento, con la concurrencia por defecto
   de RAGAS (16 workers), saturó el único servidor de Ollama y la mayoría de los jobs
   fallaron con `TimeoutError` (`faithfulness` salió en 0.4 y `context_precision` en
   `NaN` — no eran los valores reales, era saturación). Bajar a `max_workers=2` y subir el
   timeout a 300s (`eval/run_ragas.py::OLLAMA_RUN_CONFIG`) resolvió el problema, a costa de
   una corrida más lenta (~26 min para 10 preguntas × 4 métricas). Con un LLM servido por
   una API con más capacidad de concurrencia, esto no sería necesario.
3. **Dataset de 10 preguntas.** Suficiente para demostrar el pipeline de evaluación
   funcionando de punta a punta con métricas reales, pero chico para conclusiones
   estadísticamente robustas sobre la calidad del sistema. Ampliarlo es una mejora futura
   natural (ver sección de mejoras futuras).

## Fase 14 — Analítica del histórico de conversaciones

Se agregó `latency_ms` a `history/models.py::Message` (nullable, solo se completa en
mensajes del asistente) — `app/routers/chat.py` mide el tiempo de `pipeline.run()` con
`time.perf_counter()` y lo guarda junto con la respuesta. Esto habilita métricas de
impacto/performance, no solo de contenido.

Módulo `analytics/`:

- `keywords.py`: extracción simple de palabras clave (regex + stopwords en español) sobre
  los mensajes de **usuario** (no las respuestas del asistente), para ver qué temas
  preguntan realmente los usuarios.
- `metrics.py`: `compute_summary()` calcula, sobre toda la tabla `messages` de
  `history.db`: sesiones totales, mensajes totales (y por rol), promedio de mensajes por
  sesión, latencia promedio y p95 de respuesta, mensajes por día, y las palabras clave más
  frecuentes.
- `run_report.py`: CLI (`python -m analytics.run_report`) que imprime el reporte en
  terminal — la funcionalidad de "recorrer el histórico para extraer métricas" pedida,
  utilizable sin la API.

Expuesto también vía API (`app/routers/analytics.py`, `GET /analytics/summary`) y una
página mínima (`app/static/analytics.html`, `GET /analytics`) con tarjetas de resumen y
tablas — mismo criterio "funcional, no bonita" que la interfaz de chat.

### Resultado con datos reales

Se generaron 5 conversaciones reales de prueba (2 sesiones) y se corrió tanto el CLI como
la API:

```
Sesiones (conversaciones): 2
Mensajes totales: 10 (5 de usuario, 5 del asistente)
Promedio de mensajes por sesión: 5.0
Latencia promedio de respuesta: 17045 ms (p95: 25088 ms)
Temas más frecuentes: crédito (2), casa, bolsa, banca, patrimonial, privada, tarjetas,
seguro, vida, ...
```

La latencia (~17s promedio) refleja el costo real de correr retrieval híbrido + reranker +
generación con un LLM de 3B en CPU sin GPU — un dato honesto y esperable para este stack,
y justamente el tipo de métrica de impacto que esta funcionalidad busca visibilizar.

## Fase 15 — Manejo de errores y endurecimiento

- **Validación de entrada** (`app/schemas.py`): `ChatRequest` ahora exige `session_id` y
  `message` no vacíos (`min_length=1`) y acota `message` a 4000 caracteres
  (`max_length=4000`) — devuelve `422` con el detalle del campo inválido, en vez de dejar
  pasar entradas basura al pipeline.
- **Errores específicos en `/chat`** (`app/routers/chat.py`): `503` si Ollama no responde
  (`requests.exceptions.RequestException`), `503` si ChromaDB no responde
  (`httpx.ConnectError`), `500` genérico con logging para cualquier otro fallo del
  pipeline — cada caso con un mensaje entendible para quien está probando la API, no un
  traceback crudo.
- **Error handling agregado a `/history/{id}` y `/analytics/summary`**: antes no tenían
  ningún manejo de errores propio (Fase 7 y 14 asumían el camino feliz); ahora ambos
  capturan excepciones inesperadas y devuelven `500` con mensaje claro en vez de que
  FastAPI exponga el error interno.
- **Manejador global de excepciones** (`app/main.py::unhandled_exception_handler`): red de
  seguridad final — cualquier excepción no capturada explícitamente en un endpoint devuelve
  `500` con `{"detail": "Ocurrió un error interno inesperado."}` en vez de filtrar un
  traceback interno, y queda logueada del lado del servidor para debug.
- Verificado en vivo: mensaje vacío, `session_id` vacío, mensaje de 5000 caracteres,
  request sin el campo `message`, historial de una sesión inexistente, y analítica sin
  datos — todos responden con el código y mensaje esperado sin romper el servidor.

### Hallazgo real durante las pruebas (bonus de endurecimiento)

Al alternar entre correr la app en Docker (que corre como `root` dentro del contenedor) y
en bare-metal contra el **mismo** `data/history.db` montado por volumen, el contenedor deja
el archivo SQLite con dueño `root`, y el proceso bare-metal (usuario normal) no puede
escribirlo (`attempt to write a readonly database`). No es un bug del código de la app —es
el comportamiento esperable de mezclar ambos modos de ejecución sobre el mismo archivo—
pero vale la pena documentarlo: si esto pasa, `rm data/history.db` (o corregir el dueño del
archivo) y se recrea automáticamente con los permisos correctos la próxima vez que se
escriba desde ese entorno.
