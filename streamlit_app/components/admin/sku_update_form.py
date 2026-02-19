import streamlit as st
from db.orm_session import get_session
from services.admin_services import get_all_skus, get_sku_by_id, update_product_sku_with_audit

def render_sku_update_form() -> bool:
    st.subheader("Update SKU")

    with get_session() as db:
        skus = get_all_skus(db, include_inactive=True)

    if not skus:
        st.info("No SKUs found.")
        return False

    options = {f"{s['name']} ({s['sku']}) — id={s['id']}": int(s["id"]) for s in skus}
    selected = st.selectbox("Select SKU", list(options.keys()))
    sku_id = options[selected]

    with get_session() as db:
        cur = get_sku_by_id(db, sku_id)

    if not cur:
        st.warning("SKU not found.")
        return False

    with st.form(f"update_sku_{sku_id}"):
        name = st.text_input("Name", value=str(cur["name"]))
        sku_code = st.text_input("SKU Code", value=str(cur["sku"]))
        is_serialized = st.checkbox("Serialized", value=bool(cur["is_serialized"]))
        is_bundle = st.checkbox("Bundle", value=bool(cur["is_bundle"]))
        pack_qty = st.number_input("Pack Quantity", min_value=1, step=1, value=int(cur["pack_qty"]))
        is_active = st.checkbox("Active", value=bool(cur["is_active"]))
        tech_transfer = st.checkbox("Tech Transfer (temporary label)", value=bool(cur.get("tech_transfer", False)))

        reason = st.text_area("Reason (required)", placeholder="Why are you changing this SKU?")

        submitted = st.form_submit_button("Save SKU Changes")

    if submitted:
        user_id = st.session_state.get("user_id") or st.session_state.get("user", {}).get("id")
        problems = []
        if user_id is None:
            problems.append("Missing user_id in session.")
        if not reason.strip():
            problems.append("Reason is required.")
        if not name.strip():
            problems.append("Name is required.")
        if not sku_code.strip():
            problems.append("SKU code is required.")
        if not is_bundle and int(pack_qty) != 1:
            problems.append("pack_qty must be 1 when Bundle is unchecked.")

        if problems:
            st.error("Cannot save:\n- " + "\n- ".join(problems))
            return False

        # compute changes
        changes = {}
        if name.strip() != cur["name"]:
            changes["name"] = name.strip()
        if sku_code.strip() != cur["sku"]:
            changes["sku"] = sku_code.strip()
        if bool(is_serialized) != bool(cur["is_serialized"]):
            changes["is_serialized"] = 1 if is_serialized else 0
        if bool(is_bundle) != bool(cur["is_bundle"]):
            changes["is_bundle"] = 1 if is_bundle else 0
        new_pack = 1 if not is_bundle else int(pack_qty)
        if int(new_pack) != int(cur["pack_qty"]):
            changes["pack_qty"] = int(new_pack)
        if bool(is_active) != bool(cur["is_active"]):
            changes["is_active"] = 1 if is_active else 0
        if bool(tech_transfer) != bool(cur.get("tech_transfer", False)):
            changes["tech_transfer"] = 1 if tech_transfer else 0

        if not changes:
            st.info("No changes detected.")
            return False

        try:
            with get_session() as db:
                update_product_sku_with_audit(
                    db,
                    sku_id=sku_id,
                    changes=changes,
                    reason=reason.strip(),
                    changed_by=int(user_id),
                )
            st.success("SKU updated.")
            return True
        except Exception as e:
            st.error("Failed to update SKU.")
            st.exception(e)

    return False
