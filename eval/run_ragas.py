"""Etapa 2 de la evaluación: uso -> (desde .venv-eval) python -m eval.run_ragas

Lee `eval/output/eval_dataset.json` (generado por `eval.generate_dataset` en el venv
principal), calcula las métricas de RAGAS usando Ollama como juez LLM (self-hosted, sin
costo) y el mismo modelo de embeddings del resto del proyecto, y guarda el reporte en
`eval/output/report.json`.
"""
from __future__ import annotations

import json

from datasets import Dataset
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from ragas import evaluate
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
from ragas.run_config import RunConfig

from eval.config import config

# Un único servidor Ollama en CPU no aguanta los 16 workers concurrentes por defecto de
# RAGAS (cada uno dispara varias llamadas al LLM): satura el servidor y la mayoría de los
# jobs terminan en TimeoutError. Bajar la concurrencia y subir el timeout por job es más
# lento pero mucho más confiable con un LLM local pequeño.
OLLAMA_RUN_CONFIG = RunConfig(timeout=300, max_workers=2)


def main() -> None:
    dataset_path = config.output_dir / "eval_dataset.json"
    if not dataset_path.exists():
        print(f"No existe {dataset_path}. Corré primero (en el venv principal): "
              "python -m eval.generate_dataset")
        return

    rows = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset = Dataset.from_list(rows)

    llm = Ollama(model=config.judge_model, base_url=config.ollama_host)
    embeddings = HuggingFaceEmbeddings(model_name=config.embedding_model)

    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=llm,
        embeddings=embeddings,
        run_config=OLLAMA_RUN_CONFIG,
    )

    report = result.to_pandas()
    out_path = config.output_dir / "report.json"
    report.to_json(out_path, orient="records", indent=2, force_ascii=False)

    print("\n=== Promedios ===")
    for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        if metric in report.columns:
            print(f"{metric}: {report[metric].mean():.3f}")

    print(f"\nReporte detallado guardado en: {out_path}")


if __name__ == "__main__":
    main()
