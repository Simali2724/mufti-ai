from pathlib import Path
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
ROOT = Path(__file__).resolve().parents[2]
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT/'.env', extra='ignore')
    ollama_base_url: str = 'http://localhost:11434'
    llm_provider_order: str = 'anthropic,openai,gemini,ollama'
    ollama_chat_model: str = 'qwen3:1.7b'
    embedding_model: str = 'bge-m3'
    openai_api_key: str = ''
    google_api_key: str = ''
    anthropic_api_key: str = ''
    whisper_model_size: str = 'base'
    # Cloud deployment: 'gemini' uses Gemini Embedding API, 'ollama' uses local bge-m3
    embedding_provider: str = 'ollama'
    gemini_embedding_model: str = 'text-embedding-004'
    # Set to 'cloud' to disable Ollama-dependent features (voice, local fallback)
    deploy_mode: str = 'local'
    enable_knowledge_graph: bool = True
    retrieval_top_k: int = 6
    retrieval_candidates: int = 30
    rerank_threshold: float = .42
    lexical_floor: float = .25
    # Evidence size is fitted to the model that will actually answer. Measured on this 2 GB
    # MX450 with qwen3:1.7b on the same question: 8 windows / 2400 tokens made the answer call
    # take 492s, while 6 windows / 1500 tokens took 215s and produced MORE resolvable claims
    # (10, from pages 50, 257 and 280). A cloud model has no such limit.
    evidence_windows: int = 6
    # Raised from 8 for the explanation path (2026-11-16): a cloud model reads 12 passages in
    # seconds, and a complete explanation needs the surrounding passages, not only the best one.
    evidence_windows_cloud: int = 12
    # At most this many adjacent-concept passages may take evidence slots when the question
    # named a reviewed concept. They stay visible to the reader as related material.
    evidence_related_windows: int = 2
    # How far a passage is demoted when the question named a reviewed concept and the
    # passage carries no surface form of it. Swept against the 48-case benchmark; see
    # VERIFICATION.md for the measured window-recall at each value.
    off_concept_factor: float = .9
    evidence_token_budget: int = 1500
    evidence_token_budget_cloud: int = 12000
    # 'explain' (default): one streamed, cited, teacher-style answer plus a faithfulness audit
    # (app/agents/explain_agent.py). 'strict': the original claim-by-claim pipeline.
    answer_mode: str = 'explain'
    # Fact-check every explanation sentence against all sources with a second model call.
    explain_audit: bool = True
    # The audit on the local 1.7B model costs minutes and a small model is an unreliable
    # judge, so locally the answer is shown with citations and labelled as not audited.
    audit_local: bool = False
    # Seconds the fact-check may take before the answer is shown labelled as not audited.
    audit_timeout: float = 25
    # Strong first-pass audit (task 'audit_strong', gemini-2.5-flash): measured 8.5-25 s on 6-17
    # sentences, so it gets a longer budget; on timeout the lite audit gets audit_timeout.
    strong_audit: bool = True
    strong_audit_timeout: float = 40
    answer_max_sections: int = 5
    answer_max_claims: int = 8
    max_verifier_retries: int = 2
    # Targeted repair of individual rejected claims (app/agents/repair_agent.py). One round
    # only: a claim its own span could not support after a focused rewrite is not going to be
    # supported by a third attempt, and on this hardware every extra model call is minutes.
    max_repair_rounds: int = 1
    repair_max_claims: int = 4
    repair_with_model: bool = True
    # A second search round costs another answer and verifier call. On this 2 GB GPU that is
    # 215-550s each and pushed a live request past 1800s, so locally one round is reported
    # rather than leaving the reader waiting half an hour. Raise to 2 to expand locally too.
    max_search_rounds_local: int = 1
    deterministic_router: bool = True
    # Ask a model to classify questions the rules are unsure about. Off since 2026-11-16: a
    # lite router refused a real book question as out_of_scope; unsure questions are searched.
    model_router: bool = False
    deterministic_query_rewrite: bool = True
    # A first-turn question has no conversation context to resolve, so the rewrite call only
    # supplies machine translations. Measured on the 29 benchmark cases that ran both ways
    # (eval/benchmark-retrieval-segments-*.json): window recall and top-3 recall were IDENTICAL
    # (24/29 and 23/29) while total retrieval time fell from 1102s to 106s, because on a 2 GB GPU
    # each rewrite forces an embedding/chat model swap costing 90-144s. The local 3B model's
    # translations were also corrupt (Devanagari and Cyrillic characters inside Urdu output).
    # So: skip it on a local model, and still use it when a cloud model is actually available,
    # where it is cheap and its translations are usable. `True` forces it on regardless.
    model_rewrite_without_history: bool = False
    # Bounded page-tree navigation over the PDF outline's clean section titles
    # (app/retrieval/tree_nav.py). OFF by default on measurement, not on principle: over all
    # 48 benchmark cases it left window_recall and top3_recall identical (0.810 / 0.738),
    # lowered candidate_recall from 0.881 to 0.857 by spending the candidate budget, and cost
    # ~0.1s per question. The brief says keep the simplest configuration that improves
    # measured quality, and this one does not improve it. Set True to re-measure; the tree
    # itself stays in use regardless, because its clean titles supply evidence headings and
    # the rival-concept test (see app/ingestion/book_tree.py).
    enable_tree_route: bool = False
    tree_candidates: int = 12
    enable_reranker: bool = False
    retriever_mcp_url: str = ''
    port: int = 786
    # Warm the search stack in the background at server start (app/core/warmup.py). Tests turn it off.
    warmup_on_start: bool = True
settings = Settings()
config = yaml.safe_load((ROOT/'config.yaml').read_text())
# In cloud mode, use the pre-built cloud-index directory; locally use data/index
if settings.deploy_mode == 'cloud' and (ROOT/'data/cloud-index').exists():
    INDEX = ROOT/'data/cloud-index'
else:
    INDEX = ROOT/'data/index'
BOOKS = ROOT/'data/books'
INDEX.mkdir(parents=True, exist_ok=True)
BOOKS.mkdir(parents=True, exist_ok=True)
