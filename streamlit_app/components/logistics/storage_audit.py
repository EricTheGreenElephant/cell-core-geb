import streamlit as st
import time
from sqlalchemy.orm import Session
from db.orm_session import get_session
from models.production_models import ProductTracking, ProductStatuses
from models.lifecycle_stages_models import LifecycleStages
from models.storage_locations_models import StorageLocation
from models.product_quality_control_models import ProductQualityControl
from services.logistics_services import update_tracking_storage
from constants.storage_constants import STAGE_SHELF_RULES


def render_shelf_stage_mismatch_report():
    st.subheader("🔍 Shelf/Stage Mismatch Report")

    with get_session() as db:
        locations = db.query(StorageLocation).all()
        results = (
            db.query(
                ProductTracking.id,
                ProductStatuses.status_name,
                LifecycleStages.stage_code,
                StorageLocation.id.label("location_id"),
                StorageLocation.location_name,
                StorageLocation.description,                
            )
            .join(LifecycleStages, ProductTracking.current_stage_id == LifecycleStages.id)
            .join(StorageLocation, ProductTracking.location_id == StorageLocation.id)
            .outerjoin(ProductStatuses, ProductTracking.current_status_id == ProductStatuses.id)
            .all()
        )

    mismatches = []
    for row in results:
        allowed_keywords = STAGE_SHELF_RULES.get(row.stage_code, [])
        if not any(keyword in row.description for keyword in allowed_keywords):
            mismatches.append({
                "product_id": row.id,
                "status_name": row.status_name,
                "stage_code": row.stage_code,
                "location_id": row.location_id,
                "location_name": row.location_name,
                "description": row.description,
                "allowed_keywords": allowed_keywords,
            })

    if not mismatches:
        st.success("✅ All products are stored in appropriate locations.")
        return
    
    st.warning(f"{len(mismatches)} mismatches found.")
    st.markdown("---")

    for item in mismatches:
        with st.expander(f"{item['product_id']} - Shelf: {item['description']}"):
            st.write(f"**Current Status:** `{item['status_name']}`")
            st.write(f"**Current Stage:** `{item['stage_code']}`")
            st.write(f"**Current Shelf:** `{item['location_name']} - {item['description']}`")
            st.write(f"**Expected Shelf Area:** `{', '.join(item['allowed_keywords'])}`")

            valid_locations = [
                loc for loc in locations
                if any(keyword in loc.description for keyword in item["allowed_keywords"])
            ]

            if not valid_locations:
                st.error("No valid shelves found for this product's stage.")
                continue

            location_map = {
                f"{loc.location_name} - {loc.description}": loc.id
                for loc in valid_locations
            }

            shelf_label = st.selectbox(
                "Select Correct Shelf",
                options=list(location_map.keys()),
                key=f"shelf_select_{item['product_id']}"
            )

            reason = st.text_area("Reason for correction", key=f"reason_{item['product_id']}")

            if st.button(f"Submit Fix for {item['product_id']}", key=f"submit_{item['product_id']}"):
                if not reason.strip():
                    st.warning("Please provide a reason.")
                    return
                
                new_loc_id = location_map[shelf_label]
                if new_loc_id == item["location_id"]:
                    st.info("No shelf change selected.")
                    return
                
                try:
                    with get_session() as db:
                        update_tracking_storage(
                            db=db,
                            product_id=item["product_id"],
                            updates={
                                "location_id": (item["location_id"], new_loc_id)
                            },
                            reason=reason,
                            user_id=st.session_state["user_id"]
                        )
                    st.success(f"Shelf updated for {item['product_id']}.")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update shelf for {item['product_id']}.")
                    st.exception(e)
