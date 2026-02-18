import streamlit as st
from db.orm_session import get_session
from services.reasons_services import (
    get_contexts, get_reasons, upsert_reason,
    get_reason_context_ids, set_reason_contexts, toggle_reason_active
)

def render_reason_management():
    with get_session() as db:
        contexts = get_contexts(db)
        reasons = get_reasons(db, include_inactive=True)

    context_id_by_code = {c["context_code"]: c["id"] for c in contexts}
    context_label_by_id = {c["id"]: c["context_code"] for c in contexts}

    st.subheader("Create or Edit Reason")

    with st.form("reason_form", clear_on_submit=False):
        edit_mode = st.checkbox("Edit existing reason", value=False)
        selected_id = None
        if edit_mode:
            options = {f"{r['reason_label']} ({r['reason_code']})": r["id"] for r in reasons}
            chosen = st.selectbox("Select a reason to edit", options=list(options.keys()))
            selected_id = options[chosen]
            current = next(r for r in reasons if r["id"] == selected_id)
            def_val_code = current["reason_code"]
            def_val_label = current["reason_label"]
            def_val_cat = current["category"]
            def_val_out = current["default_outcome"]
            def_val_sev = current["severity"]
            def_val_active = bool(current["is_active"])
        else:
            def_val_code = ""
            def_val_label = ""
            def_val_cat = "Visual"
            def_val_out = "B-Ware"
            def_val_sev = None
            def_val_active = True

        reason_code = st.text_input("Reason Code", value=def_val_code, help="Stable identifier, e.g., VIS_MISSING_LID")
        reason_label = st.text_input("Reason Label", value=def_val_label, help="User-facing label")
        category = st.text_input("Category", value=def_val_cat, help="Visual, Packaging, Process, etc.")
        default_outcome = st.selectbox(
            "Default Outcome (optional)", 
            options=[None, "B-Ware", "Waste", "Quarantine"], 
            index=[None, "B-Ware", "Waste", "Quarantine"].index(def_val_out) if def_val_out in ["B-Ware", "Waste", "Quarantine"] else 0
        )
        severity = st.number_input("Severity (optional, 1-5)", min_value=1, max_value=5, value=int(def_val_sev) if def_val_sev is not None else 1)
        is_active = st.checkbox("Active", value=def_val_active)

        submitted = st.form_submit_button("Save Reason")
        if submitted:
            try:
                with get_session() as db:
                    new_id = upsert_reason(
                        db,
                        reason_id=selected_id,
                        reason_code=reason_code.strip(),
                        reason_label=reason_label.strip(),
                        category=category.strip(),
                        default_outcome=default_outcome,
                        severity=severity if severity else None,
                        is_active=is_active
                    )
                st.success(f"Reason saved (id={new_id}).")
                st.rerun()
            except Exception as e:
                st.error("Failed to save reason.")
                st.exception(e)

    st.divider()

    st.subheader("Reason -> Context Mapping")

    for r in reasons:
        with st.expander(f"{r['reason_label']} ({r['reason_code']}) * Category: {r['category']} * Active: {bool(r['is_active'])}"):
            cols = st.columns([2, 1])
            with cols[0]:
                with get_session() as db:
                    mapped_ids = set(get_reason_context_ids(db, r["id"]))
                current_labels = [context_label_by_id[cid] for cid in mapped_ids]
                chosen_labels = st.multiselect(
                    "Enabled in contexts",
                    options=list(context_id_by_code.keys()),
                    default=current_labels,
                    key=f"contexts_{r['id']}"
                )
                new_ids = [context_id_by_code[label] for label in chosen_labels]
                if st.button("Save Context Mapping", key=f"save_map_{r['id']}"):
                    try:
                        with get_session() as db:
                            set_reason_contexts(db, r["id"], new_ids)
                        st.success("Mapping saved.")
                    except Exception as e:
                        st.error("Failed to save mapping.")
                        st.exception(e)
            with cols[1]:
                active_toggle = st.checkbox("Active", value=bool(r["is_active"]), key=f"active_{r['id']}")
                if st.button("Apply Active Toggle", key=f"toggle_{r['id']}"):
                    try:
                        with get_session() as db:
                            toggle_reason_active(db, r["id"], active_toggle)
                        st.success("Active state updated.")
                    except Exception as e:
                        st.error("Failed to update active state.")
                        st.exception(e)