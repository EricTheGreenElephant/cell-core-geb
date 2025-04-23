import streamlit as st

def toggle_button(state_key: str, label_off: str, label_on: str):
    """
    A resuable toggle button that updates a boolean session state key.
    
    Parameters: 
        - state_key: the session state key to track (e.g. 'show_inventory')
        - label_off: button label when the toggle is False (off)
        - label_on: button label when the toggle is True (on)
    """

    if state_key not in st.session_state:
        st.session_state[state_key] = False

    def _toggle():
        st.session_state[state_key] = not st.session_state[state_key]

    current_state = st.session_state[state_key]

    st.button(
        label_on if current_state else label_off,
        key=f"toggle_btn_{state_key}",
        on_click=_toggle
    )
    