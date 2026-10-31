# Pinned environments (isolated venvs; never one combined stack)

| File | Used for | Python |
|---|---|---|
| `llama_gpt.txt` | vLLM Llama generation, GPT AsyncOpenAI generation, offline tests | 3.11 |
| `evaluation.txt` | COMET/BLEU/chrF++, statistics, flags, figures, freeze builder | 3.11 (torch from cu124 index) |
| `retrieval.txt` | LaBSE/FAISS job preparation | 3.11 (torch from cu124 index) |
| `nllb.txt` | NLLB-200 3.3B baseline generation, splitter gates | 3.13 (torch from cu130 index) |

Install exactly as in the notebooks (`uv pip install --python <venv> -r <file>`; install torch first from the indicated index). Each run also saves `requirements_resolved.txt` with the full resolved set.
