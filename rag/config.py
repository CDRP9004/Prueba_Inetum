"""Configuración del pipeline RAG (Fase 5): retrieval y generación."""
from dataclasses import dataclass

from dotenv import load_dotenv
import os

load_dotenv()


@dataclass(frozen=True)
class RagConfig:
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    llm_model: str = os.getenv("LLM_MODEL", "llama3.2:3b")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    top_k: int = int(os.getenv("RAG_TOP_K", "5"))
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))

    # --- Retrieval híbrido + MMR (Fase 9) ---
    use_hybrid_search: bool = os.getenv("USE_HYBRID_SEARCH", "true").lower() == "true"
    rrf_k: int = int(os.getenv("RRF_K", "60"))
    mmr_lambda: float = float(os.getenv("MMR_LAMBDA", "0.5"))
    retrieval_candidate_multiplier: int = int(os.getenv("RETRIEVAL_CANDIDATE_MULTIPLIER", "4"))

    # --- Reranker (Fase 10) ---
    use_reranker: bool = os.getenv("USE_RERANKER", "true").lower() == "true"
    reranker_model: str = os.getenv("RERANKER_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    # Cuántos candidatos de más se recuperan antes de rerankear y quedarse con `top_k`
    rerank_candidate_multiplier: int = int(os.getenv("RERANK_CANDIDATE_MULTIPLIER", "3"))


config = RagConfig()
