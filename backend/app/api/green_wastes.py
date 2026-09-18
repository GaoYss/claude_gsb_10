"""绿化废弃物处置台账接口。"""

from flask import Blueprint, request

from ..schemas import validate_green_waste, waste_filters
from ..services import GreenWasteService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("green_wastes", __name__)


@bp.get("/green-wastes")
def list_wastes():
    filters = waste_filters(request.args)
    page, page_size = parse_page_args()
    query = GreenWasteService.list_wastes(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = GreenWasteService.summary(filters)
    return ok(data)


@bp.get("/green-wastes/summary")
def waste_summary():
    return ok(GreenWasteService.summary(waste_filters(request.args)))


@bp.post("/green-wastes")
def create_waste():
    payload = validate_green_waste(json_body())
    waste = GreenWasteService.create(payload)
    return created(waste.to_dict(detail=True), message="废弃物处置记录登记成功")


@bp.get("/green-wastes/<int:waste_id>")
def get_waste(waste_id):
    return ok(GreenWasteService.detail(waste_id))


@bp.put("/green-wastes/<int:waste_id>")
def update_waste(waste_id):
    payload = validate_green_waste(json_body())
    waste = GreenWasteService.update(waste_id, payload)
    return ok(waste.to_dict(detail=True), message="废弃物处置记录已更新")


@bp.delete("/green-wastes/<int:waste_id>")
def delete_waste(waste_id):
    GreenWasteService.delete(waste_id)
    return ok(None, message="废弃物处置记录已删除")
