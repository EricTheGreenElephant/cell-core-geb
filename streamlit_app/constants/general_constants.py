COLOR_MAP = {
    "Passed": "green",
    "B-Ware": "orange",
    "Quarantine": "blue",
    "Waste": "red"
}

VALID_OUTCOMES = {"B-Ware", "Quarantine", "Waste", None}

RESOLUTION_OPTIONS = {
    "Approve as A-Ware": "Passed",
    "Approve as B-Ware": "B-Ware",
    "Mark as Waste": "Waste",
    "Under Investigation": "Investigation",
}

INVESTIGATION_RESOLUTION_OPTIONS = {
    "Approve as A-Ware": "Passed",
    "Approve as B-Ware": "B-Ware",
    "Mark as Waste": "Waste",
}