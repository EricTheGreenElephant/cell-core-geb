SHELF_OPTIONS_BY_RESULT = {
    "A-Ware": {
        "Post-Harvest QC": ["CellScrew; Inventory"],
        "Post-Treatment QC": ["CellScrew; Sales"]
    },
    "B-Ware": {
        "Post-Harvest QC": ["CellScrew; B-Ware"],
        "Post-Treatment QC": ["CellScrew; Internal Use"]
    },
    "In Quarantine": {
        "Post-Harvest QC": ["CellScrew; Quarantine"],
        "Post-Treatment QC": ["CellScrew; Quarantine"]
    },
    "Waste": {
        "Post-Harvest QC": ["Disposed Product"],
        "Post-Treatment QC": ["Disposed Product"]
    }
}

NEXT_STAGE_BY_RESULT = {
    "A-Ware": {
        "Post-Harvest QC": "InInterimStorage",
        "Post-Treatment QC": "PostTreatmentStorage"
    },
    "B-Ware": {
        "Post-Harvest QC": "InInterimStorage",
        "Post-Treatment QC": "PostTreatmentStorage"
    },
    "In Quarantine": {
        "Post-Harvest QC": "Quarantine",
        "Post-Treatment QC": "Quarantine"
    },
    "Waste": {
        "Post-Harvest QC": "Disposed",
        "Post-Treatment QC": "Disposed"
    }
}

# Mapping: stage_code → acceptable shelf keywords in storage_location.description
STAGE_SHELF_RULES = {
    "HarvestQCComplete": ["CellScrew; Inventory", "CellScrew; B-Ware"],
    "InInterimStorage": ["CellScrew; Inventory", "CellScrew; B-Ware"],
    "QMTreatmentApproval": ["CellScrew; Inventory", "CellScrew; B-Ware"],
    "InTreatment": ["Offsite", "Treatment/Partner/Customer"],
    "PostTreatmentQC": ["CellScrew; Sales", "Internal Use", "CellScrew; B-Ware"],
    "PostTreatmentStorage": ["CellScrew; Sales", "Internal Use", "CellScrew; B-Ware"],
    "QMSalesApproval": ["CellScrew; Sales"],
    "Quarantine": ["CellScrew; Quarantine"],
    "Disposed": ["Disposed Product", "Waste"],
    "Internal Use": ["Internal Use"],  # If you later create shelves like "CellScrew; Internal Use"
}