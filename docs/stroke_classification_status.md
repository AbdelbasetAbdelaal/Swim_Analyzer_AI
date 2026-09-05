# Swimming Stroke Selection Architectural Status

## Current Status: Mandatory User Stroke Selection

Automated swimming stroke classification has been permanently removed from the active product analysis path.

### Key Architectural Contracts:
1. **User Mandatory Selection**: The user MUST explicitly choose the stroke type (**Freestyle**, **Backstroke**, **Breaststroke**, **Butterfly**) before launching analysis.
2. **Single Source of Truth**: The value `selected_stroke` is the sole source of truth across all application layers.
3. **No Automatic Overrides**: The system does not attempt to infer, classify, or override the user's selection.
4. **Analysis Reliability**: The metric "Confidence" measures video tracking quality and landmark completeness, NOT stroke classification probability.
5. **Direct Strategy Dispatch**: `AnalysisService` dispatches directly to the matching strategy (`FreestyleStrategy`, `BackstrokeStrategy`, `BreaststrokeStrategy`, `ButterflyStrategy`) based on `selected_stroke`.
