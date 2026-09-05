"""
Admin Console Presenter for SwimAnalyzer AI.
Includes Account/Profile overview, Scientific Database Updater, and Storage Cleanup.
"""
import streamlit as st
from services.auth_service import AuthService
from services.athlete_service import AthleteService
from services.analysis_history_service import AnalysisHistoryService
from services.storage_service import StorageRetentionService

def render_admin_dashboard_page():
    """Renders the Admin Console for site-wide account, storage, and database management."""
    st.title("🏛 Admin Console")
    st.markdown("Admin users can review accounts, manage storage retention, and oversee system records.")

    account_list = AuthService.get_all_accounts()
    coach_count = sum(1 for a in account_list if a.role == "coach")
    user_count = sum(1 for a in account_list if a.role == "user")
    admin_count = sum(1 for a in account_list if a.role == "admin")

    athlete_service = AthleteService()
    all_athletes = []

    history_service = AnalysisHistoryService()
    try:
        all_sessions = history_service.get_all_sessions(st.session_state.current_coach)
    except Exception:
        all_sessions = []

    st.markdown("### 🔐 Account Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Accounts", len(account_list))
    c2.metric("Coaches", coach_count)
    c3.metric("Users", user_count)
    c4.metric("Admins", admin_count)

    st.markdown("---")
    st.markdown("### 🧹 Storage Retention & Disk Management")
    stats = StorageRetentionService.get_storage_stats()
    sc1, sc2 = st.columns(2)
    sc1.metric("Runtime Artifacts Count", f"{stats['total_files']} files")
    sc2.metric("Total Disk Usage", f"{stats['total_mb']} MB")
    
    with st.expander("📁 Directory Storage Breakdown", expanded=False):
        for dirname, dinfo in stats["directories"].items():
            st.write(f"- **{dirname}**: {dinfo['file_count']} files ({dinfo['mb']} MB)")

    cl_col1, cl_col2 = st.columns([2, 1])
    retention_days = cl_col1.slider("Retention Threshold (Days)", min_value=1, max_value=30, value=7)
    if cl_col2.button("🧹 Clean Stale Artifacts", key="btn_clean_storage", type="secondary"):
        clean_res = StorageRetentionService.cleanup_stale_artifacts(max_age_days=retention_days)
        st.success(f"✓ Cleaned {clean_res['deleted_files_count']} files! Reclaimed {clean_res['reclaimed_mb']} MB.")
        st.rerun()

    st.markdown("---")
    st.markdown("### 🔬 Scientific Database Management")
    st.caption("Admin-only action: refresh the verified scientific literature database and benchmark coverage.")
    if st.button("🔄 Update Scientific Database", key="btn_update_sci_db_admin_page"):
        st.session_state["trigger_sci_db_update"] = True

    if "last_sci_db_update_res" in st.session_state:
        res = st.session_state["last_sci_db_update_res"]
        verdict = res.get('verdict', '')
        if res.get('database_changed') is False and verdict == "SUCCESSFUL_UPDATE":
            st.success("✓ **Scientific Database Already Up To Date** — No new literature found.")
        elif verdict == "INTERNET_UNAVAILABLE":
            st.warning(f"⚠️ **Internet Literature Update Could Not Be Completed** — External scientific sources were unavailable. Previous verified database preserved intact. (Version: `{res.get('previous_version', '2026.08.08')}`)")
        elif verdict == "UPDATE_ABORTED":
            st.error(f"❌ **Scientific Database Update Aborted** — Safety validation tests failed. Previous verified database preserved intact. (Version: `{res.get('previous_version', '2026.08.08')}`)")
        else:
            st.success(f"✓ **Scientific Database Update Complete!** (Version: `{res.get('previous_version')}` → `{res.get('new_version')}`)")

        with st.container(border=True):
            st.markdown("### 🔬 Scientific Database Update Summary")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Sources Discovered", res.get("sources_discovered", 0))
            c2.metric("New Sources", res.get("new_sources", 0))
            c3.metric("Full-Text Verified", res.get("full_text_verified", 0))
            c4.metric("Evidence Candidates", res.get("evidence_candidates", 0))

    st.markdown("---")
    st.markdown("### 🧾 Account Management")
    if not account_list:
        st.info("No accounts registered.")
    else:
        for account in account_list:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{account.full_name}** (@{account.username})")
                    st.caption(f"Role: {account.role.title()} | Created: {account.created_at}")
                with col2:
                    if account.role != "admin":
                        if st.button("Delete", key=f"delete_account_{account.coach_id}", type="secondary"):
                            if AuthService.delete_account(account.coach_id):
                                st.success(f"Deleted account {account.username}.")
                                st.rerun()
                            else:
                                st.error("Unable to delete account.")
                    else:
                        st.markdown("*Protected*", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📊 System Activity")
    st.write(f"Total analysis sessions: {len(all_sessions)}")
    if all_sessions:
        account_map = {a.coach_id: f"{a.username} ({a.role.title()})" for a in account_list}
        latest = sorted(all_sessions, key=lambda s: s.analysis_timestamp, reverse=True)[:8]
        for s in latest:
            if s.athlete_id:
                actor = s.athlete_id
            elif s.account_id:
                actor = "Personal Account Upload"
            else:
                actor = "Guest Session"
            account_info = account_map.get(s.account_id, f"Unknown Account ({s.account_id})") if s.account_id else "No Account"
            score_text = f"{s.performance_score:.1f}" if s.performance_score is not None else "N/A"
            st.markdown(
                f"- {s.analysis_timestamp}: {actor} | {s.stroke_type} | Score {score_text} | Uploaded by: {account_info} | Account ID: {s.account_id or 'None'}"
            )
