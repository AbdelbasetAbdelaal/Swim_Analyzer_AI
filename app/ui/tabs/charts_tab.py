"""
Charts and Kinematic Timeseries Tab Presenter for SwimAnalyzer AI.
"""
import streamlit as st
import numpy as np
import pandas as pd
from core.logger import setup_logger

logger = setup_logger(__name__)

def safe_log(msg: str):
    logger.debug(msg)

def render_raw_data_tab(analysis_result):
    safe_log("[TRACE] ENTER render_raw_data_tab")
    
    ts_data = {
        "timestamp_ms": [],
        "left_elbow": [], "right_elbow": [],
        "left_knee": [], "right_knee": [],
        "left_shoulder": [], "right_shoulder": [],
        "body_roll": [], "valid": []
    }
    
    for f in analysis_result.frames:
        ts_data["timestamp_ms"].append(f.timestamp_ms)
        ts_data["left_elbow"].append(f.angles.left_elbow.value if f.angles.left_elbow else np.nan)
        ts_data["right_elbow"].append(f.angles.right_elbow.value if f.angles.right_elbow else np.nan)
        ts_data["left_knee"].append(f.angles.left_knee.value if f.angles.left_knee else np.nan)
        ts_data["right_knee"].append(f.angles.right_knee.value if f.angles.right_knee else np.nan)
        ts_data["left_shoulder"].append(f.angles.left_shoulder.value if f.angles.left_shoulder else np.nan)
        ts_data["right_shoulder"].append(f.angles.right_shoulder.value if f.angles.right_shoulder else np.nan)
        ts_data["body_roll"].append(f.angles.body_roll.value if f.angles.body_roll else np.nan)
        ts_data["valid"].append(f.is_valid)
        
    df = pd.DataFrame(ts_data)
    
    for col in ["left_elbow", "right_elbow", "left_knee", "right_knee", "left_shoulder", "right_shoulder", "body_roll"]:
        df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
    
    if not df.empty:
        df.set_index('timestamp_ms', inplace=True)
        
        st.markdown("##### Valid Frames")
        st.write(f"High confidence frames: {df['valid'].sum()} / {len(df)}")
        
        st.markdown("##### Body Roll Angle")
        safe_log("[TRACE] ENTER body_roll_chart")
        try:
            st.line_chart(df[['body_roll']].dropna(how='all'))
        except Exception as e:
            logger.error(f"Error rendering body_roll chart: {e}")
        safe_log("[TRACE] EXIT body_roll_chart")
        
        st.markdown("##### Elbow Joint Angles Over Time")
        safe_log("[TRACE] ENTER elbow_chart")
        try:
            st.line_chart(df[['left_elbow', 'right_elbow']].dropna(how='all'))
        except Exception as e:
            logger.error(f"Error rendering elbows chart: {e}")
        safe_log("[TRACE] EXIT elbow_chart")
        
        st.markdown("##### Shoulder Angles Over Time")
        safe_log("[TRACE] ENTER shoulder_chart")
        try:
            st.line_chart(df[['left_shoulder', 'right_shoulder']].dropna(how='all'))
        except Exception as e:
            logger.error(f"Error rendering shoulders chart: {e}")
        safe_log("[TRACE] EXIT shoulder_chart")
        
        st.markdown("##### Stroke Phase Summary")
        safe_log("[TRACE] ENTER dataframe_render")
        if analysis_result.stroke_statistics:
            stats = analysis_result.stroke_statistics
            st.write(f"Completed Cycles: {stats.completed_cycles}")
            st.write(f"Avg Cycle Duration: {stats.average_cycle_duration_ms:.1f} ms")
            
            st.markdown("###### Time in Phases (ms)")
            phase_time_df = pd.DataFrame(list(stats.time_in_phases.items()), columns=['Phase', 'Time (ms)'])
            st.dataframe(phase_time_df, width='stretch')
        else:
            phases = [f.stroke_phase for f in analysis_result.frames if f.is_valid]
            phase_df = pd.Series(phases).value_counts().reset_index()
            phase_df.columns = ['Phase', 'Frame Count']
            st.dataframe(phase_df, width='stretch')
        safe_log("[TRACE] EXIT dataframe_render")
        
    else:
        st.info("No biomechanical data was successfully extracted.")
    safe_log("[TRACE] EXIT render_raw_data_tab")
