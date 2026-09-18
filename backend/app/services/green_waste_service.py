"""绿化废弃物处置业务逻辑。"""

import calendar
from decimal import Decimal

from sqlalchemy import or_

from ..constants import DISPOSAL_METHOD, GREEN_WASTE_TYPE
from ..errors import ValidationError
from ..extensions import db
from ..models import GreenSpace, GreenWaste, MaintenanceRecord
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix

ZERO = Decimal("0")


def _q(value):
    return Decimal(str(value or 0))


class GreenWasteService(BaseService):
    """废弃物处置记录：登记产生量，补录处置去向，并核算待处置差异。"""

    model = GreenWaste
    label = "废弃物处置记录"
    code_field = "waste_no"
    code_width = 3

    SORTABLE = {
        "produce_date": GreenWaste.produce_date,
        "quantity": GreenWaste.quantity,
        "created_at": GreenWaste.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("WA")

    # ------------------------------------------------------------ 校验与派生
    @classmethod
    def prepare_instance(cls, instance, payload):
        errors = {}

        green_space_id = payload.get("green_space_id", instance.green_space_id)
        space = db.session.get(GreenSpace, green_space_id) if green_space_id else None
        if space is None:
            raise ValidationError("登记失败", details={"green_space_id": "所选绿地不存在"})

        record_id = payload.get("maintenance_record_id", instance.maintenance_record_id)
        if record_id:
            record = db.session.get(MaintenanceRecord, record_id)
            if record is None:
                errors["maintenance_record_id"] = "关联的养护记录不存在"
            elif record.green_space_id != space.id:
                errors["maintenance_record_id"] = "关联的养护记录不属于所选绿地"

        produce_date = payload.get("produce_date", instance.produce_date)
        if produce_date and space.established_date and produce_date < space.established_date:
            errors["produce_date"] = f"产生日期不能早于该绿地建成日期 {space.established_date}"

        quantity = _q(payload.get("quantity", instance.quantity))
        method = payload.get("disposal_method", instance.disposal_method)
        disposal_date = payload.get("disposal_date", instance.disposal_date)
        disposal_quantity = payload.get("disposal_quantity", instance.disposal_quantity)

        # 处置方式与处置日期必须成对补全
        if bool(method) != bool(disposal_date):
            if not method:
                errors["disposal_method"] = "已填写处置日期，请同时选择处置方式"
            if not disposal_date:
                errors["disposal_date"] = "已选择处置方式，请同时填写处置日期"

        if disposal_date and produce_date and disposal_date < produce_date:
            errors["disposal_date"] = "处置日期不能早于产生日期"

        if disposal_quantity is not None and _q(disposal_quantity) > quantity:
            errors["disposal_quantity"] = "处置数量不能大于产生数量"

        if errors:
            raise ValidationError("登记失败", details=errors)

    @classmethod
    def apply_derived(cls, instance):
        """已补录处置但未填处置量时，默认全部处置。"""

        if instance.is_disposed and instance.disposal_quantity is None:
            instance.disposal_quantity = instance.quantity

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("green_space_id"):
            query = query.filter(GreenWaste.green_space_id == filters["green_space_id"])
        if filters.get("maintenance_record_id"):
            query = query.filter(GreenWaste.maintenance_record_id == filters["maintenance_record_id"])
        if filters.get("waste_type"):
            query = query.filter(GreenWaste.waste_type == filters["waste_type"])
        if filters.get("disposal_method"):
            query = query.filter(GreenWaste.disposal_method == filters["disposal_method"])
        if filters.get("status") == "disposed":
            query = query.filter(
                GreenWaste.disposal_method.isnot(None),
                GreenWaste.disposal_date.isnot(None),
            )
        elif filters.get("status") == "pending":
            query = query.filter(
                or_(GreenWaste.disposal_method.is_(None), GreenWaste.disposal_date.is_(None))
            )
        if filters.get("date_from"):
            query = query.filter(GreenWaste.produce_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(GreenWaste.produce_date <= filters["date_to"])
        if filters.get("month"):
            year, month = (int(part) for part in filters["month"].split("-"))
            last_day = calendar.monthrange(year, month)[1]
            query = query.filter(
                GreenWaste.produce_date >= f"{year:04d}-{month:02d}-01",
                GreenWaste.produce_date <= f"{year:04d}-{month:02d}-{last_day:02d}",
            )
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    GreenWaste.waste_no.like(like),
                    GreenWaste.source_detail.like(like),
                    GreenWaste.vehicle_no.like(like),
                    GreenWaste.receiver.like(like),
                    GreenWaste.disposal_note.like(like),
                    GreenWaste.operator.like(like),
                )
            )
        return query

    @classmethod
    def list_wastes(cls, filters, args):
        query = cls._apply_filters(db.session.query(GreenWaste), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, GreenWaste.produce_date.desc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    # ------------------------------------------------------------ 汇总
    @classmethod
    def _rows(cls, filters):
        """取出当前筛选范围内的全部记录用于 Python 侧归并（数据量有限，避免方言日期函数）。"""

        return (
            cls._apply_filters(db.session.query(GreenWaste), filters)
            .order_by(GreenWaste.produce_date.asc(), GreenWaste.id.asc())
            .all()
        )

    @staticmethod
    def _blank_bucket():
        return {"produced": ZERO, "disposed": ZERO, "count": 0}

    @classmethod
    def summary(cls, filters):
        rows = cls._rows(filters)

        total_produced = ZERO
        total_disposed = ZERO
        pending_count = 0
        by_type = {}
        by_method = {}
        by_month = {}
        by_space = {}

        for waste in rows:
            produced = _q(waste.quantity)
            disposed = produced - waste.pending_quantity
            month_key = waste.produce_date.strftime("%Y-%m")

            total_produced += produced
            total_disposed += disposed
            if not waste.is_disposed:
                pending_count += 1

            type_bucket = by_type.setdefault(waste.waste_type, cls._blank_bucket())
            type_bucket["produced"] += produced
            type_bucket["count"] += 1

            method_key = waste.disposal_method if waste.is_disposed else None
            method_bucket = by_method.setdefault(method_key, cls._blank_bucket())
            method_bucket["disposed"] += disposed
            method_bucket["count"] += 1

            month_bucket = by_month.setdefault(month_key, cls._blank_bucket())
            month_bucket["produced"] += produced
            month_bucket["disposed"] += disposed
            month_bucket["count"] += 1

            space = waste.green_space
            space_key = space.id if space else None
            space_bucket = by_space.setdefault(space_key, {
                "green_space_id": space_key,
                "green_space_name": space.name if space else "（已删除绿地）",
                "code": space.code if space else None,
                "district": space.district if space else None,
                "produced": ZERO,
                "disposed": ZERO,
                "count": 0,
            })
            space_bucket["produced"] += produced
            space_bucket["disposed"] += disposed
            space_bucket["count"] += 1

        def _finish(bucket):
            produced = bucket["produced"]
            disposed = bucket["disposed"]
            return {
                "produced": to_float(produced) or 0,
                "disposed": to_float(disposed) or 0,
                "pending": to_float(produced - disposed) or 0,
                "count": bucket["count"],
            }

        type_rows = [
            {
                "value": value,
                "label": GREEN_WASTE_TYPE.label(value),
                **_finish(bucket),
            }
            for value, bucket in by_type.items()
        ]
        type_rows.sort(key=lambda item: item["produced"], reverse=True)

        method_rows = [
            {
                "value": value,
                "label": DISPOSAL_METHOD.label(value) if value else "暂存待处置",
                "disposed": to_float(bucket["disposed"]) or 0,
                "count": bucket["count"],
            }
            for value, bucket in by_method.items()
        ]
        method_rows.sort(key=lambda item: (item["value"] is None, -item["disposed"]))

        month_rows = []
        unbalanced_months = []
        for month_key in sorted(by_month):
            item = {"month": month_key, **_finish(by_month[month_key])}
            month_rows.append(item)
            if item["pending"] > 0:
                unbalanced_months.append(item)

        space_rows = []
        unbalanced_spaces = []
        for bucket in by_space.values():
            item = {
                "green_space_id": bucket["green_space_id"],
                "green_space_name": bucket["green_space_name"],
                "code": bucket["code"],
                "district": bucket["district"],
                **_finish(bucket),
            }
            space_rows.append(item)
            if item["pending"] > 0:
                unbalanced_spaces.append(item)
        space_rows.sort(key=lambda item: item["pending"], reverse=True)
        unbalanced_spaces.sort(key=lambda item: item["pending"], reverse=True)

        total_pending = total_produced - total_disposed
        return {
            "total_count": len(rows),
            "pending_count": pending_count,
            "total_quantity": to_float(total_produced) or 0,
            "total_disposed_quantity": to_float(total_disposed) or 0,
            "total_pending_quantity": to_float(total_pending) or 0,
            "by_type": type_rows,
            "by_method": method_rows,
            "by_month": month_rows,
            "by_green_space": space_rows,
            "unbalanced": {
                "months": unbalanced_months,
                "green_spaces": unbalanced_spaces,
            },
        }
