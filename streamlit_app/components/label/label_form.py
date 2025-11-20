import streamlit as st
import base64
from datetime import datetime
from components.label.label_generator import generate_label_with_overlays
from services.label_services import get_label_data_by_product_id
from db.orm_session import get_session
from streamlit.components.v1 import html


def render_label_form():
    st.subheader("Generate Product Label")

    product_id = st.text_input("Enter Product ID")
    label_choice = st.selectbox("Choose Label", options=["Select...", "Harvest", "Bag and Package"], index=0)
    generate = st.button("Generate Label", type="primary", use_container_width=True)
    
    if generate and product_id and label_choice != "Select...":
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

        label_fields = [
            {"text": data["reference_number"], "position": (380, 40), "font_size": 42},
            {"text": data["product_type"], "position": (270, 169), "font_size": 42},
            {"text": f"{data['volume']} cm\u00b2", "position": (150, 246), "font_size": 42},
            {"text": f"{data['product_id']}", "position": (210, 550), "font_size": 42},
            {"text": expiration_formatted, "position": (210, 660), "font_size": 42},
        ]
    
        # Temporary placeholder data
        # label_fields = [
        #     {"text": "GEB-AAAKTCS-4", "position": (305, 35), "font_size": 14},
        #     {"text": "CS MINI", "position": (40, 120), "font_size": 18},
        #     {"text": "6,000 cm²", "position": (40, 170), "font_size": 18},
        #     {"text": "LT2025-08", "position": (40, 220), "font_size": 18},
        #     {"text": "2026-08-01", "position": (40, 270), "font_size": 18},
        # ]
    
        qr_position = (613, 333)
        qr_data = product_id

        if label_choice == "Harvest":
            # background_path = "streamlit_app/assets/GEB-Label-Image-wo-Text.png"
            background_path = "streamlit_app/assets/Label-V2.png"
        else:
            background_path = "streamlit_app/assets/GEB-Label2-Image-wo-Text.png"

        label_img = generate_label_with_overlays(
            background_path=background_path,
            fields=label_fields,
            qr_data=qr_data,
            qr_position=qr_position
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

        st.download_button(
            label="Download Label",
            type="primary",
            data=label_img,
            # file_name=f"label_{product_id}.png",
            file_name=f"label_{product_id}.pdf",
            # mime="image/png",
            mime="application/pdf",
            use_container_width=True
        )
    
    elif generate and not product_id:
        st.warning("Please enter a Product ID and label choice before generating.")
        return
    
    elif generate and label_choice == "Select...":
        st.warning("Please choose a label!")
        return
