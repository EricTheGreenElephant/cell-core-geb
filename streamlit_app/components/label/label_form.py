import streamlit as st
import base64
from datetime import datetime
from components.label.label_generator import generate_label_with_overlays
from services.label_services import get_label_data_by_product_id, get_harvested
from db.orm_session import get_session
from constants.label_constants import SKU_DATA_SPECS, QR_LABEL_MAP

def label_validation(product_sku: str):
    label_choices = []
    for package in QR_LABEL_MAP:
        if product_sku in package["allowed_skus"]:
            label_choices += package["labels"]
    return label_choices

def label_spec_finder(label: str):
    for package in QR_LABEL_MAP:
        if label in package["labels"]:
            label_specs = package["label_specs"]
            qr_required = package["qr_required"]
            qr_specs = package["qr_specs"]
            print_size = package["print_size"]
            return label_specs, qr_required, qr_specs, print_size
    return {}, False, {}, 0

def render_label_form():
    st.subheader("Generate Product Label")

    product_ids = []
    label_choice = ""
    product_sku = ""
    manual_entry = False
    details_required = False
    automate = False

    search_option = st.selectbox(
        "Choose Search Option:",
        options=["Select an option...", "Pull harvested products", "Product ID", "Tridock"],
        index=0
    )
    if search_option == "Pull harvested products":
        with get_session() as db:
            product_ids = get_harvested(db)
        
        if product_ids:
            product_options = {
                f"{p['product_id']} | {p['reference_number']} | {p['product_type']}": product_ids.index(p)
                for p in product_ids
            }
            
            selected_product = st.selectbox("Choose product", options=list(product_options.keys()))

            product_idx = product_options[selected_product]
            product_data = product_ids[product_idx]
            product_sku = product_data["reference_number"]
            product_id = product_data["product_id"]
            product_specs = SKU_DATA_SPECS[product_sku]
            details_required = True

        else:
            st.info("No recently harvested products.")

    elif search_option == "Product ID":
        # Use for manual label generator
        manual_entry = st.checkbox(
            label="Select for manual product ID entry:",
            value=False,
            help="If you need to manually generate Product ID for label, click here. This will generally be needed throughout testing, since Product IDs may not match."
        )

        if manual_entry:
            product_sku = st.selectbox(
                label="Choose the Product SKU",
                # options=QR_LABEL_DATA_SPECS.keys()
                options=SKU_DATA_SPECS.keys(),
                index=0
            )
            product_specs = SKU_DATA_SPECS[product_sku]

            product_amount = st.number_input(
                label="Enter number of products for label printing.",
                min_value=0,
                max_value=1000,
                step=1,
                help="This will automatically generate the addtional IDs for label printing."
            )
            
            if product_amount > 1:
                automate = st.checkbox(
                    "Auto Generate Product ID numbers",
                    value=False
                )

            if automate:
                product_id_input = st.number_input(
                    label="Enter First Product ID",
                    min_value=0,
                    step=1
                )
                product_ids = [product_id_input + x for x in range(0, product_amount)]

            else:
                for i in range(int(product_amount)):
                    product_id_input = st.number_input(
                        f"Product ID:",
                        key=f"product_id_{i}",
                        step=1
                    )
                    product_ids.append(product_id_input)

        else:
            # product_id = st.text_input("Enter Product ID")
            product_id_search = st.number_input(
                label="Enter Product ID",
                min_value=0,
                step=1
            )
            product_ids.append(product_id_search)

        product_id = st.radio(label="Choose Product ID", options=product_ids)
        try:
            product_id_int = int(product_id)
        except ValueError:
            st.error("Product ID must be a number.")
            return

        with get_session() as db:
            data = get_label_data_by_product_id(db, product_id_int)
        
        if not data:
            st.warning("Product not found.")
            return
        product_sku = data["reference_number"]
        details_required = True

    else:
        search_option = "Tridock"
        product_sku = "GEB-CSmTD"
    
    label_choices = label_validation(product_sku)
    
    # label_choice = st.selectbox("Choose Label", options=["Select...", "Harvest", "Bag and Package"], index=0)
    label_choice = st.selectbox(
        "Choose label",
        options=label_choices,
        index=0
    )

    label_specs, qr_required, qr_specs, print_size = label_spec_finder(label_choice)

    if label_choice == "CSmini_v3":
        options = [', '.join(str(x) for x in product_ids[y*3:3*(y+1)]) for y in range(0, len(product_ids)//3)] 
        product_id = st.radio(
            "Choose Version 3 label Product ID display",
            options=options,
            index=0
        )

    generate = st.button("Generate Label", type="primary", use_container_width=True)
    
    if generate and label_choice:
        if details_required:
            if manual_entry:
                today = datetime.today()
                expire_date = today.replace(year=today.year + 2)
                expiration_formatted = f"{expire_date.month} / {expire_date.year}"
                product_type = product_specs["product_type"]
                surface_area = product_specs["surface_area"]
            elif search_option == "Pull harvested products":
                expire_date = datetime.strptime(product_data["expiration_date"], "%Y-%m-%d")
                expiration_formatted = f"{expire_date.month} / {expire_date.year}"
                product_type = product_specs["product_type"]
                surface_area = product_specs["surface_area"]
            else:
                expiration_raw = data["expiration_date"]  # e.g. "2026-07-15"
                exp_date = datetime.strptime(expiration_raw, "%Y-%m-%d")
                expiration_formatted = f"{exp_date.month} / {exp_date.year}"
                product_sku = data["reference_number"]
                product_specs = SKU_DATA_SPECS[product_sku]
                product_type = product_specs["product_type"]
                surface_area = product_specs["surface_area"]
                product_id = data["product_id"]

            qr_specs['qr_data'] = str(product_id)
            label_specs['surface_area']['text'] = f"{surface_area} cm\u00b2"
            label_specs['product_id']['text'] = str(product_id)
            label_specs['expiration_formatted']['text'] = expiration_formatted
            if "product_type" in label_specs:
                label_specs['product_type']['text'] = product_type

        label_specs['product_sku']['text'] = product_sku 

        background_path = f"streamlit_app/assets/labels/{label_choice}.png"

        label_img = generate_label_with_overlays(
            background_path=background_path,
            fields=label_specs,
            qr_specs=qr_specs,
            qr_required=qr_required,
            print_size=print_size
        )

        st.success("Label generated.")

        # --- Inline PDF preview(iframe) ---
        pdf_b64 = base64.b64encode(label_img.getvalue()).decode("utf-8")
        st.markdown(
            f"""
            <iframe
                src="data:application/pdf;base64,{pdf_b64}"
                width="100%"
                height="700"
                style="border:1px solid #ddd; border-radius:8px;"
            ></iframe>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <p style="margin-top: 0.5rem;">
                <a href="data:application/pdf;base64,{pdf_b64}" target="_blank">
                    Open label in new tab
                </a>
            </p>
            """,
            unsafe_allow_html=True,
        )
