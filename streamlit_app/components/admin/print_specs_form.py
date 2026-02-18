# components/admin/print_specs_form.py

import streamlit as st
from db.orm_session import get_session
from services.admin_services import (
    get_skus_with_print_specs_flag,
    get_print_specs_for_sku,
    upsert_print_specs,
)

def render_print_specs_admin() -> bool:
    """
    Admin UI to view/edit product_print_specs for a SKU.
    Returns True if something was saved (caller should st.rerun()).
    """
    st.subheader("SKU Print Specs")

    # --- Load SKUs + flag for missing specs (one DB call) ---
    with get_session() as db:
        skus = get_skus_with_print_specs_flag(db)

    if not skus:
        st.info("No SKUs found.")
        return False

    # --- Filters ---
    cols = st.columns([1, 2])
    with cols[0]:
        only_missing = st.checkbox("Show only SKUs missing print specs", value=False)

    filtered = [s for s in skus if (s["has_print_specs"] == 0)] if only_missing else skus

    if not filtered:
        st.success("All SKUs have print specs 🎉")
        return False

    # --- SKU chooser ---
    # Nice labels for admins: status icon + name + sku + inactive hint
    def _label(s: dict) -> str:
        icon = "✅" if s["has_print_specs"] else "⚠️"
        inactive = " [inactive]" if not bool(s.get("is_active", True)) else ""
        return f"{icon} {s.get('name','(no name)')} ({s.get('sku','')}){inactive} — id={s['id']}"

    # Make ordering stable and friendly (already ordered in SQL, but just in case)
    filtered_sorted = sorted(filtered, key=lambda x: (str(x.get("name", "")).lower(), str(x.get("sku", "")).lower()))

    options = {_label(s): int(s["id"]) for s in filtered_sorted}
    selected_label = st.selectbox("Select SKU", list(options.keys()))
    sku_id = options[selected_label]

    # --- Load current specs for selected SKU ---
    with get_session() as db:
        specs = get_print_specs_for_sku(db, sku_id)

    if specs is None:
        st.warning("No print specs exist for this SKU yet. Fill the form below to create them.")
        defaults = {
            "height_mm": 0.0,
            "diameter_mm": 0.0,
            "average_weight_g": 0.0,
            "weight_buffer_g": 0.0,
        }
    else:
        defaults = specs

    # --- Edit form ---
    with st.form("print_specs_form"):
        c1, c2 = st.columns(2)

        with c1:
            height_mm = st.number_input(
                "Height (mm)",
                min_value=0.0,
                value=float(defaults["height_mm"]),
                step=0.01,
                format="%.2f",
                key=f"pps_height_{sku_id}",
            )
            diameter_mm = st.number_input(
                "Diameter (mm)",
                min_value=0.0,
                value=float(defaults["diameter_mm"]),
                step=0.01,
                format="%.2f",
                key=f"pps_diameter_{sku_id}",
            )

        with c2:
            average_weight_g = st.number_input(
                "Average Weight (g)",
                min_value=0.0,
                value=float(defaults["average_weight_g"]),
                step=0.01,
                format="%.2f",
                key=f"pps_avg_w_{sku_id}",
            )
            weight_buffer_g = st.number_input(
                "Weight Buffer (g)",
                min_value=0.0,
                value=float(defaults["weight_buffer_g"]),
                step=0.01,
                format="%.2f",
                key=f"pps_buf_w_{sku_id}",
            )

        reason = st.text_area(
            "Reason for change (required)",
            key=f"pps_reason_{sku_id}",
            placeholder="e.g., measured new dimensions after calibration",
        )


        submitted = st.form_submit_button("Save Print Specs")

    if submitted:
        user_id = st.session_state.get("user_id") or st.session_state.get("user", {}).get("id")

        problems = []
        if user_id is None:
            problems.append("Missing user_id in session (login state).")
        if not reason.strip():
            problems.append("Reason is required.")
        if height_mm <= 0:
            problems.append("Height must be > 0.")
        if diameter_mm <= 0:
            problems.append("Diameter must be > 0.")
        if average_weight_g <= 0:
            problems.append("Average weight must be > 0.")
        if weight_buffer_g < 0:
            problems.append("Weight buffer must be ≥ 0.")

        if problems:
            st.error("Cannot save:\n- " + "\n- ".join(problems))
            return False

        try:
            with get_session() as db:
                upsert_print_specs(
                    db,
                    sku_id=sku_id,
                    height_mm=float(height_mm),
                    diameter_mm=float(diameter_mm),
                    average_weight_g=float(average_weight_g),
                    weight_buffer_g=float(weight_buffer_g),
                    reason=reason.strip(),
                    changed_by=int(user_id),
                )
            st.success("Print specs saved.")
            return True
        except Exception as e:
            st.error("Failed to save print specs.")
            st.exception(e)
            return False