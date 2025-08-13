import streamlit as st
import pandas as pd
import time
from services.quality_management_services import (
    search_products_for_quarantine, 
    mark_products_ad_hoc_quarantine
)
from db.orm_session import get_session


def render_ad_hoc_quarantine():
    st.subheader("Ad-Hoc Quarantine")

    if "adhoc_results" not in st.session_state:
        st.session_state["adhoc_results"] = []

    search_mode = st.selectbox(
        "Search By",
        options=["Product ID", "Lot Number", "Treatment Batch", "Filament Mount ID"]
    )

    if search_mode == "Product ID":
        search_value = st.number_input("Enter Product ID", min_value=1, step=1)
    else:
        search_value = st.text_input(f"Enter {search_mode}").strip()

    if st.button("Search"):
        if not search_value:
            st.warning("Please enter a value to search.")
            return

        try:
            with get_session() as db:
                results = search_products_for_quarantine(db, search_mode, search_value)
            if not results:
                st.info("No products found matching the search criteria.")
                st.session_state["adhoc_results"] = []
                return
            
            st.session_state["adhoc_results"] = [r.model_dump() for r in results]

        except Exception as e:
            st.error("Failed to search for products.")
            st.exception(e)
            return
    
    if st.session_state["adhoc_results"]:
        df = pd.DataFrame(st.session_state["adhoc_results"])

        if "Select" not in df.columns:
            df["Select"] = False

        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Select": st.column_config.CheckboxColumn("Select for Quarantine"),
                "product_id": st.column_config.NumberColumn("Product ID"),
                "tracking_id": st.column_config.TextColumn("Tracking ID"),
                "product_type": st.column_config.TextColumn("Product Type"),
                "lot_number": st.column_config.TextColumn("Lot Number"),
                "current_stage_name": "Current Stage",
                "current_status": "Current Status",
                "location_name": "Location",
                "last_updated_at": st.column_config.DatetimeColumn("Last Updated"),
            },
            disabled=(
                "product_id", "tracking_id", "product_type", 
                "lot_number", "current_stage_name", "current_status", 
                "location_name", "last_updated_at"
            )
        )
        # st.write(f"Found {len(results)} product(s). Select products to quarantine:")
        # selected_products = []
        # for r in results:
        #     with st.expander(f"Product {r.product_id} - {r.product_type}"):
        #         st.write(f"**Tracking ID:** {r.tracking_id}")
        #         st.write(f"**Lot Number:** {r.lot_number or 'N/A'}")
        #         st.write(f"**Current Stage:** {r.current_stage_name}")
        #         st.write(f"**Current Status:** {r.current_status or 'N/A'}")
        #         st.write(f"**Location:** {r.location_name or 'N/A'}")
        #         st.write(f"**Last Updated:** {r.last_updated_at.strftime('%Y-%d-%m %H:%M')}")

        #         if st.checkbox(f"Mark Product {r.product_id} for Quarantine", key=f"adhocq_{r.product_id}"):
        #             selected_products.append(r.product_id)
        selected_products = edited_df.loc[edited_df["Select"], "product_id"].tolist()

        if selected_products:
            st.markdown("---")
            st.write(f"Selected {len(selected_products)} product(s) for quarantine.")
            comment = st.text_area("Quarantine Reason (required)", max_chars=255).strip()

            if st.button("Confirm Quarantine"):
                if not comment:
                    st.warning("You must provide a reason for quarantine.")
                    return
                try:
                    user_id = st.session_state.get("user_id")
                    with get_session() as db:
                        mark_products_ad_hoc_quarantine(
                            db=db,
                            product_ids=selected_products,
                            user_id=user_id,
                            comment=comment
                        )
                    st.success(f"{len(selected_products)} product(s) moved to quarantine.")
                    st.session_state["adhoc_results"] = []
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error("Failed to quarantine selected products.")
                    st.exception(e)