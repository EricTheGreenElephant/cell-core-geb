import streamlit as st
from sqlalchemy.orm import Session
from db.orm_session import get_session
from models.production_models import ProductTracking
from models.lifecycle_stages_models import LifecycleStages
from models.storage_locations_models import StorageLocation

# Mapping: stage_code → acceptable shelf keywords in storage_location.description
STAGE_SHELF_RULES = {
    "HarvestQCComplete": ["CellScrew; Inventory"],
    "InInterimStorage": ["CellScrew; Inventory"],
    "QMTreatmentApproval": ["Offsite"],
    "InTreatment": ["Offsite"],
    "PostTreatmentQC": ["CellScrew; Inventory", "CellScrew; B-Ware"],
    "PostTreatmentStorage": ["CellScrew; Inventory", "CellScrew; B-Ware"],
    "QMSalesApproval": ["CellScrew; Sales"],
    "Quarantine": ["CellScrew; Quarantine"],
    "Disposed": ["Disposed Product", "Waste"],
    "Internal Use": ["Internal Use"],  # If you later create shelves like "CellScrew; Internal Use"
}

def render_shelf_stage_mismatch_report():
    st.subheader("🔍 Shelf/Stage Mismatch Report")

    with get_session() as db:
        results = (
            db.query(
                ProductTracking.tracking_id,
                LifecycleStages.stage_code,
                StorageLocation.location_name,
                StorageLocation.description,
            )
            .join(LifecycleStages, ProductTracking.current_stage_id == LifecycleStages.id)
            .join(StorageLocation, ProductTracking.location_id == StorageLocation.id)
            .all()
        )

    mismatches = []
    for row in results:
        allowed_keywords = STAGE_SHELF_RULES.get(row.stage_code, [])
        if not any(keyword in row.description for keyword in allowed_keywords):
            mismatches.append({
                "Tracking ID": row.tracking_id,
                "Stage": row.stage_code,
                "Shelf": row.location_name,
                "Shelf Description": row.description,
                "Expected Shelf Keywords": ", ".join(allowed_keywords),
            })

    if not mismatches:
        st.success("✅ All products are stored in appropriate locations.")
    else:
        st.warning(f"⚠️ {len(mismatches)} mismatches found.")
        st.dataframe(mismatches, use_container_width=True)