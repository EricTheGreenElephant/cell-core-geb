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
    
    label_map = {f"{sku} - {name}": sku_id for (sku_id, sku, name) in skus}
    
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

            with get_session() as db:
                errors, info = validate_materials_available(db, sku_id=sku_id, quantity=quantity)

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
                            quantity=quantity,
                            notes=notes
                        )
                        insert_product_request(db, payload)
                        st.success("Product request submitted successfully!")
                    except Exception as e:
                        st.error("Failed to submit request.")
                        st.exception(e)