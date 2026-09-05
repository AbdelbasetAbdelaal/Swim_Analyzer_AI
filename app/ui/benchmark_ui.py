import streamlit as st
from typing import Any, Optional

from models.benchmark_models import BenchmarkResult
from models.scientific_evidence_models import (
    AuditDecision
)
from services.scientific_evidence_service import ScientificEvidenceService

def render_population_benchmark_cards(bm_res: BenchmarkResult, athlete_profile: Optional[Any] = None):
    """
    Renders Population Benchmark Cards with evidence badges, provenance,
    and demographic compatibility guards.
    """
    if not bm_res or not getattr(bm_res, 'comparisons', None):
        st.info("No population benchmark data available for this analysis.")
        return

    # 1. Demographic Compatibility Banner
    ev_service = ScientificEvidenceService()
    athlete_gender = athlete_profile.gender if athlete_profile and athlete_profile.gender else "Male"
    athlete_age = athlete_profile.age if athlete_profile and athlete_profile.age else 20

    is_demographic_compatible = getattr(bm_res, 'is_population_compatible', False)

    # Determine athlete demographic cohort description
    if athlete_age < 18:
        demographic_desc = f"Youth Athlete (Age {athlete_age})"
    elif athlete_age <= 25:
        demographic_desc = f"Adult {athlete_gender} (Age {athlete_age})"
    elif athlete_age <= 35:
        demographic_desc = f"Adult {athlete_gender} (Age {athlete_age}, 26-35)"
    else:
        demographic_desc = f"Masters {athlete_gender} (Age {athlete_age})"

    # Retrieve actual reference cohort name from evidence metadata if present
    ref_cohort_name = "Adult Male (18–25)"
    for m_comp in bm_res.comparisons.values():
        if m_comp.population_mean is not None:
            if m_comp.evidence and getattr(m_comp.evidence, 'population_description', None):
                ref_cohort_name = m_comp.evidence.population_description
                break
            elif is_demographic_compatible:
                ref_cohort_name = demographic_desc

    if not is_demographic_compatible:
        st.warning(
            f"⚠️ **No direct peer-reviewed reference dataset is currently indexed for this specific demographic group** "
            f"({demographic_desc}). "
            f"Athlete measurements are displayed below for context, but percentiles and Z-scores are suppressed to uphold scientific accuracy."
        )
    else:
        st.success(
            f"✓ **Athlete belongs to a scientifically validated reference population cohort** "
            f"({demographic_desc} - {ref_cohort_name})."
        )

    b_c1, b_c2, b_c3 = st.columns(3)
    b_c1.metric("Skill Level Tier", bm_res.overall_skill_level if is_demographic_compatible else "N/A (Unvalidated Cohort)")
    b_c2.metric("Athlete Cohort", demographic_desc)
    b_c3.metric("Reference Cohort", ref_cohort_name if is_demographic_compatible else "Adult Male (18–25) Baseline")

    st.caption(f"**Evidence Registry Dataset:** {bm_res.dataset_name} (ID: `{bm_res.dataset_id}`, v{bm_res.dataset_version}, Revision: {bm_res.scientific_revision})")
    
    if is_demographic_compatible:
        from app.ui.charts import create_benchmark_radar_chart
        radar_fig = create_benchmark_radar_chart(bm_res)
        st.plotly_chart(radar_fig, width="stretch")

    st.markdown("---")

    # 2. Render Cards for each Metric
    for m_name, comp in bm_res.comparisons.items():
        if m_name == "performance_score":
            continue # Handled separately as SwimAnalyzer Composite Score

        ev_meta = getattr(comp, 'evidence', None)
        m_title = m_name.replace("_", " ").title()

        # Evidence status badge text & icon
        ev_id = getattr(ev_meta, 'evidence_id', 'NONE') if ev_meta else 'NONE'
        ev_record = ev_service.get_evidence_record(ev_id) if ev_id != 'NONE' else None

        badge_text = "⚠ INSUFFICIENT EVIDENCE"
        badge_style = "background-color:#FF9800; color:white;"

        if ev_record:
            if ev_record.audit_decision in [AuditDecision.ACCEPT, AuditDecision.ACCEPT_AS_DERIVED]:
                badge_text = "✓ SCIENTIFICALLY ACCEPTED"
                badge_style = "background-color:#4CAF50; color:white;"
            elif ev_record.audit_decision == AuditDecision.REFERENCE_ONLY:
                badge_text = "⚠ REFERENCE ONLY"
                badge_style = "background-color:#FFC107; color:black;"
            elif ev_record.audit_decision == AuditDecision.REJECT:
                badge_text = "✕ REJECTED"
                badge_style = "background-color:#F44336; color:white;"

        relationship_label = ev_record.relationship_to_benchmark.value if ev_record else "UNVERIFIED"
        relationship_fmt = relationship_label.replace("_", " ").title()

        with st.container(border=True):
            col_head, col_badge = st.columns([3, 2])
            with col_head:
                st.markdown(f"#### {m_title}")
            with col_badge:
                st.markdown(
                    f"""<div style="text-align:right;">
                    <span style="display:inline-block; padding:4px 12px; border-radius:12px; font-weight:bold; font-size:0.85rem; {badge_style}">
                    {badge_text}
                    </span></div>""",
                    unsafe_allow_html=True
                )

            # Metric Values
            c_val1, c_val2, c_val3, c_val4 = st.columns(4)
            raw_value = getattr(comp, 'raw_value', None)
            raw_display = f"{raw_value} {comp.unit}".strip() if raw_value is not None else "UNAVAILABLE"
            c_val1.metric("Athlete Measurement", raw_display)
            
            ref_val = f"{comp.population_mean:.1f} {comp.unit}".strip() if comp.population_mean is not None else "N/A"
            c_val2.metric("Scientific Reference", ref_val)
            
            c_val3.metric("Reference Population", "Adult Competitive Males (18–25)")
            
            z_display = f"{comp.z_score:+.2f}" if comp.z_score is not None else "N/A"
            pct_display = f"{comp.percentile:.1f}%" if comp.percentile is not None else "N/A"
            c_val4.metric("Percentile Rank", pct_display, delta=f"Z: {z_display}" if z_display != "N/A" else None)

            # Source Line
            if ev_record:
                authors_str = ", ".join(ev_record.authors[:2]) if ev_record.authors else "Unknown"
                if len(ev_record.authors) > 2:
                    authors_str += " et al."
                citation_line = f"**Source:** {authors_str} ({ev_record.year}) — *{ev_record.publication}* | **Relationship:** {relationship_fmt}"
            else:
                citation_line = "**Source:** Not available in verified primary source | **Relationship:** Unverified"

            st.markdown(citation_line)

            # Expandable Scientific Evidence Drawer
            with st.expander("🔬 Scientific Evidence & Provenance Details", expanded=False):
                if ev_record:
                    st.markdown(f"**Publication Title:** {ev_record.title or 'Not available in verified source.'}")
                    st.markdown(f"**Authors:** {', '.join(ev_record.authors) if ev_record.authors else 'Not available in verified source.'}")
                    st.markdown(f"**Journal & Year:** {ev_record.publication} ({ev_record.year})")
                    st.markdown(f"**DOI:** {ev_record.doi if ev_record.doi else 'Not available in verified source.'}")
                    st.markdown(f"**Source Type:** {ev_record.source_quality.value if hasattr(ev_record, 'source_quality') else 'PEER_REVIEWED_FULL_TEXT'}")
                    st.markdown(f"**Sample Size:** N = {ev_record.sample_size if ev_record.sample_size else 'Not available in verified source.'}")
                    st.markdown(f"**Exact Source Location:** {ev_record.table_or_figure_reference}, {ev_record.page_reference}")
                    st.markdown(f"**Original Measurement:** {ev_record.reported_mean} ± {ev_record.reported_std} {ev_record.measurement_units}")
                    if ev_record.conversion_formula:
                        st.markdown(f"**Conversion Formula:** `{ev_record.conversion_formula}`")
                        st.markdown(f"**Converted Derived Value:** {ev_record.converted_value} {ev_record.converted_unit}")
                    st.markdown(f"**Definition Match:** `{ev_record.definition_compatibility.value}`")
                    st.markdown(f"**Population Match:** `{ev_record.population_compatibility.value}`")
                    st.markdown(f"**Audit Decision:** `{ev_record.audit_decision.value}`")
                    if ev_record.notes:
                        st.info(f"**Scientific Audit Notes:** {ev_record.notes}")
                else:
                    st.caption("No primary peer-reviewed evidence record is attached to this parameter.")

    # 3. Proprietary Performance Score Callout
    st.markdown("---")
    with st.container(border=True):
        st.markdown("#### 🏆 SwimAnalyzer Composite Score")
        ps_comp = bm_res.comparisons.get('performance_score') if bm_res and bm_res.comparisons else None
        ps_val = ps_comp.raw_value if (ps_comp and ps_comp.raw_value is not None) else None
        st.metric("Composite Technique Index", f"{ps_val:.1f} / 100" if ps_val is not None else "INSUFFICIENT_EVIDENCE")
