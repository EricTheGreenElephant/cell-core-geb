import streamlit as st
import base64
from datetime import datetime
from components.label.label_generator import generate_label_with_overlays
from services.label_services import get_label_data_by_product_id
from db.orm_session import get_session
from streamlit.components.v1 import html
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
            return label_specs, qr_required, qr_specs
    return {}, False, {}

def render_label_form():
    st.subheader("Generate Product Label")

    product_ids = []
    label_choice = ""
    product_sku = ""
    manual_entry = False
    details_required = False

    search_option = st.selectbox(
        "Choose Search Option:",
        options=["Product ID", "Tridock"],
        index=0
    )
    if search_option == "Product ID":
        # Use for manual label generator
        manual_entry = st.checkbox(
            label="Select for manual product ID entry:",
            value=False,
            help="If you need to manually generate Product ID for label, click here. This will generally be needed throughout testing, since Product IDs may not match."
        )

        # product_id = st.text_input("Enter Product ID")
        product_id_search = st.number_input(
            label="Enter Product ID",
            min_value=0,
            step=1
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
                step=3 if product_specs["product_type"] == "CS MINI" else 1,
                help="This will automatically generate the addtional IDs for label printing."
            )
            if product_specs["product_type"] == "CS MINI":
                if product_amount % 3 != 0:
                    st.error("Please enter amount in 3s!")
                    return

            product_ids = [product_id_search + x for x in range(0, product_amount)]
        else:
            product_ids.append(product_id_search)

        product_id = st.radio(label="Choose Product ID", options=product_ids)
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

    label_specs, qr_required, qr_specs = label_spec_finder(label_choice)

    if label_choice == "CSmini_v3":
        options = [', '.join(str(x) for x in product_ids[y:y+3]) for y in range(0, len(product_ids)//3)] 
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
                expire_date = today.replace(year=today.year + 1)
                expiration_formatted = f"{expire_date.month} / {expire_date.year}"
                product_type = product_specs["product_type"]
                surface_area = product_specs["surface_area"]
            else:
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

                expiration_raw = data["expiration_date"]  # e.g. "2026-07-15"
                exp_date = datetime.strptime(expiration_raw, "%Y-%m-%d")
                expiration_formatted = f"{exp_date.month} / {exp_date.year}"
                product_sku = data["reference_number"]
                product_type = data["product_type"]
                surface_area = data["volume"]
                product_id = data["product_id"]

            # label_fields = [
            #     {"text": product_sku, "position": (380, 40), "font_size": 44},
            #     {"text": product_type, "position": (270, 169), "font_size": 42},
            #     {"text": f"{surface_area} cm\u00b2", "position": (150, 246), "font_size": 42},
            #     {"text": f"{product_id}", "position": (210, 550), "font_size": 42},
            #     {"text": expiration_formatted, "position": (210, 660), "font_size": 42},
            # ]
            qr_specs['qr_data'] = str(product_id)
            label_specs['surface_area']['text'] = f"{surface_area} cm\u00b2"
            label_specs['product_id']['text'] = str(product_id)
            label_specs['expiration_formatted']['text'] = expiration_formatted
            if "product_type" in label_specs:
                label_specs['product_type']['text'] = product_type

        label_specs['product_sku']['text'] = product_sku 
    
        # Temporary placeholder data
        # label_fields = [
        #     {"text": "GEB-AAAKTCS-4", "position": (305, 35), "font_size": 14},
        #     {"text": "CS MINI", "position": (40, 120), "font_size": 18},
        #     {"text": "6,000 cm²", "position": (40, 170), "font_size": 18},
        #     {"text": "LT2025-08", "position": (40, 220), "font_size": 18},
        #     {"text": "2026-08-01", "position": (40, 270), "font_size": 18},
        # ]

        # QR Code format specs
        # if product_type == "CS MINI":
        #     qr_position = (457, 333)
        #     qr_size = 135
        # else:
        #     qr_position = (613, 333)
        #     qr_size = 270
        # qr_data = product_id

        background_path = f"streamlit_app/assets/{label_choice}.png"
        # if label_choice == "Harvest":
        #     # background_path = "streamlit_app/assets/GEB-Label-Image-wo-Text.png"
        #     background_path = "streamlit_app/assets/Label-V2.png"
        # else:
        #     background_path = "streamlit_app/assets/GEB-Label2-Image-wo-Text.png"


        # for pid in product_ids:
            # label_fields.append({"text": f"{product_id}", "position": (210, 550), "font_size": 42})
        label_img = generate_label_with_overlays(
            background_path=background_path,
            # fields=label_fields,
            fields=label_specs,
            # qr_data=qr_data,
            # qr_position=qr_position,
            # qr_size=qr_size,
            qr_specs=qr_specs,
            qr_required=qr_required
        )


        st.success("Label generated.")

        # --- Inline PDF preview(iframe) ---
        pdf_b64 = base64.b64encode(label_img.getvalue()).decode("utf-8")
        html(
            f"""
            <iframe
                src="data:application/pdf;base64,{pdf_b64}"
                width="100%"
                height="700"
                style="border:1px solid #ddd; border-radius:8px;"
            ></iframe>
            """,
            height=720
        )

        # st.image(label_img, caption="Generated Label", use_container_width=False)

        # st.download_button(
        #     label="Download Label",
        #     type="primary",
        #     data=label_img,
        #     # file_name=f"label_{product_id}.png",
        #     file_name=f"label_{product_id}.pdf",
        #     # mime="image/png",
        #     mime="application/pdf",
        #     use_container_width=True
        # )
    
    # elif generate and not product_id:
    #     st.warning("Please enter a Product ID and label choice before generating.")
    #     return
    
    # elif generate and label_choice == "Select...":
    #     st.warning("Please choose a label!")
    #     return
