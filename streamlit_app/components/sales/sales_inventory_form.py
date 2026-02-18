import streamlit as st
from services.sales_services import get_sales_ready_inventory
from db.orm_session import get_session


def render_sales_tab():
    st.subheader("Sales-Ready Inventory")

    with get_session() as db:
        rows = get_sales_ready_inventory(db)

    if not rows:
        st.info("No products currently available for sale.")
        return

    sku_options = ["All"] + sorted({r.get("sku") for r in rows if r.get("sku")})
    status_options = ["All"] + sorted({r.get("product_status") for r in rows if r.get("product_status")})
    printed_by_options = ["All"] + sorted({r.get("printed_by") for r in rows if r.get("printed_by")})

    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    with c1:
        sku_filter = st.selectbox("SKU", sku_options, index=0)
    with c2:
        status_filter = st.selectbox("Status", status_options, index=0)
    with c3:
        printed_by_filter = st.selectbox("Printed by", printed_by_options, index=0)
    with c4:
        show_lots = st.toggle("Show lots", value=True)

    def _matches(r: dict) -> bool:
        if sku_filter != "All" and r.get("sku") != sku_filter:
            return False
        if status_filter != "All" and r.get("product_status") != status_filter:
            return False 
        if printed_by_filter != "All" and r.get("printed_by") != printed_by_filter:
            return False 
        return True
    
    filtered_rows = [r for r in rows if _matches(r)]

    if not filtered_rows:
        st.warning("No results match the current filters.")
        return 
    
    summary = {}
    for r in filtered_rows:
        sku = r.get("sku")
        sku_name = r.get("sku_name")
        key = (sku, sku_name)
        summary[key] = summary.get(key, 0) + 1
    
    summary_rows = [
        {"sku": sku, "sku_name": sku_name, "available_qty": count}
        for (sku, sku_name), count in summary.items()
    ]
    summary_rows.sort(key=lambda x: (x["sku"] or ""))

    st.markdown("#### Summary by SKU")
    st.dataframe(summary_rows, width="stretch", hide_index=True)

    if show_lots:
        st.markdown("#### Lots / Individual Items")

        detail = []
        for r in filtered_rows:
            detail.append({
                "sku": r.get("sku"),
                "sku_name": r.get("sku_name"),
                "lot_number": r.get("lot_number"),
                "product_status": r.get("product_status"),
                "current_stage": r.get("current_stage"),
                "last_updated_at": r.get("last_updated_at"),
                "printed_by": r.get("printed_by"),
            })
        
        st.dataframe(detail, width="stretch", hide_index=True)

        try:
            import pandas as pd
            df = pd.DataFrame(detail)
            st.download_button(
                "Download CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name="sales_inventory.csv",
                mime="text/csv",
                type="primary"
            )
        except Exception:
            pass