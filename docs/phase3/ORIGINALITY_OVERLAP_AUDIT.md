# Norris and ICAI Methodological Overlap Review

Review date: 19 October 2026. Status: source comparison complete; PI review of shared methods pending before protocol freeze.

## Source and scope

Source: final paper supplied as ICAI (3).pdf, 16 pages, titled Large Language Model-Based Automatic Post-Editing for Test-Time Domain Adaptation in Neural Machine Translation. Authors: Benyamin Ahmadnia, Shazan Mohammed, Sahar Hooshmand, Li Zhou. Page references below refer to the supplied PDF. Its publication metadata and experimental claims were not independently reproduced.

| Dimension | ICAI evidence | Norris evidence and boundary |
|---|---|---|
| Research objective | Test-time domain adaptation across four specialized EN to DE corpora (pp. 1-2, 6). | Quality gains, metric-defined harm, over-editing and direction/resource effects for En/Tl and En/Es. |
| Language and data | English to German; UFAL Medical, JRC-Acquis, OpenSubtitles2016, KDE4/GNOME; 20k/2k/2k train/dev/test per domain (p. 6). | Four directions on revision-pinned FLORES+; dev 997, devtest 1012; 100 aligned pilot IDs. |
| NMT and post-editors | Helsinki-NLP/opus-mt-en-de plus gpt-4-turbo-2024-04-09; beam 5; LLM temperature .2, top_p .95, cap 128 (pp. 4, 6-7). | NLLB-200 3.3B split primary and unsplit diagnostic; GPT-4o Mini and Llama 3 8B; temperature 0, cap 1024. |
| Shared APE architecture | Frozen NMT draft plus source and LLM post-editing without extra training (pp. 3-4). | Same broad architecture. It is prior work and is not claimed as a new Norris method. |
| Shared semantic retrieval | Multilingual Sentence-BERT cosine nearest neighbors; k=3 parallel exemplars (p. 4); pool-size sensitivity (pp. 11-12). | LaBSE plus exact FAISS cosine, top-1 dev exemplar; full pilot-ID and duplicate-source exclusions. Encoder, k and controls differ; retrieval-based APE itself is shared. |
| Prompt conditions | No exemplars, exemplars, and exemplars plus a second terminology-verification call; domain descriptors (pp. 4-7). | Zero shot, retrieved one shot and single-call diagnostic reason-then-edit; no domain descriptor or second verification call. |
| Evaluation | BLEU and COMET; BERTScore ablation; human ratings; terminology/hallucination review; cost/latency (pp. 8-13). | COMET primary, BLEU and chrF++ secondary; dev CIs; planned main Holm families; protect-pool harm and schema/fallback analysis. No external human raters. |
| Contribution boundary | Already establishes and studies NMT anchoring, dense exemplars, no-update APE and verification. NLLB, lower-resource pairs and open LLMs are stated future work (p. 14). | Norris is an empirical extension in those directions with a stronger baseline, two editors, four directions, output-contract failures and over-editing analyses. No blanket first/novel pipeline or retrieval claim. |

## Substantial overlap to disclose

Both studies use source-conditioned LLM post-editing anchored on a frozen NMT draft, include no-example and retrieved-example conditions, and retrieve source-similar parallel exemplars with multilingual sentence embeddings and cosine similarity. These are substantive common methodological elements. They must be cited as prior work. A different encoder, k value, language pair, or JSON schema does not make retrieval-based APE a new invention.

## Proposed manuscript boundary statement

Our earlier study examined LLM post-editing for English-to-German domain adaptation using a frozen OPUS-MT model, GPT-4 Turbo, three retrieved exemplars and an optional terminology-verification pass. The Norris study evaluates a stronger NLLB baseline in four English-Tagalog and English-Spanish directions, compares commercial and open-weight post-editors, and measures over-editing and output-contract failures. We treat NMT anchoring and semantic exemplar retrieval as established components, not as new methodological contributions.

## Scientific and implementation distinctions

The current comparison is not a controlled cross-paper ablation: corpora, languages, baseline strength, model, decoding and metrics differ. No direct numeric superiority claim across the two papers is justified. Reason-then-edit is not the ICAI second-pass verifier. The supplied ICAI manuscript does not identify an exact Sentence-BERT checkpoint or a COMET checkpoint revision; these details are left unspecified here rather than invented.

## Isolation and limits

The supplied Norris pilot code, model manifests, storage paths and logs use the Norris namespace. No ICAI datasets, generations, training artifacts, or code were supplied for byte-level comparison, so this review cannot certify a cross-repository no-copy audit. The Norris benchmark/language/model provenance is documented separately. TRACE-MT remains a separate project; its current protocol and repository were not re-audited in this review. J.UCS is excluded as instructed by the PI.

## Decision required before freeze

The September 24 PI instruction requires substantial overlap to be brought to the PI before freeze. The shared anchoring/retrieval methodology is now explicitly identified. Submit this comparison and the proposed boundary statement for PI review. No protocol freeze or devtest main execution is declared by this package.

ICAI PDF SHA-256: e69c7da86b066baa20bdc39138827dc06beaad062e71ee8d8b1ef2989e6d37f3
Norris evidence ZIP SHA-256: 8d4a608296d4592ea4cc179a7d0a8cb66cfab19035cb9d6e3cf61a471066eb25
