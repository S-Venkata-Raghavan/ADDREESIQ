# AddressIQ: Last-Mile Address Intelligence with Failure Analysis

> Hand this file to Cursor as the source of truth. Build milestone by milestone (Section 13). Do not skip ahead.

---

## 1. Problem statement

In Indian last-mile logistics, a large share of failed first delivery attempts and returns trace back to bad addresses: missing or wrong pincodes, landmark-only text ("near big temple, opp. SBI"), Hinglish and spelling variants ("Hydrabad", "Kukatpalli"), abbreviations ("H.No", "Opp", "Nr"), and conflicts between the written locality and the pincode.

A wrong auto-route costs a wasted delivery attempt, a return-to-origin risk, and a poor customer experience. Over-sending addresses to manual review costs analyst time. **The core problem is not "extract fields". It is deciding when to trust the system and when not to.**

### What AddressIQ does
Takes a raw address string and returns:
1. A structured address (house/building, landmark, locality, city, district, state, pincode)
2. The resolved locality and pincode, with a **calibrated confidence score**
3. A routing decision: `AUTO_ROUTE`, `CONFIRM_WITH_CUSTOMER`, or `MANUAL_REVIEW`
4. A human-readable reason for that decision

### What makes it different from a typical NLP project
- It compares three resolver approaches (rules, small fine-tuned model, LLM) on **accuracy, cost per 1,000 addresses, and latency**.
- It measures **where each approach breaks** using a labeled failure taxonomy and controlled noise injection.
- It reports **calibration** (does 0.9 confidence mean 90% correct?) and a **coverage-vs-risk curve** to justify the review threshold.

### Honesty constraint (non-negotiable)
No Delhivery data is used. All data is public (India Post pincode directory, OpenStreetMap) plus synthetic noisy addresses. The README must say so plainly and must never imply production results.

---

## 2. Users and jobs to be done

| Persona | Job | What they need from the product |
|---|---|---|
| Hub ops analyst | Clear the review queue fast | Sorted queue, side-by-side raw vs. parsed, one-click accept/correct |
| Data scientist | Decide which resolver and threshold to ship | Benchmark dashboard, cost/latency/accuracy trade-offs, calibration plots |
| Recruiter / engineer reviewing the portfolio | Judge depth in under 3 minutes | Live demo, results table, "Where this breaks" page |

---

## 3. Goals, non-goals, success metrics

**Goals**
- G1: End-to-end pipeline with a clean, swappable resolver interface.
- G2: Reproducible benchmark on a labeled synthetic set of 5,000+ addresses across 4 difficulty tiers.
- G3: Calibrated confidence and a defensible decision policy.
- G4: Failure explorer that shows real misresolved examples grouped by cause.

**Non-goals**
- Door-level geocoding or turn-by-turn routing.
- Multi-country support. India only.
- Training a large model from scratch.
- Claiming performance on real customer data.

**Metrics** (report all; targets are aspirational, never fabricate)
- Pincode accuracy, locality accuracy (top-1 and top-3)
- Field-level F1 for entity extraction
- Expected Calibration Error (ECE) and Brier score
- Coverage at fixed risk (e.g., "automation rate at 2% wrong-route rate")
- p50/p95 latency and cost per 1,000 addresses per resolver
- Accuracy vs. noise level curve per resolver

---

## 4. Decision policy (the rules engine)

Every result carries `confidence` in [0,1], `evidence` list, and `conflicts` list.

**Routing rules (evaluated in order; first match wins)**
1. **Hard block to `MANUAL_REVIEW`** if: address text is under 3 meaningful tokens, or no locality candidate found, or two top candidates differ in city.
2. **Pincode conflict rule.** If the written pincode disagrees with the locality-derived pincode:
   - If the locality match confidence is at least 0.85 and the written pincode is not in the candidate locality's pincode set, flag `PINCODE_CONFLICT` and route to `CONFIRM_WITH_CUSTOMER`.
   - If the written pincode is valid for the city but the locality match is below 0.85, trust the pincode, lower the overall confidence by 0.15, and add evidence.
3. **Landmark-only rule.** If there is no locality or pincode and only a landmark: never `AUTO_ROUTE`. Use `CONFIRM_WITH_CUSTOMER` if a landmark maps uniquely in OSM within the city, otherwise `MANUAL_REVIEW`.
4. **Confidence thresholds** (defaults, then tuned on validation data):
   - `confidence >= T_auto` and no conflicts: `AUTO_ROUTE`
   - `T_review <= confidence < T_auto`: `CONFIRM_WITH_CUSTOMER`
   - `confidence < T_review`: `MANUAL_REVIEW`
5. Thresholds are set by a **cost function**: `cost = C_wrong_route * P(wrong | auto) + C_review * P(review)`. Costs are configurable in `config/costs.yaml`. Defaults are illustrative and must be labeled as assumptions.

All rule outcomes must be unit-tested with table-driven tests.

---

## 5. System architecture

```
                 +----------------------+
 Raw address --> |  Normalizer          |  lowercase, expand abbreviations, script
                 |  (deterministic)     |  normalization, remove noise tokens
                 +----------+-----------+
                            v
                 +----------------------+
                 |  Resolver (pluggable)|  A) Rules + fuzzy   B) Token-classifier
                 |  common interface    |  C) LLM structured output
                 +----------+-----------+
                            v
                 +----------------------+
                 |  Gazetteer Matcher   |  candidate localities/pincodes from
                 |  (index lookup)      |  India Post + OSM; phonetic + fuzzy
                 +----------+-----------+
                            v
                 +----------------------+
                 |  Confidence Scorer   |  features -> calibrated probability
                 |  + Calibrator        |  (isotonic / Platt)
                 +----------+-----------+
                            v
                 +----------------------+
                 |  Decision Policy     |  rules in Section 4
                 +----------+-----------+
                            v
        FastAPI  ->  Postgres (results, reviews)  ->  Streamlit UI
                            |
                 Benchmark Runner (offline) -> results parquet -> dashboard
```

### Core interface (Python)
```python
class ResolverResult(BaseModel):
    parsed: ParsedAddress           # structured fields
    candidates: list[Candidate]     # ranked (locality_id, pincode, score)
    raw_confidence: float
    latency_ms: float
    cost_usd: float                 # 0.0 for local resolvers
    metadata: dict                  # model name, prompt version, etc.

class Resolver(Protocol):
    name: str
    def resolve(self, address: str) -> ResolverResult: ...
```
All three resolvers implement this. The benchmark runner only talks to this interface.

### Tech stack
- Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, Postgres (SQLite allowed for local dev)
- `rapidfuzz` for fuzzy matching, `jellyfish` or `indic-transliteration` for phonetic/transliteration handling
- Hugging Face `transformers` for a small multilingual token-classification model (e.g., a MuRIL or XLM-R base checkpoint; pick one and record it in a model card)
- LLM resolver via OpenRouter with JSON-schema constrained output; cache all calls to disk to make benchmarks reproducible and cheap
- Streamlit for the UI; Plotly for charts
- `pytest`, `ruff`, `mypy`, `pre-commit`; Docker Compose for one-command startup

---

## 6. Data plan

### Sources
1. **India Post pincode directory** (data.gov.in): office name, pincode, district, state.
2. **OpenStreetMap** (Geofabrik extracts or Overpass API): localities/suburbs, landmarks (temples, banks, schools, hospitals) for 4 to 6 pilot cities. Suggested pilots: Hyderabad, Bengaluru, Delhi NCR, Mumbai, Chennai, plus one tier-2 city (e.g., Vijayawada). Attribute OSM (ODbL) in the README.

### Gazetteer build
- One row per locality: `locality_id, name, aliases[], city, district, state, pincodes[], lat, lon`.
- Aliases come from OSM `alt_name`, India Post office names, and generated transliteration variants.

### Synthetic address generator
Generate clean ground-truth addresses from templates, then apply **noise operators**. Store the operator list on every row so failures can be traced to causes.

| Operator | Example |
|---|---|
| Spelling/transliteration variant | Hyderabad -> Hydrabad, Kukatpally -> Kukatpalli |
| Abbreviation and format noise | House No -> H.No, Opposite -> Opp, Near -> Nr |
| Hinglish word order/fillers | "wahan pe near SBI bank" |
| Missing pincode | pincode dropped |
| Wrong pincode | swapped with a neighboring locality's pincode |
| Missing locality | locality dropped, landmark kept |
| Landmark-only | only "opp. Ganesh temple, <city>" |
| Duplicate/scrambled tokens | repeated city, shuffled clauses |
| Typos | edit-distance 1 to 3 |

### Difficulty tiers
- **T1 Clean:** full address, correct pincode
- **T2 Noisy:** spelling and format noise, correct pincode
- **T3 Sparse:** missing or wrong pincode, Hinglish
- **T4 Hard:** landmark-only or conflicting signals

### Splits
Split **by locality, not by row**, so the test set contains localities unseen in training (prevents leakage). Fixed seeds. Store split manifests in `data/splits/`.

### Ground-truth schema
`address_id, raw_text, true_locality_id, true_pincode, true_city, tier, noise_ops[], split`

A small hand-labeled set of **200 addresses** (written by you, realistic and messy) should be kept separate as a sanity check that the synthetic noise is not too easy.

---

## 7. The three resolvers

**A. Rules + fuzzy (baseline)**
Normalize, regex-extract pincode, tokenize, fuzzy-match against gazetteer aliases with phonetic keys, rank by weighted score. Must be fully deterministic.

**B. Fine-tuned token classifier**
BIO tagging for `HOUSE, BUILDING, LANDMARK, LOCALITY, CITY, PINCODE`. Train on synthetic train split; evaluate on unseen localities. The output spans then go through the same gazetteer matcher as A.

**C. LLM with structured output**
Prompt versioned in `prompts/v1.md`. JSON schema enforced. Includes a shortlist of gazetteer candidates in the prompt (retrieval-augmented) so the LLM chooses rather than invents. Temperature 0. Every call cached by hash of (model, prompt version, address).

**Hybrid (stretch):** use B or A first, escalate to C only when confidence is low. Report cost savings vs. always calling C.

---

## 8. Confidence and calibration

- Features: top-1 vs. top-2 margin, fuzzy score, pincode agreement, token coverage, landmark uniqueness, resolver agreement (when running two resolvers).
- Fit a calibrator (isotonic or Platt) on the **validation** split, evaluate on test.
- Report: reliability diagram, ECE, Brier score, and coverage-vs-risk curve.
- The decision thresholds `T_auto` and `T_review` are chosen from the cost function in Section 4 and shown on the curve.

---

## 9. Evaluation protocol

1. Run all resolvers on the same test set with the same seed and cached inputs.
2. Report metrics overall, **per tier, and per noise operator**.
3. **Noise sweep:** increase typo/transliteration noise in steps and plot accuracy per resolver.
4. Bootstrap 95% confidence intervals for headline numbers.
5. Cost per 1,000 addresses and p50/p95 latency measured on the same machine; record hardware in the README.
6. Save all raw predictions to parquet so any chart can be regenerated.

### Failure taxonomy (every wrong prediction gets one primary tag)
`TRANSLITERATION_MISS`, `LANDMARK_AMBIGUOUS`, `PINCODE_CONFLICT_WRONG_TRUST`, `WRONG_CITY_SAME_LOCALITY_NAME`, `TOKEN_TRUNCATION`, `LLM_HALLUCINATED_LOCALITY`, `GAZETTEER_GAP`, `OTHER`.
Auto-tag with heuristics, then manually review a sample of 100 to check the tagger.

---

## 10. Product design (UI)

Streamlit multipage app. Keep it clean and fast; no decoration that costs time.

1. **Playground:** input box, resolver dropdown, structured output, confidence gauge, decision badge, reason text, and a map marker at the locality centroid. Include 10 preset messy examples.
2. **Review Queue:** table sorted by lowest confidence; side-by-side raw vs. parsed; buttons Accept / Correct / Reject. Corrections are stored (feeds an optional retraining export).
3. **Benchmark Dashboard:** resolver comparison table (accuracy, cost, latency), noise-sweep chart, calibration plot, coverage-vs-risk curve with threshold slider.
4. **Failure Explorer:** filter by failure tag, tier, resolver; show real examples with the noise operators applied.
5. **About / Where This Breaks:** plain-language limitations page.

UX rules: always show *why* the system made a decision; never show a bare confidence number without context; colorblind-safe badge colors; mobile is not required.

---

## 11. Repository structure

```
addressiq/
  README.md
  ADDRESSIQ_SPEC.md
  .cursorrules
  pyproject.toml
  docker-compose.yml
  config/            costs.yaml, thresholds.yaml, noise.yaml
  data/              raw/, processed/, splits/   (raw is gitignored; scripts fetch it)
  prompts/           v1.md
  src/addressiq/
    normalize/       normalizer.py, abbreviations.py
    gazetteer/       build.py, index.py, matcher.py
    resolvers/       base.py, rules.py, token_clf.py, llm.py, hybrid.py
    scoring/         features.py, calibrate.py
    policy/          decision.py
    synth/           generator.py, noise_ops.py
    eval/            runner.py, metrics.py, failure_tagger.py
    api/             main.py, schemas.py
    ui/              app.py, pages/
  tests/             unit/, integration/, golden/
  notebooks/         exploration only, never imported
  docs/              model_card.md, data_card.md, limitations.md
```

---

## 12. Engineering rules (also in `.cursorrules`)

- Type hints everywhere; `mypy --strict` on `src/`.
- No network calls in unit tests; use cached fixtures.
- Config in YAML, never hard-coded thresholds.
- Every random operation takes a seed.
- Deterministic normalizer with golden tests (input/output pairs in `tests/golden/`).
- Log resolver name, prompt version, model version with every result.
- Never commit API keys; use `.env` and `.env.example`.
- Every metric in the README must be reproducible with one command (`make benchmark`).

---

## 13. Milestones (6 weeks, each ends with something demoable)

| Week | Deliverable | Done when |
|---|---|---|
| 1 | Gazetteer + normalizer + resolver A | `make demo` resolves addresses; golden tests pass |
| 2 | Synthetic generator + splits + hand-labeled 200 | Tier distribution report; splits leak-free by locality |
| 3 | Resolver B (token classifier) + eval runner | Metrics per tier saved to parquet |
| 4 | Resolver C (LLM, cached) + hybrid | Cost/latency measured; hybrid savings reported |
| 5 | Calibration + decision policy + API | ECE, coverage-risk curve, rule unit tests |
| 6 | Streamlit UI + failure explorer + docs + deploy | Live URL, README with real results, 2-minute demo video |

### Suggested prompts to give Cursor per milestone
- **Week 1:** "Read ADDRESSIQ_SPEC.md sections 5, 6, 7A. Implement the normalizer and gazetteer builder for Hyderabad only, with golden tests. Do not implement other resolvers yet."
- **Week 2:** "Implement the synthetic generator per section 6 with each noise operator as a pure, seeded function and unit tests. Split by locality."
- **Week 3:** "Implement BIO token classification training script and the eval runner per section 9. Log per-tier metrics."
- **Week 4:** "Implement the LLM resolver with disk caching and JSON-schema output. Add cost and latency tracking."
- **Week 5:** "Implement calibration and the decision policy from section 4 with table-driven tests for every rule."
- **Week 6:** "Build the Streamlit pages in section 10 using saved parquet results."

---

## 14. Definition of done

- [ ] `docker compose up` starts API + UI locally
- [ ] `make benchmark` regenerates every number and chart in the README
- [ ] README contains: problem, architecture diagram, results table with CIs, calibration plot, "Where this breaks" with 5 real failure examples, cost/latency table, limitations, data attribution
- [ ] Model card and data card in `docs/`
- [ ] Live demo link and a 2-minute demo video
- [ ] All decision-policy rules unit-tested
- [ ] No claim in any document that is not backed by a saved result

---

## 15. Resume and interview framing (fill in only with real numbers)

> Built AddressIQ, a last-mile address-resolution pipeline over noisy Indian addresses comparing rule-based, fine-tuned token-classifier, and LLM resolvers; achieved **[X]%** locality accuracy on unseen localities, calibrated confidence (ECE **[Y]**), and a review policy that automates **[Z]%** of addresses at **[W]%** wrong-route rate.

Be ready to explain: why calibration matters more than raw accuracy, why the split is by locality, where the LLM was worse or too costly, and what would change with real production data.
