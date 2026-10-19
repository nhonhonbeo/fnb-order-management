"""Giao diện theo dõi và cập nhật tiến độ chế biến."""
import streamlit as st

from ui.presenters import order_views
from ui.state import status_label


def _refresh_order_status(order_id: str) -> None:
    st.session_state.orders = order_views(st.session_state.order_service.list_orders())


def render_kitchen_queue() -> None:
    queue = st.session_state.kitchen_service.list_requests()
    current = st.session_state.kitchen_service.current()
    active_queue = [request for request in queue if request.status != "DONE"]
    if not active_queue:
        st.info("Chưa có món nào chờ chế biến trong hàng đợi bếp.")
        return

    for index, request in enumerate(queue):
        if request.status == "DONE":
            continue
        is_current = (
            current is not None
            and current.order_id == request.order_id
            and current.item_code == request.item_code
        )
        order = st.session_state.order_service.get_order(request.order_id)
        cols = st.columns([3, 2, 2])
        cols[0].write(
            f"**{request.item_name} × {request.quantity}**  \n"
            f"`{request.order_id}` · **{order.table_id}**"
        )
        cols[1].write(status_label(request.status))

        if request.status == "NEW" and cols[2].button(
            "🔥 Bắt đầu nấu", key=f"cook_{index}", disabled=not is_current
        ):
            st.session_state.kitchen_service.start(request.order_id, request.item_code)
            _refresh_order_status(request.order_id)
            st.rerun()
        elif request.status == "COOKING" and cols[2].button(
            "✅ Đã hoàn thành", key=f"ready_{index}", disabled=not is_current
        ):
            st.session_state.kitchen_service.complete(request.order_id, request.item_code)
            _refresh_order_status(request.order_id)
            st.rerun()
        elif request.status == "READY":
            cols[2].success("Sẵn sàng phục vụ")