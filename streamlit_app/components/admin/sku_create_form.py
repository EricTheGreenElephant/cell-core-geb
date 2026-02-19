import streamlit as st
from db.orm_session import get_session
from services.admin_services import get_product_types, create_product_sku

def render_sku_create_form() -> bool:
    st.subheader("Create New SKU")

    with get_session() as db:
        product_types = get_product_types(db)

    if not product_types:
        st.warning("No product types found.")
        return False

    pt_options = {pt["name"]: int(pt["id"]) for pt in product_types}

    with st.form("create_sku_form"):
        product_type_name = st.selectbox("Product Type", list(pt_options.keys()))
        product_type_id = pt_options[product_type_name]

        sku = st.text_input("SKU Code", help="Unique code, e.g. ABC-123")
        name = st.text_input("SKU Name", help="Display name for users")

        c1, c2, c3 = st.columns(3)
        with c1:
            is_serialized = st.checkbox("Serialized", value=True)
        with c2:
            is_bundle = st.checkbox("Bundle", value=False)
        with c3:
            is_active = st.checkbox("Active", value=True)

        pack_qty = st.number_input("Pack Quantity", min_value=1, step=1, value=1)
        tech_transfer = st.checkbox("Tech Transfer (temporary label)", value=False)

        submitted = st.form_submit_button("Create SKU")

    if submitted:
        try:
            with get_session() as db:
                new_id = create_product_sku(
                    db,
                    product_type_id=product_type_id,
                    sku=sku,
                    name=name,
                    is_serialized=is_serialized,
                    is_bundle=is_bundle,
                    pack_qty=int(pack_qty),
                    is_active=is_active,
                    tech_transfer=tech_transfer,
                )
            st.success(f"SKU created (id={new_id}).")
            return True
        except Exception as e:
            st.error("Failed to create SKU.")
            st.exception(e)

    return False
