"""Simple secure authentication helpers for Streamlit."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional

import streamlit as st

from database import execute, fetch_one


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    salt = salt or os.urandom(16).hex()
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        120_000,
    ).hex()
    return password_hash, salt


def create_user(username: str, password: str, role: str = "Analyst") -> bool:
    if not username.strip() or len(password) < 6:
        return False
    password_hash, salt = hash_password(password)
    try:
        execute(
            "INSERT INTO users(username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
            (username.strip().lower(), password_hash, salt, role),
        )
        return True
    except Exception:
        return False


def authenticate(username: str, password: str) -> Optional[dict]:
    user = fetch_one("SELECT * FROM users WHERE username = ?", (username.strip().lower(),))
    if not user:
        return None
    attempted_hash, _ = hash_password(password, user["salt"])
    if hmac.compare_digest(attempted_hash, user["password_hash"]):
        return user
    return None


def require_login() -> bool:
    if "user" in st.session_state:
        return True

    st.sidebar.title("Login")
    tab_login, tab_signup = st.sidebar.tabs(["Login", "Create account"])

    with tab_login:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", use_container_width=True):
            user = authenticate(username, password)
            if user:
                st.session_state.user = {"username": user["username"], "role": user["role"]}
                st.rerun()
            st.error("Invalid username or password")

    with tab_signup:
        new_username = st.text_input("New username", key="new_username")
        new_password = st.text_input("New password", type="password", key="new_password")
        role = st.selectbox("Role", ["Analyst", "Project Manager", "Auditor"])
        if st.button("Create account", use_container_width=True):
            if create_user(new_username, new_password, role):
                st.success("Account created. Now log in.")
            else:
                st.warning("Use a unique username and a password of at least 6 characters.")

    return False


def logout_button() -> None:
    user = st.session_state.get("user")
    if not user:
        return
    st.sidebar.caption(f"Signed in as **{user['username']}** · {user['role']}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.pop("user", None)
        st.rerun()
