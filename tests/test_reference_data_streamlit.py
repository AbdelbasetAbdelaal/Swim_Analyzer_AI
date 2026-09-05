"""
Tests for Streamlit UI helper imports and UI rendering integrity.
"""


def test_streamlit_ui_imports():
    from app.ui.reference_data_ui import render_reference_data_manager_page
    assert callable(render_reference_data_manager_page)
