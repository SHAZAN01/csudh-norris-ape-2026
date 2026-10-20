# Internal reviewer preparation memo

This is an anticipated-objections memo for the development draft. It is not a response to an actual conference review or a claim that the main experiment is complete.

## 1. Is this a new APE method, or the earlier ICAI system on different languages?

The manuscript explicitly treats frozen-NMT anchoring and semantic exemplar retrieval as prior methods. The ICAI comparison is disclosed in Related Work and in the page-level overlap audit. The proposed contribution is a controlled empirical evaluation of a stronger NLLB draft, four Tagalog/Spanish directions, two fixed editors, and preservation/output-contract behavior. Whether that contribution is sufficient for submission remains a PI/editorial judgment. Different encoders or JSON formats alone are not presented as novelty.

## 2. Does a 56.75% fallback rate make the reasoning comparison invalid?

It prevents an intrinsic claim about the benefits or costs of reasoning. It does not erase the operational result of the specified model-prompt-validator policy. All 400 planned Llama diagnostic outcomes remain in the primary evaluation, including 227 baseline fallbacks. Plain zero-shot and one-shot have no fallbacks. The manuscript separates parsing from validity and explains the stricter diagnostic contract. A redesigned contract would be a documented new dev condition; it cannot silently replace the measured condition after observing test outcomes. The disposition is unresolved before freeze.

## 3. Do metric gains show useful, safe post-editing for low-resource communities?

No such general conclusion is supported. There are only two language pairs; resource availability, direction and starting quality are confounded. FLORES+ has standard Spanish and translation references rather than human minimal post-edits. The pilot is development data and has no independent human ratings. Item 429 demonstrates numeric corruption despite a COMET gain; item 825 illustrates a metric penalty without equally obvious meaning loss. These source-based examples motivate separate fidelity and validity analysis, not a measured population error rate or a community deployment claim.

## Model choice and scope

GPT-4o Mini and original Llama 3 8B implement the approved, computationally accessible model matrix. They are not claimed to be frontier representatives in 2026. Results must be tied to the dated snapshot and pinned open-weight revision. No scaling conclusion follows from comparing these two models.

## Evidence needed for the next revision

Resolve the overlap and diagnostic-policy decisions, record the exact protocol and comparison families, complete the held-out run and analysis, confirm the byline and ICAI publication metadata, then replace the development abstract, results and conclusion. Do not remove unsuccessful conditions or relabel development intervals as confirmatory results.
