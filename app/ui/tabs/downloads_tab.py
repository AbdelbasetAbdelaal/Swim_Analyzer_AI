"""
Downloads and Video Player Tab Presenter for SwimAnalyzer AI.
"""
from pathlib import Path
import streamlit as st
from services.pdf_report_service import PDFReportService
from core.logger import setup_logger

logger = setup_logger(__name__)

def safe_log(msg: str):
    try:
        print(f"[TRACE] {msg}", flush=True)
        logger.info(msg)
    except Exception:
        pass

def render_video_section(output_video_path, video_render_mode):
    safe_log("[TRACE] ENTER render_video_section")
    st.markdown("#### Annotated Video")

    if video_render_mode == "Disabled (text only)":
        st.success("Video generated successfully.")
        st.write(output_video_path)

    elif video_render_mode == "Native Streamlit (st.video)":
        safe_log("[TRACE] ENTER render_video_native_mode")
        try:
            with open(output_video_path, 'rb') as f:
                video_bytes = f.read()
            st.video(video_bytes)
        except Exception as e:
            st.error(f"Error serving video: {e}")
        safe_log("[TRACE] EXIT render_video_native_mode")

    elif video_render_mode == "HTML5 Streaming Player":
        safe_log("[TRACE] ENTER render_video_html5_mode")
        try:
            from utils.video_utils import prepare_static_video
            static_url = prepare_static_video(output_video_path, str(Path(__file__).resolve().parent.parent.parent))
            st.markdown(
                f'''
                <video width="100%" controls style="max-height: 480px; border-radius: 8px; background: #000; width: 100%;">
                    <source src="{static_url}" type="video/mp4">
                    Your browser does not support HTML5 video.
                </video>
                ''',
                unsafe_allow_html=True
            )
        except Exception as e:
            st.error(f"Error encoding HTML5 video: {e}")
        safe_log("[TRACE] EXIT render_video_html5_mode")

    safe_log("[TRACE] EXIT render_video_section")

def render_download_buttons(output_video_path, json_report_path, metadata_path, analysis_result=None, profile=None):
    logger.debug("Rendering download buttons tab")
    
    # Detailed Session PDF Report Download (Cached per analysis result to prevent duplicate runs)
    if analysis_result:
        try:
            pdf_cache_key = f"_pdf_report_{id(analysis_result)}"
            if pdf_cache_key not in st.session_state or not Path(st.session_state[pdf_cache_key]).exists():
                pdf_service = PDFReportService()
                current_coach = st.session_state.get("current_coach")
                pdf_path = pdf_service.generate_session_analysis_pdf(analysis_result, profile=profile, coach=current_coach)
                st.session_state[pdf_cache_key] = pdf_path
            else:
                pdf_path = st.session_state[pdf_cache_key]

            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            st.download_button(
                label="📄 Download Detailed PDF Report",
                data=pdf_bytes,
                file_name=Path(pdf_path).name,
                mime="application/pdf",
                type="primary",
                width="stretch"
            )
        except Exception as e:
            logger.warning(f"Failed to generate PDF for download button: {e}")

    stroke_name = str(getattr(analysis_result, 'stroke_type', 'Session')).title() if analysis_result else "Session"
    
    with open(output_video_path, 'rb') as video_file:
        video_bytes = video_file.read()
    st.download_button(
        label="🎥 Download Processed Video (.mp4)",
        data=video_bytes,
        file_name=f"SwimVideo_{stroke_name}.mp4",
        mime="video/mp4",
        width="stretch"
    )
    
    if json_report_path:
        with open(json_report_path, 'r') as json_file:
            json_str = json_file.read()
        st.download_button(
            label="📊 Download Biomechanical Data (.json)",
            data=json_str,
            file_name=f"SwimReport_{stroke_name}.json",
            mime="application/json",
            width="stretch"
        )
        
    if metadata_path:
        with open(metadata_path, 'r') as meta_file:
            meta_str = meta_file.read()
        st.download_button(
            label="ℹ️ Download Session Metadata (.json)",
            data=meta_str,
            file_name=f"SwimMetadata_{stroke_name}.json",
            mime="application/json",
            width="stretch"
        )
