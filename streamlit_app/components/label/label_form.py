import streamlit as st
import base64
import copy
from datetime import datetime
from io import BytesIO
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
    selected_products = []
    label_choice = ""
    product_sku = ""
    details_required = True
    automate = False
    single = False

    selected_option = st.selectbox(
        "Quick Search",
        options=[
            "Select an option...",
            "Pull Harvested",
            "Pull Post-QC",
            "More options"
        ],
        index=0
    )

    if selected_option == "More options":
        alt_option = st.selectbox(
            "Select another option:",
            options=[
            "Select an option...",
            "Search Product ID", 
            "Enter ID Manually",
            "Tridock"
            ],
            index=0
        )
        selected_option = alt_option

    if selected_option == "Select an option...":
        return 
       
    if selected_option == "Tridock":
        details_required = False
        product_sku = "GEB-CSmTD"

    elif selected_option == "Enter ID Manually":
        today = datetime.today()
        expire_date = today.replace(year=today.year + 2)
        expiration_formatted = f"{expire_date.month} / {expire_date.year}"

        product_sku = st.selectbox(
            label="Choose the Product SKU",
            options=SKU_DATA_SPECS.keys(),
            index=0
        )

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
        # product_id = st.radio(label="Choose Product ID", options=product_ids)
        for pid in product_ids:
            product_data = {"product_id": pid, "reference_number": product_sku, "expiration_date": expiration_formatted}
            selected_products.append(product_data)

    else:
        if selected_option == "Search Product ID":
            single = True
            product_id_search = st.number_input(
                label="Enter Product ID",
                min_value=0,
                step=1
            )
            try:
                product_id = int(product_id_search)
            except ValueError:
                st.error("Product ID must be a number.")
                return
        with get_session() as db:
            if single:
                product_data = get_label_data_by_product_id(db, product_id)
            else:    
                product_data = get_harvested(db, selected_option)

            if not product_data:
                st.warning("Product not found.")
                return

            product_options = {
                f"{p['product_id']} | {p['reference_number']} | {p['product_type']}": product_data.index(p)
                for p in product_data
            }
            product_ids = [
                p['product_id'] for p in product_data 
                if SKU_DATA_SPECS.get(p['reference_number'], {}).get('product_type') == 'CS MINI'
            ]
            
            selected_product = st.multiselect(
                "Choose product to print", 
                options=list(product_options.keys()),
                key=f"product_select"
            )
            if selected_product:
                for product in selected_product:
                    product_idx = product_options[product]
                    selected_product_data = product_data[product_idx]
                    expire_date = datetime.strptime(selected_product_data["expiration_date"], "%Y-%m-%d")
                    expiration_formatted = f"{expire_date.month} / {expire_date.year}"
                    selected_product_data["expiration_date"] = expiration_formatted
                    selected_products.append(selected_product_data)

        # if product_data:
            # product_sku = product_data["reference_number"]
            # product_id = product_data["product_id"]
            # expire_date = datetime.strptime(product_data["expiration_date"], "%Y-%m-%d")
            # expiration_formatted = f"{expire_date.month} / {expire_date.year}"
        # else:
        #     st.info("No recently harvested products.")

    
    if selected_products:
        images = []
        for product_to_print in selected_products:
            if product_to_print["reference_number"]:
                product_sku = product_to_print["reference_number"]
                product_id = product_to_print["product_id"]
                label_choices = label_validation(product_sku)
                
                # label_choice = st.selectbox(
                #     "Choose label",
                #     options=label_choices,
                #     index=0
                # )
                selected_labels = st.multiselect(
                    f"Choose label(s) for Product ID: {product_id}",
                    options=label_choices,
                    default=label_choices[:1] if label_choices else [],
                    key=f"label_select_{product_id}"
                )

                if "CSmini_v3" in selected_labels:
                    selected_product_ids = st.multiselect(
                        "Choose Product IDs to display:",
                        options=product_ids,
                        key=f"selected_label_display_{product_id}"
                    )

                    if len(selected_product_ids) < 3:
                        st.warning("Your label contains less than 3 CS minis.")
                    if len(selected_product_ids) > 3:
                        st.warning("Your label contains more than 3 CS minis.")

                    display_product_id = ', '.join(str(x) for x in selected_product_ids)
                    st.write(display_product_id)


            # if generate and selected_labels:
            if selected_labels:
                # images = []

                for label_choice in selected_labels:

                    label_specs, qr_required, qr_specs, print_size = label_spec_finder(label_choice)

                    label_specs = copy.deepcopy(label_specs)
                    qr_specs = copy.deepcopy(qr_specs)

                    if label_choice == "CSmini_v3":
                        product_id = display_product_id

                    if details_required and label_choice:
                        product_specs = SKU_DATA_SPECS[product_sku]
                        product_type = product_specs["product_type"]
                        surface_area = product_specs["surface_area"]
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

                    images.append(label_img)

        generate = st.button("Generate Label", type="primary", use_container_width=True)
        if generate:
            pdf_out = BytesIO()
            images[0].save(pdf_out, format="PDF", save_all=True, append_images=images[1:])
            pdf_out.seek(0)

            pdf_bytes = pdf_out.getvalue()
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            # --- Inline PDF preview(iframe) ---

            # pdf_b64 = base64.b64encode(label_img.getvalue()).decode("utf-8")
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
