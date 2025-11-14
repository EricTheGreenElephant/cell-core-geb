import urllib.parse
import streamlit as st
from typing import Optional, Dict
from utils.auth import get_current_user


def build_login_url(redirect_to: str = "/") -> str:
    return "/.auth/login/aad?post_login_redirect_uri=" + urllib.parse.quote(redirect_to, safe="")

def build_logout_url(redirect_to: str = "/") -> str:
    return "/.auth/logout?post_logout_redirect_uri=" + urllib.parse.quote(redirect_to, safe="")

def render_account_box(expanded: bool = True, home_after_logout: str = "/"):
    """
    Renders a sidebar 'Account' box with Login, Logout, and Switch account.
    - Logout returns to `home_after_logout` (default "/")
    - Login returns to the *current* path (best-effort) so users land back where they were
    """
    user = get_current_user()
    with st.sidebar.expander("Account", expanded=expanded):
        if user:
            st.write(f"Signed in as **{user['name'] or user['email']}**")
            col1, col2 = st.columns(2)
            with col1:
                st.link_button("Log out", build_logout_url(home_after_logout))
            with col2:
                # Switch = log out, then immediately start login back to the current page
                st.link_button("Switch account", build_logout_url(build_login_url()))
        else:
            st.write("You’re not signed in.")
            st.link_button("Log in", build_login_url())
            st.caption("Use your Microsoft Entra account.")