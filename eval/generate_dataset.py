"""Etapa 1 de la evaluación: uso -> python -m eval.generate_dataset

Corre el pipeline RAG real (mismo venv/entorno que la app) contra cada pregunta de
`eval/dataset.py` y guarda pregunta + respuesta + contextos recuperados + ground_truth en
`eval/output/eval_dataset.json`.

Se separa en dos etapas (generación acá, scoring en `run_ragas.py`) porque RAGAS 0.1.x
requiere una versión de `langchain` incompatible con el resto del proyecto (ver README,
Fase 13) y corre en un virtualenv distinto (`.venv-eval`) que no tiene instalado
`sentence-transformers`/`chromadb` de la app.
"""
from __future__ import annotations

import json

from eval.config import config
from eval.dataset import EVAL_DATASET
from indexing.config import config as indexing_config
from indexing.embeddings import build_embedder
from rag.config import config as rag_config
from rag.pipeline import build_default_pipeline


def main() -> None:
    embedder = build_embedder(indexing_config.embedding_model)
    pipeline = build_default_pipeline(rag_config, embedder)

    rows = []
    for i, item in enumerate(EVAL_DATASET, start=1):
        print(f"[{i}/{len(EVAL_DATASET)}] {item.question}")
        result = pipeline.run(item.question)
        rows.append(
            {
                "question": item.question,
                "answer": result.answer,
                "contexts": [chunk.text for chunk in result.chunks],
                "ground_truth": item.ground_truth,
            }
        )

    config.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = config.output_dir / "eval_dataset.json"
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardado: {out_path}")


if __name__ == "__main__":
    main()
