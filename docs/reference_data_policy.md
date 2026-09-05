# Reference Data Scientific Policy

> **Core Policy Statement:**  
> *"The Reference Data Manager is a data management system, not an evidence generator."*

---

## 1. Scientific Data Taxonomy

Swim_Analyzer_AI maintains a strict separation between four distinct tiers of reference data:

### Tier 1: Peer-Reviewed Scientific Evidence (`BENCHMARK`)
- **Sources:** Peer-reviewed systematic reviews, meta-analyses, or primary empirical studies published in indexed biomechanics/sports science journals.
- **Requirements:** Complete citation (authors, title, year, journal, DOI/PMID), known sample size ($N \ge 10$), explicit stroke definition, explicit population demographic boundaries.
- **Usage:** Serves as authoritative benchmark baseline for percentile rankings, Z-scores, and population comparisons.

### Tier 2: Validated Team Reference Data (`VALIDATED_TEAM_DATA`)
- **Sources:** Empirical team measurements collected systematically by coaches using validated timing or video analysis protocols.
- **Requirements:** Explicit demographic cohort definition and internal team audit review.
- **Usage:** Secondary priority for team-specific progression tracking.

### Tier 3: Coach-Defined Reference Data (`COACH_DEFINED`)
- **Sources:** Target metrics or ranges manually entered by coaches for specialized training goals.
- **Default Eligibility:** `CONTEXT_ONLY`.
- **Disclaimer:** *"Coach-defined reference — not a universal scientific benchmark."*
- **Usage:** Contextual guidance for drill targets. Never masquerades as a peer-reviewed scientific population norm.

### Tier 4: Imported Unvalidated Data (`IMPORTED_REFERENCE`)
- **Sources:** External CSV/JSON dataset files imported into the system.
- **Default Status:** `DRAFT` with `CONTEXT_ONLY` eligibility until explicitly validated through the 8 Scientific Integrity Rules.

---

## 2. Mandatory Rules of Evidence Integrity

1. **No Fabricated Fallbacks:** Missing numerical measurements must remain `None` (`null`). No artificial values ($0$, $70$, $100$, $0.5$) may be substituted to force a calculation.
2. **Demographic Isolation:** Youth ($age \le 17$) and Masters ($age \ge 36$) datasets are isolated. They are never merged or averaged with adult general population baselines.
3. **Stroke Separation:** Freestyle, Backstroke, Breaststroke, and Butterfly metrics are strictly isolated.
4. **Transparent Match Scores:** Population match scores are represented explicitly as `REFERENCE_MATCH_SCORE` (0.0 to 100.0) based on demographic compatibility. Internal match metrics are never labeled as "probabilities".
