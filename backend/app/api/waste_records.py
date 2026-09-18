"""绿化废弃物处置记录接口。"""

from flask import Blueprint, request

from ..schemas import validate_waste_record
from ..schemas.filters import waste_record_filters
from ..services import WasteRecordService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("waste_records", __name__)


@bp.get("/waste-records")
def list_waste_records():
    filters = waste_record_filters(request.args)
    page, page_size = parse_page_args()
    query = WasteRecordService.list_records(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = WasteRecordService.summary(filters)
    return ok(data)


@bp.get("/waste-records/summary")
def waste_record_summary():
    return ok(WasteRecordService.summary(waste_record_filters(request.args)))


@bp.get("/waste-records/monthly")
def waste_record_monthly():
    return ok(WasteRecordService.monthly(waste_record_filters(request.args)))


@bp.post("/waste-records")
def create_waste_record():
    payload = validate_waste_record(json_body())
    record = WasteRecordService.create(payload)
    return created(record.to_dict(detail=True), message="废弃物处置记录登记成功")


@bp.get("/waste-records/<int:record_id>")
def get_waste_record(record_id):
    return ok(WasteRecordService.detail(record_id))


@bp.put("/waste-records/<int:record_id>")
def update_waste_record(record_id):
    payload = validate_waste_record(json_body())
    record = WasteRecordService.update(record_id, payload)
    return ok(record.to_dict(detail=True), message="废弃物处置记录已更新")


@bp.delete("/waste-records/<int:record_id>")
def delete_waste_record(record_id):
    WasteRecordService.delete(record_id)
    return ok(None, message="废弃物处置记录已删除")
