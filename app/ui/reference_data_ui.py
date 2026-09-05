"""
Streamlit UI Component: Reference Data Manager.
Renders Dataset Directory, Dataset Creator/Editor, Metric Editor, CSV Import/Export Center,
Audit History Viewer, and Benchmark Priority Engine Simulator.
"""

import streamlit as st
import pandas as pd
from models.reference_data_models import (
    ReferenceDataset, ReferenceMetric, ReferenceSource,
    ReferenceSourceType, ReferenceBenchmarkEligibility,
    ReferenceValidationStatus, ReferenceMeasurementDomain
)
from services.reference_data_service import ReferenceDataService
from services.reference_csv_service import ReferenceCSVService
from services.reference_export_service import ReferenceExportService

def render_reference_data_manager_page():
    st.title("📚 Reference Data Manager")
    st.markdown(
        "Manage, curate, validate, import, export, and inspect swimming reference datasets across all four strokes. "
        "Coexists seamlessly with the scientifically authoritative peer-reviewed YAML benchmark registry."
    )

    # Disclaimer Callout
    st.info(
        "ℹ️ **Scientific Policy Notice:** The Reference Data Manager is a reference data management system. "
        "Coach-entered or unvalidated imported datasets default to `CONTEXT_ONLY` and cannot automatically become universal scientific benchmarks."
    )

    current_coach = st.session_state.get("current_coach")
    is_admin = bool(current_coach and getattr(current_coach, "role", None) == "admin")
    if not is_admin:
        st.warning("🔒 **Read-Only Access:** Administrator privileges are required to create, edit, archive, or delete reference datasets. You may inspect and export existing records.")

    service = ReferenceDataService(principal=current_coach)

    tab_list, tab_create, tab_import, tab_export, tab_simulator = st.tabs([
        "📋 Dataset Directory",
        "➕ Create / Edit Dataset",
        "📥 CSV Import Center",
        "📤 Export Center",
        "🧪 Priority Resolver Inspector"
    ])

    # ---------------------------------------------------------
    # TAB 1: DATASET DIRECTORY
    # ---------------------------------------------------------
    with tab_list:
        st.subheader("📋 Reference Datasets")
        datasets = service.get_all_datasets(include_archived=True)

        # Filters
        c_f1, c_f2, c_f3 = st.columns(3)
        with c_f1:
            filter_stroke = st.selectbox("Filter by Stroke", ["All", "FREESTYLE", "BACKSTROKE", "BREASTSTROKE", "BUTTERFLY"])
        with c_f2:
            filter_status = st.selectbox("Filter by Status", ["All", "DRAFT", "PENDING_REVIEW", "COACH_VALIDATED", "SCIENTIFICALLY_VALIDATED", "REJECTED"])
        with c_f3:
            show_archived = st.checkbox("Show Archived Datasets", value=False)

        # Apply Filters
        filtered_ds = datasets
        if not show_archived:
            filtered_ds = [d for d in filtered_ds if not d.is_archived]
        if filter_stroke != "All":
            filtered_ds = [d for d in filtered_ds if d.stroke == filter_stroke or d.stroke == "ALL"]
        if filter_status != "All":
            filtered_ds = [d for d in filtered_ds if d.validation_status == filter_status]

        if not filtered_ds:
            st.warning("No reference datasets found matching the selected filters.")
        else:
            for ds in filtered_ds:
                # Status badge color
                val_bg = "#4CAF50" if ds.validation_status == "SCIENTIFICALLY_VALIDATED" else (
                    "#2196F3" if ds.validation_status == "COACH_VALIDATED" else (
                        "#FFC107" if ds.validation_status == "PENDING_REVIEW" else (
                            "#F44336" if ds.validation_status == "REJECTED" else "#9E9E9E"
                        )
                    )
                )

                elig_bg = "#8E24AA" if ds.benchmark_eligibility == "BENCHMARK" else (
                    "#009688" if ds.benchmark_eligibility == "CONTEXT_ONLY" else "#607D8B"
                )

                with st.container(border=True):
                    head_col, badge_col = st.columns([3, 2])
                    with head_col:
                        arch_tag = " [ARCHIVED]" if ds.is_archived else ""
                        st.markdown(f"### 🏊 {ds.name}{arch_tag}")
                        st.caption(f"**Stroke:** {ds.stroke} | **Age Range:** [{ds.age_min}–{ds.age_max}] | **Sex:** {ds.sex} | **Skill:** {ds.skill_level} | **Category:** {ds.athlete_category}")
                    with badge_col:
                        st.markdown(
                            f"""<div style="text-align:right;">
                            <span style="display:inline-block; padding:4px 10px; border-radius:12px; font-weight:bold; font-size:0.8rem; color:white; background-color:{val_bg};">
                            {ds.validation_status}
                            </span>
                            <span style="display:inline-block; padding:4px 10px; border-radius:12px; font-weight:bold; font-size:0.8rem; color:white; background-color:{elig_bg}; margin-left:4px;">
                            {ds.benchmark_eligibility}
                            </span>
                            </div>""",
                            unsafe_allow_html=True
                        )

                    if ds.source_type in ["COACH_DEFINED", "VALIDATED_TEAM_DATA"]:
                        st.caption("⚠️ *Coach-defined reference — not a universal scientific benchmark.*")

                    st.markdown(f"**Description:** {ds.description or 'N/A'}")
                    st.markdown(f"**Source Type:** `{ds.source_type}` | **Metrics Count:** `{len(ds.metrics)}` | **Last Updated:** {ds.updated_at[:10] if ds.updated_at else 'N/A'}")

                    # Expanders for Metrics, Sources, Audit
                    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
                    with col_b1:
                        if st.button("✏️ Edit Dataset", key=f"btn_edit_{ds.dataset_id}"):
                            st.session_state["editing_dataset_id"] = ds.dataset_id
                            st.rerun()

                    with col_b2:
                        if ds.is_archived:
                            if st.button("🔄 Unarchive", key=f"btn_unarch_{ds.dataset_id}"):
                                service.archive_dataset(ds.dataset_id, is_archived=False)
                                st.success("Dataset unarchived.")
                                st.rerun()
                        else:
                            if st.button("📦 Archive", key=f"btn_arch_{ds.dataset_id}"):
                                service.archive_dataset(ds.dataset_id, is_archived=True)
                                st.success("Dataset archived.")
                                st.rerun()

                    with col_b3:
                        if st.button("📋 Duplicate", key=f"btn_dup_{ds.dataset_id}"):
                            dup_ds = ReferenceDataset(
                                name=f"{ds.name} (Copy)",
                                description=ds.description,
                                stroke=ds.stroke,
                                age_min=ds.age_min,
                                age_max=ds.age_max,
                                sex=ds.sex,
                                skill_level=ds.skill_level,
                                athlete_category=ds.athlete_category,
                                source_type=ds.source_type,
                                metrics=ds.metrics,
                                sources=ds.sources
                            )
                            service.save_dataset(dup_ds)
                            st.success(f"Duplicated dataset '{ds.name}'.")
                            st.rerun()

                    with col_b4:
                        confirm_del = st.checkbox("Confirm Delete", key=f"chk_del_{ds.dataset_id}")
                        if st.button("🗑 Delete", key=f"btn_del_{ds.dataset_id}", disabled=not confirm_del):
                            service.delete_dataset(ds.dataset_id)
                            st.success(f"Deleted dataset '{ds.name}'.")
                            st.rerun()

                    # Details Expander
                    with st.expander("📊 View Metrics & Scientific Provenance", expanded=False):
                        if not ds.metrics:
                            st.caption("No metrics currently recorded for this dataset.")
                        else:
                            st.markdown("#### Metric Definitions")
                            m_rows = []
                            for m in ds.metrics:
                                m_rows.append({
                                    "Metric": m.display_name or m.metric_name,
                                    "Min": m.value_min if m.value_min is not None else "None",
                                    "Typical": m.value_typical if m.value_typical is not None else "None",
                                    "Median": m.value_median if m.value_median is not None else "None",
                                    "Max": m.value_max if m.value_max is not None else "None",
                                    "Unit": m.unit,
                                    "Domain": m.measurement_domain,
                                    "Status": m.status
                                })
                            st.dataframe(pd.DataFrame(m_rows), width="stretch")

                        if ds.sources:
                            st.markdown("#### Scientific Provenance Citations")
                            for src in ds.sources:
                                st.markdown(f"- **{src.source_title or 'Untitled Source'}** ({src.publication_year or 'N/A'})")
                                st.caption(f"Authors: {src.authors or 'N/A'} | DOI: {src.doi or 'N/A'} | PMID: {src.pmid or 'N/A'} | Sample Size: N={src.sample_size or 'N/A'}")

                        if ds.validation_events:
                            st.markdown("#### Audit History Log")
                            ev_rows = []
                            for ev in ds.validation_events:
                                ev_rows.append({
                                    "Timestamp": ev.timestamp[:19] if ev.timestamp else "",
                                    "Action": ev.action,
                                    "User": ev.user,
                                    "Old Status": ev.old_status,
                                    "New Status": ev.new_status,
                                    "Notes": ev.notes
                                })
                            st.dataframe(pd.DataFrame(ev_rows), width="stretch")

    # ---------------------------------------------------------
    # TAB 2: CREATE / EDIT DATASET FORM
    # ---------------------------------------------------------
    with tab_create:
        editing_id = st.session_state.get("editing_dataset_id")
        target_ds = service.get_dataset(editing_id) if editing_id else None

        if target_ds:
            st.subheader(f"✏️ Edit Dataset: {target_ds.name}")
            if st.button("⬅️ Cancel Edit (Create New Dataset Instead)"):
                st.session_state["editing_dataset_id"] = None
                st.rerun()
        else:
            st.subheader("➕ Create New Reference Dataset")

        with st.form("form_reference_dataset"):
            f_name = st.text_input("Dataset Name *", value=target_ds.name if target_ds else "")
            f_desc = st.text_area("Description", value=target_ds.description if target_ds else "")

            c1, c2 = st.columns(2)
            with c1:
                f_stroke = st.selectbox("Stroke *", ["FREESTYLE", "BACKSTROKE", "BREASTSTROKE", "BUTTERFLY", "ALL"], index=0 if not target_ds else ["FREESTYLE", "BACKSTROKE", "BREASTSTROKE", "BUTTERFLY", "ALL"].index(target_ds.stroke if target_ds.stroke in ["FREESTYLE", "BACKSTROKE", "BREASTSTROKE", "BUTTERFLY", "ALL"] else "FREESTYLE"))
                f_age_min = st.number_input("Age Min *", min_value=0, max_value=120, value=target_ds.age_min if target_ds else 18)
                f_age_max = st.number_input("Age Max *", min_value=0, max_value=120, value=target_ds.age_max if target_ds else 25)
            with c2:
                f_sex = st.selectbox("Sex *", ["Male", "Female", "Mixed", "Unknown"], index=2 if not target_ds else ["Male", "Female", "Mixed", "Unknown"].index(target_ds.sex if target_ds.sex in ["Male", "Female", "Mixed", "Unknown"] else "Mixed"))
                f_skill = st.selectbox("Skill Level *", ["Beginner", "Intermediate", "Advanced", "Elite", "Unknown"], index=1 if not target_ds else ["Beginner", "Intermediate", "Advanced", "Elite", "Unknown"].index(target_ds.skill_level if target_ds.skill_level in ["Beginner", "Intermediate", "Advanced", "Elite", "Unknown"] else "Intermediate"))
                f_cat = st.selectbox("Athlete Category *", ["Youth", "Adult", "Masters", "Sprinter", "Distance", "IM", "Custom"], index=1 if not target_ds else ["Youth", "Adult", "Masters", "Sprinter", "Distance", "IM", "Custom"].index(target_ds.athlete_category if target_ds.athlete_category in ["Youth", "Adult", "Masters", "Sprinter", "Distance", "IM", "Custom"] else "Adult"))

            st.markdown("#### Scientific Provenance & Metadata")
            c3, c4 = st.columns(2)
            with c3:
                f_src_type = st.selectbox("Source Type *", [e.value for e in ReferenceSourceType], index=4 if not target_ds else [e.value for e in ReferenceSourceType].index(target_ds.source_type if target_ds.source_type in [e.value for e in ReferenceSourceType] else "COACH_DEFINED"))
                f_src_title = st.text_input("Source Title / Publication", value=target_ds.sources[0].source_title if (target_ds and target_ds.sources) else "")
                f_authors = st.text_input("Authors", value=target_ds.sources[0].authors if (target_ds and target_ds.sources) else "")
            with c4:
                f_pub_yr = st.number_input("Publication Year", min_value=1900, max_value=2100, value=target_ds.sources[0].publication_year if (target_ds and target_ds.sources and target_ds.sources[0].publication_year) else 2026)
                f_doi = st.text_input("DOI", value=target_ds.sources[0].doi if (target_ds and target_ds.sources) else "")
                f_sample = st.number_input("Sample Size N", min_value=0, value=target_ds.sources[0].sample_size if (target_ds and target_ds.sources and target_ds.sources[0].sample_size) else 0)

            st.markdown("#### Classification & Status")
            c5, c6 = st.columns(2)
            with c5:
                f_elig = st.selectbox("Benchmark Eligibility", [e.value for e in ReferenceBenchmarkEligibility], index=1 if not target_ds else [e.value for e in ReferenceBenchmarkEligibility].index(target_ds.benchmark_eligibility if target_ds.benchmark_eligibility in [e.value for e in ReferenceBenchmarkEligibility] else "CONTEXT_ONLY"))
            with c6:
                f_status = st.selectbox("Validation Status", [e.value for e in ReferenceValidationStatus], index=0 if not target_ds else [e.value for e in ReferenceValidationStatus].index(target_ds.validation_status if target_ds.validation_status in [e.value for e in ReferenceValidationStatus] else "DRAFT"))

            btn_submit = st.form_submit_button("💾 Save Dataset & Add Metrics", type="primary")

            if btn_submit:
                if not f_name.strip():
                    st.error("Dataset name is required.")
                else:
                    new_ds = ReferenceDataset(
                        dataset_id=target_ds.dataset_id if target_ds else "",
                        name=f_name.strip(),
                        description=f_desc.strip(),
                        stroke=f_stroke,
                        age_min=f_age_min,
                        age_max=f_age_max,
                        sex=f_sex,
                        skill_level=f_skill,
                        athlete_category=f_cat,
                        source_type=f_src_type,
                        benchmark_eligibility=f_elig,
                        validation_status=f_status,
                        metrics=target_ds.metrics if target_ds else [],
                        sources=[
                            ReferenceSource(
                                source_type=f_src_type,
                                source_title=f_src_title.strip(),
                                authors=f_authors.strip(),
                                publication_year=f_pub_yr if f_pub_yr > 0 else None,
                                doi=f_doi.strip(),
                                sample_size=f_sample if f_sample > 0 else None
                            )
                        ]
                    )

                    # Check duplicates
                    dups = service.check_duplicates(new_ds)
                    if dups and not target_ds:
                        st.warning(f"⚠️ **Possible duplicate detected!** {len(dups)} existing dataset(s) match these demographic parameters.")

                    success, val_res = service.save_dataset(new_ds)
                    if success:
                        st.success(f"Successfully saved dataset '{f_name}'!")
                        if val_res.disclaimers:
                            for d in val_res.disclaimers:
                                st.info(f"ℹ️ {d}")
                        st.session_state["editing_dataset_id"] = new_ds.dataset_id
                        st.rerun()
                    else:
                        st.error(f"Validation Error: {'; '.join(val_res.errors)}")

        # METRIC EDITOR FOR SELECTED DATASET
        if target_ds:
            st.markdown("---")
            st.subheader(f"🧬 Metric Definitions Editor ({target_ds.name})")

            with st.expander("➕ Add / Edit Metric", expanded=True):
                with st.form("form_add_metric"):
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        common_metrics = [
                            "Custom", "stroke_rate", "stroke_length", "dps", "cycle_time",
                            "velocity", "stroke_index", "body_roll", "elbow_angle",
                            "knee_angle", "hip_angle", "start_time", "turn_time", "underwater_time"
                        ]
                        sel_preset = st.selectbox("Preset Metric", common_metrics)
                        m_name_in = st.text_input("Metric Name *", value=sel_preset if sel_preset != "Custom" else "")
                        m_unit_in = st.text_input("Unit", value="spm" if sel_preset == "stroke_rate" else ("m" if sel_preset in ["stroke_length", "dps"] else "deg"))

                    with col_m2:
                        m_domain_in = st.selectbox("Measurement Domain *", [e.value for e in ReferenceMeasurementDomain], index=0)
                        m_status_in = st.selectbox("Status", ["available", "unavailable"], index=0)

                    st.markdown("##### Reference Ranges (Leave blank if unavailable — Nulls are preserved)")
                    rc1, rc2, rc3, rc4 = st.columns(4)
                    with rc1:
                        in_min = st.text_input("Min Value", value="")
                    with rc2:
                        in_typ = st.text_input("Typical Value", value="")
                    with rc3:
                        in_med = st.text_input("Median Value", value="")
                    with rc4:
                        in_max = st.text_input("Max Value", value="")

                    m_submit = st.form_submit_button("Add / Update Metric")

                    if m_submit:
                        if not m_name_in.strip():
                            st.error("Metric name is required.")
                        else:
                            def to_float(val):
                                if not val or val.strip() == "":
                                    return None
                                try:
                                    return float(val.strip())
                                except ValueError:
                                    return None

                            v_min_f = to_float(in_min)
                            v_typ_f = to_float(in_typ)
                            v_med_f = to_float(in_med)
                            v_max_f = to_float(in_max)

                            new_m = ReferenceMetric(
                                metric_name=m_name_in.strip(),
                                display_name=m_name_in.strip().replace("_", " ").title(),
                                value_min=v_min_f,
                                value_typical=v_typ_f,
                                value_median=v_med_f,
                                value_max=v_max_f,
                                unit=m_unit_in.strip(),
                                measurement_domain=m_domain_in,
                                status=m_status_in
                            )

                            # Update metrics list
                            target_ds.metrics = [m for m in target_ds.metrics if m.metric_name != new_m.metric_name]
                            target_ds.metrics.append(new_m)

                            success, val_res = service.save_dataset(target_ds)
                            if success:
                                st.success(f"Added metric '{m_name_in}' to dataset '{target_ds.name}'.")
                                st.rerun()
                            else:
                                st.error(f"Metric Validation Error: {'; '.join(val_res.errors)}")

    # ---------------------------------------------------------
    # TAB 3: CSV IMPORT CENTER
    # ---------------------------------------------------------
    with tab_import:
        st.subheader("📥 CSV Import & Validation Center")
        st.markdown("Upload CSV reference files to import multiple datasets and metrics simultaneously. All rows undergo rigorous scientific validation previews.")

        col_dl, col_up = st.columns([1, 2])
        with col_dl:
            template_csv = ReferenceCSVService.generate_sample_csv_template()
            st.download_button(
                label="📄 Download CSV Template",
                data=template_csv,
                file_name="reference_data_template.csv",
                mime="text/csv",
                type="primary",
                width="stretch"
            )

        with col_up:
            uploaded_file = st.file_uploader("Upload Reference CSV File", type=["csv"])
            strict_mode = st.toggle("🛡️ Strict Scientific Mode", value=True, help="Enforces strict scientific validation: Coach data defaults to CONTEXT_ONLY, invalid rows are not auto-fixed, no fabricated values.")

        if uploaded_file:
            try:
                csv_text = uploaded_file.getvalue().decode("utf-8-sig")
            except UnicodeDecodeError:
                csv_text = uploaded_file.getvalue().decode("latin1", errors="ignore")

            preview = ReferenceCSVService.parse_and_validate_csv(csv_text, strict_scientific_mode=strict_mode)

            st.markdown("### 🔍 Validation Preview Summary")
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Total Rows", preview.total_rows)
            k2.metric("Valid Rows", preview.valid_rows)
            k3.metric("Invalid Rows", preview.invalid_rows)
            k4.metric("Warnings", preview.warnings_count)
            k5.metric("Duplicates", preview.duplicate_rows)

            # Categorized Error & Warning Summary Expander
            with st.expander("⚠️ View Categorized Validation Summary", expanded=False):
                if preview.schema_errors:
                    st.error(f"**Schema Errors ({len(preview.schema_errors)}):**\n" + "\n".join([f"- {e}" for e in preview.schema_errors[:5]]))
                if preview.metadata_errors:
                    st.error(f"**Metadata Errors ({len(preview.metadata_errors)}):**\n" + "\n".join([f"- {e}" for e in preview.metadata_errors[:5]]))
                if preview.metric_errors:
                    st.error(f"**Metric Range Errors ({len(preview.metric_errors)}):**\n" + "\n".join([f"- {e}" for e in preview.metric_errors[:5]]))
                if preview.duplicate_errors:
                    st.warning(f"**Duplicate Metric Errors ({len(preview.duplicate_errors)}):**\n" + "\n".join([f"- {e}" for e in preview.duplicate_errors[:5]]))
                if preview.provenance_warnings:
                    st.info(f"**Provenance Warnings ({len(preview.provenance_warnings)}):**\n" + "\n".join([f"- {w}" for w in preview.provenance_warnings[:5]]))
                if preview.eligibility_warnings:
                    st.info(f"**Eligibility Policy Warnings ({len(preview.eligibility_warnings)}):**\n" + "\n".join([f"- {w}" for w in preview.eligibility_warnings[:5]]))
                if not (preview.schema_errors or preview.metadata_errors or preview.metric_errors):
                    st.success("✅ No critical schema or dataset validation errors detected.")

            st.markdown("#### Row Validation Details")
            row_data = []
            for r in preview.row_results:
                if not r.is_valid:
                    status_icon = "❌ INVALID"
                elif r.norm_row.record_type == "SOURCE":
                    status_icon = "✅ VALID (SOURCE)"
                else:
                    status_icon = "✅ VALID (METRIC)"

                row_data.append({
                    "Row": r.row_index,
                    "Type": r.norm_row.record_type,
                    "Dataset": r.dataset_name,
                    "Stroke": r.stroke,
                    "Metric": r.metric_name if r.norm_row.record_type == "METRIC" else "(Source Provenance)",
                    "Status": status_icon,
                    "Eligibility": r.benchmark_eligibility,
                    "Errors": "; ".join(r.errors) if r.errors else "None",
                    "Warnings": "; ".join(r.warnings) if r.warnings else "None"
                })
            st.dataframe(pd.DataFrame(row_data), width="stretch")

            # Preview Import Transformation Section
            with st.expander("🔄 Preview Import Transformation Stages", expanded=False):
                st.caption("Inspect stage-by-stage transformation: RAW CSV ROW → RECORD TYPE DETECTION → NORMALIZED RECORD → VALIDATION RESULT → BENCHMARK ELIGIBILITY")
                for r in preview.row_results[:6]:
                    st.markdown(f"**Row {r.row_index}: `{r.dataset_name}` (`{r.norm_row.record_type}`)**")
                    st.json({
                        "RAW CSV ROW": r.raw_csv_row,
                        "RECORD TYPE DETECTION": r.norm_row.record_type,
                        "NORMALIZED RECORD": r.normalized_dataset if r.norm_row.record_type == "SOURCE" else {**r.normalized_dataset, **r.normalized_metric},
                        "VALIDATION RESULT": r.validation_result,
                        "BENCHMARK ELIGIBILITY": r.benchmark_eligibility
                    })

            # Action Buttons: Import & Download Normalized CSV
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                if preview.valid_rows > 0:
                    if st.button(f"📥 Import {preview.valid_rows} Validated Rows", type="primary", width="stretch"):
                        datasets_to_import = ReferenceCSVService.convert_csv_to_datasets(preview)
                        count_imported = 0
                        for ds in datasets_to_import:
                            success, _ = service.save_dataset(ds)
                            if success:
                                count_imported += 1
                        st.success(f"Successfully imported {count_imported} dataset(s) into database!")
                        st.rerun()
                else:
                    st.error("No valid rows detected. Fix CSV errors before importing.")

            with col_act2:
                norm_csv_data = ReferenceCSVService.generate_normalized_csv(preview)
                st.download_button(
                    label="📄 Download Normalized CSV",
                    data=norm_csv_data,
                    file_name="normalized_reference_dataset.csv",
                    mime="text/csv",
                    width="stretch"
                )

            # Version Activation Management Sub-Section
            st.markdown("---")
            st.subheader("⚙️ Dataset Version Management")
            get_ver_fn = getattr(service, "get_dataset_versions", None)
            versions = get_ver_fn() if callable(get_ver_fn) else ReferenceDataService().get_dataset_versions()
            if versions:
                v_rows = []
                for v in versions:
                    v_rows.append({
                        "Version Label": v.version_name,
                        "Filename": v.filename,
                        "Imported At": v.imported_at[:19] if v.imported_at else "",
                        "Records": v.record_count,
                        "Valid": v.valid_count,
                        "Active State": "ACTIVE ✅" if v.is_active else "INACTIVE ❌",
                        "Importer": v.importer
                    })
                st.dataframe(pd.DataFrame(v_rows), width="stretch")

                col_v1, col_v2 = st.columns(2)
                with col_v1:
                    sel_ver = st.selectbox("Select Version to Toggle", [v.version_name for v in versions])
                with col_v2:
                    st.write("")
                    st.write("")
                    curr_v = next((v for v in versions if v.version_name == sel_ver), None)
                    if curr_v:
                        if curr_v.is_active:
                            if st.button(f"🔴 Deactivate Version '{sel_ver}'"):
                                service.deactivate_dataset_version(sel_ver)
                                st.success(f"Version '{sel_ver}' deactivated.")
                                st.rerun()
                        else:
                            if st.button(f"🟢 Activate Version '{sel_ver}'"):
                                service.activate_dataset_version(sel_ver)
                                st.success(f"Version '{sel_ver}' activated.")
                                st.rerun()

    # ---------------------------------------------------------
    # TAB 4: EXPORT CENTER
    # ---------------------------------------------------------
    with tab_export:
        st.subheader("📤 Reference Data Export Center")
        st.markdown("Export reference datasets to CSV, JSON, or YAML formats while preserving scientific provenance and validation status.")

        datasets = service.get_all_datasets(include_archived=True)
        if not datasets:
            st.info("No datasets available to export.")
        else:
            st.write(f"Total Datasets Available: **{len(datasets)}**")

            exp_csv = ReferenceExportService.export_to_csv(datasets)
            exp_json = ReferenceExportService.export_to_json(datasets)
            exp_yaml = ReferenceExportService.export_to_yaml(datasets)

            e1, e2, e3 = st.columns(3)
            with e1:
                st.download_button(
                    label="📥 Download CSV Export",
                    data=exp_csv,
                    file_name="swim_reference_datasets.csv",
                    mime="text/csv",
                    type="primary",
                    width="stretch"
                )
            with e2:
                st.download_button(
                    label="📥 Download JSON Export",
                    data=exp_json,
                    file_name="swim_reference_datasets.json",
                    mime="application/json",
                    width="stretch"
                )
            with e3:
                st.download_button(
                    label="📥 Download YAML Export",
                    data=exp_yaml,
                    file_name="swim_reference_datasets.yaml",
                    mime="text/yaml",
                    width="stretch"
                )

    # ---------------------------------------------------------
    # TAB 5: PRIORITY RESOLVER SIMULATOR
    # ---------------------------------------------------------
    with tab_simulator:
        st.subheader("🧪 Benchmark Priority Resolver Simulator")
        st.markdown("Test how the Priority Engine resolves dataset matches for specific athlete profiles.")

        s_col1, s_col2 = st.columns(2)
        with s_col1:
            sim_stroke = st.selectbox("Athlete Stroke", ["FREESTYLE", "BACKSTROKE", "BREASTSTROKE", "BUTTERFLY"])
            sim_age = st.number_input("Athlete Age", min_value=5, max_value=100, value=20)
        with s_col2:
            sim_sex = st.selectbox("Athlete Sex", ["Male", "Female", "Mixed"])
            sim_metric = st.selectbox("Target Metric", ["stroke_rate", "stroke_length", "dps", "cycle_time", "body_roll"])

        if st.button("🔍 Resolve Reference Priority", type="primary"):
            match = service.resolve_reference(
                metric_name=sim_metric,
                stroke=sim_stroke,
                age=sim_age,
                sex=sim_sex
            )

            st.markdown("### Match Resolution Report")
            m1, m2, m3 = st.columns(3)
            m1.metric("Selected Dataset", match.selected_dataset_name)
            m2.metric("REFERENCE_MATCH_SCORE", f"{match.compatibility_score:.1f}/100")
            m3.metric("Scientific Confidence", match.scientific_confidence)

            st.info(f"**Selection Reason:** {match.selection_reason}")
            if match.disclaimers:
                for d in match.disclaimers:
                    st.warning(f"⚠️ {d}")

            if match.reference_metric:
                st.markdown("#### Resolved Metric Reference")
                st.json({
                    "metric_name": match.reference_metric.metric_name,
                    "min": match.reference_metric.value_min,
                    "typical": match.reference_metric.value_typical,
                    "median": match.reference_metric.value_median,
                    "max": match.reference_metric.value_max,
                    "unit": match.reference_metric.unit,
                    "domain": match.reference_metric.measurement_domain
                })
