import streamlit as st
from services.production_services import get_requestable_skus, insert_product_request
from services.tracking_service import validate_materials_available
from schemas.production_schemas import ProductRequestCreate
from db.orm_session import get_session

def render_product_request_form():
    st.markdown("Submit New Product Request")

    with get_session() as db:
        skus = get_requestable_skus(db)

    if not skus:
        st.warning("No requestable SKUs found. Check your catalog.")
        return
    
    label_map: dict[str, int] = {}
    meta_map: dict[int, dict] = {}

    for sku_id, sku, name, is_bundle, pack_qty in skus:
        label = f"{sku} - {name}"
        label_map[label] = sku_id
        meta_map[sku_id] = {
            "is_bundle": bool(is_bundle),
            "pack_qty": int(pack_qty or 1),
        }
    
    with st.form("new_product_request_form"):
        label = st.selectbox("Select Product (SKU)", list(label_map.keys()))
        quantity = st.number_input("Quantity to Print", min_value=1, step=1)
        notes = st.text_area("Notes (optional)", max_chars=250).strip()

        submitted = st.form_submit_button("Submit Request")

        if submitted: 
            user_id = st.session_state.get("user_id")
            if not user_id:
                st.error("You must be logged in to make a request.")
                return
            
            sku_id = label_map[label]
            meta = meta_map[sku_id]
            pack_qty = meta["pack_qty"]
            is_bundle = meta["is_bundle"]

            expanded_qty = quantity * pack_qty if is_bundle else quantity

            with get_session() as db:
                errors, info = validate_materials_available(db, sku_id=sku_id, quantity=expanded_qty)

                if errors:
                    for e in errors:
                        st.error(e)
                    if info:
                        st.info(info)
                    return
                else:
                    try:
                        payload = ProductRequestCreate(
                            requested_by=user_id,
                            sku_id=sku_id,
                            quantity=int(expanded_qty),
                            notes=notes
                        )
                        insert_product_request(db, payload)

                        if is_bundle and pack_qty > 1:
                            st.success(f"Submitted! This will create {expanded_qty} individual bottles ({pack_qty} per bundle.)")
                        else:
                            st.success("Product request submitted successfully!")
                    except Exception as e:
                        st.error("Failed to submit request.")
                        st.exception(e)