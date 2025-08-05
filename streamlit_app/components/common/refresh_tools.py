import streamlit as st


def refresh_cache(label: str = "Refresh", key: str = "refresh_button") -> bool:
    """
    Renders a refresh button and clears Streamlit's data cache if clicked.

    Returns:
        bool: True if the button was clicked, False otherwise.
    """
    clicked = st.button(label, key=key)
    if clicked:
        st.cache_data.clear()
    return clicked