import streamlit as st


class StateManager:
    @staticmethod
    def get(scope: str, id_: str, key:str):
        return st.session_state.get(f"{scope}:{id_}:{key}")
    
    @staticmethod
    def set(scope: str, id_: str, key: str, value):
        st.session_state[f"{scope}:{id_}:{key}"] = value

    @staticmethod
    def clear(scope: str, id_: str):
        keys_to_delete = [k for k in st.session_state if k.startswith(f"{scope}:{id_}:")]
        for k in keys_to_delete:
            del st.session_state[k]