import streamlit as st
import pandas as pd
import time
from services.quality_management_services import (
    search_products_for_quarantine, 
    mark_products_ad_hoc_quarantine
)
from services.reasons_services import get_reasons_for_context, filter_reasons_by_outcome
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
                "sku": st.column_config.TextColumn("SKU"),
                "sku_name": st.column_config.TextColumn("SKU Desc."),
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

        selected_products = edited_df.loc[edited_df["Select"], "product_id"].tolist()

        if selected_products:
            st.markdown("---")
            st.write(f"Selected {len(selected_products)} product(s) for quarantine.")

            CONTEXT_CODE = "AdHoc"

            try:
                with get_session() as db:
                    reasons = get_reasons_for_context(db, context_code=CONTEXT_CODE, include_inactive=False)
                
                reasons = filter_reasons_by_outcome(reasons, outcome="Quarantine")
                
            except Exception as e:
                st.error("Failed to load quarantine reasons.")
                st.exception(e)
                return
            
            if not reasons:
                st.warning(f"No reasons configured for context '{CONTEXT_CODE}'.")
                return
            
            reason_options = {
                (f"{r['reason_label']} [{r['category']}]" if r["category"] else r["reason_label"]): r["id"]
                for r in reasons
            }
            other_id = next((r["id"] for r in reasons if r["reason_code"] == "OTHER_QUARANTINE"), None)

            with st.form("adhoc_quarantine_confirm"):
                chosen_reason_labels = st.multiselect(
                    "Reason(s)",
                    options=list(reason_options.keys()),
                )
                chosen_reason_ids = [reason_options[label] for label in chosen_reason_labels]
                is_other_selected = (other_id is not None) and (other_id in chosen_reason_ids)
                notes_placeholder = "; ".join(chosen_reason_labels)
                
                comment = st.text_area(
                    "Comment" + (" (required for 'Other')" if is_other_selected else " (optional)"),
                    value=notes_placeholder,
                    max_chars=255,
                    placeholder="Add details. If you picked 'Other', explain why."
                ).strip()

                submitted = st.form_submit_button("Confirm Quarantine")

            if submitted:
                if not chosen_reason_ids:
                    st.warning("Please choose at least one reason.")
                    return 
                
                if is_other_selected and not comment:
                    st.warning("You must provide details for 'Other'.")
                    return
                
                try:
                    user_id = st.session_state.get("user_id")
                    with get_session() as db:
                        mark_products_ad_hoc_quarantine(
                            db=db,
                            product_ids=selected_products,
                            user_id=user_id,
                            reason_ids=chosen_reason_ids,
                            comment=comment
                        )
                    st.success(f"{len(selected_products)} product(s) moved to quarantine.")
                    st.session_state["adhoc_results"] = []
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error("Failed to quarantine selected products.")
                    st.exception(e)