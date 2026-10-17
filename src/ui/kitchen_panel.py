"""Giao diện theo dõi và cập nhật tiến độ chế biến."""
import streamlit as st

from ui.presenters import order_views
from ui.state import status_label


def _refresh_order_status(order_id: str) -> None:
    requests = [
        request
        for request in st.session_state.kitchen_service.list_requests()
        if request.order_id == order_id
    ]
    if requests and all(request.status == "READY" for request in requests):
        st.session_state.order_service.mark_completed(order_id)
    st.session_state.orders = order_views(st.session_state.order_service.list_orders())


def render_kitchen_queue() -> None:
    queue = st.session_state.kitchen_service.list_requests()
    active_queue = [request for request in queue if request.status != "DONE"]
    if not active_queue:
        st.info("Chưa có món nào chờ chế biến trong hàng đợi bếp.")
        return

    for index, request in enumerate(queue):
        if request.status == "DONE":
            continue
        order = st.session_state.order_service.get_order(request.order_id)
        cols = st.columns([3, 2, 2])
        cols[0].write(
            f"**{request.item_name} × {request.quantity}**  \n"
            f"`{request.order_id}` · **{order.table_id}**"
        )
        cols[1].write(status_label(request.status))

        if request.status == "NEW" and cols[2].button("🔥 Bắt đầu nấu", key=f"cook_{index}"):
            st.session_state.kitchen_service.update_status(
                request.order_id, request.item_code, "COOKING"
            )
            _refresh_order_status(request.order_id)
            st.rerun()
        elif request.status == "COOKING" and cols[2].button("✅ Đã hoàn thành", key=f"ready_{index}"):
            st.session_state.kitchen_service.update_status(
                request.order_id, request.item_code, "READY"
            )
            _refresh_order_status(request.order_id)
            st.rerun()
        elif request.status == "READY":
            cols[2].success("Sẵn sàng phục vụ")