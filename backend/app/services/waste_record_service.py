"""绿化废弃物处置记录业务逻辑。"""

from collections import defaultdict

from sqlalchemy import func, or_

from ..constants import ENUM_GROUPS
from ..errors import ValidationError
from ..extensions import db
from ..models import GreenSpace, WasteRecord
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix


class WasteRecordService(BaseService):
    """绿化废弃物处置台账：登记产生量与处置量，按月与绿地对账。"""

    model = WasteRecord
    label = "废弃物处置记录"
    code_field = "record_no"
    code_width = 3

    SORTABLE = {
        "generate_date": WasteRecord.generate_date,
        "quantity": WasteRecord.quantity,
        "disposed_quantity": WasteRecord.disposed_quantity,
        "created_at": WasteRecord.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("WR")

    # ------------------------------------------------------------ 校验与派生
    @classmethod
    def prepare_instance(cls, instance, payload):
        green_space_id = payload.get("green_space_id", instance.green_space_id)
        space = db.session.get(GreenSpace, green_space_id) if green_space_id else None
        if space is None:
            raise ValidationError("登记失败", details={"green_space_id": "所选绿地不存在"})

        generate_date = payload.get("generate_date", instance.generate_date)
        if generate_date and space.established_date and generate_date < space.established_date:
            raise ValidationError(
                "登记失败",
                details={
                    "generate_date": f"产生日期不能早于该绿地建成日期 {space.established_date}"
                },
            )

        quantity = payload.get("quantity", instance.quantity)
        disposed = payload.get("disposed_quantity", instance.disposed_quantity)
        if quantity is not None and disposed is not None and float(disposed) > float(quantity):
            raise ValidationError(
                "登记失败", details={"disposed_quantity": "处置量不能大于产生量"}
            )

        disposed_date = payload.get("disposed_date", instance.disposed_date)
        if disposed_date and generate_date and disposed_date < generate_date:
            raise ValidationError(
                "登记失败", details={"disposed_date": "处置日期不能早于产生日期"}
            )

        method = payload.get("disposal_method", instance.disposal_method)
        if method == "transport":
            vehicle = payload.get("transport_vehicle", instance.transport_vehicle)
            destination = payload.get("destination", instance.destination)
            details = {}
            if not vehicle or not str(vehicle).strip():
                details["transport_vehicle"] = "外运消纳时需填写运输车辆"
            if not destination or not str(destination).strip():
                details["destination"] = "外运消纳时需填写去向"
            if details:
                raise ValidationError("登记失败", details=details)

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("green_space_id"):
            query = query.filter(WasteRecord.green_space_id == filters["green_space_id"])
        if filters.get("waste_type"):
            query = query.filter(WasteRecord.waste_type == filters["waste_type"])
        if filters.get("disposal_method"):
            query = query.filter(WasteRecord.disposal_method == filters["disposal_method"])
        if filters.get("date_from"):
            query = query.filter(WasteRecord.generate_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(WasteRecord.generate_date <= filters["date_to"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    WasteRecord.record_no.like(like),
                    WasteRecord.transport_vehicle.like(like),
                    WasteRecord.destination.like(like),
                    WasteRecord.operator.like(like),
                )
            )
        return query

    @classmethod
    def list_records(cls, filters, args):
        query = cls._apply_filters(db.session.query(WasteRecord), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, WasteRecord.generate_date.desc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    # ------------------------------------------------------------ 汇总
    @classmethod
    def summary(cls, filters):
        """汇总：按计量单位核算产生/处置/待处置量，按类型与处置方式统计分布。"""

        def _group(column, group_key):
            rows = (
                cls._apply_filters(
                    db.session.query(
                        column,
                        func.count(WasteRecord.id),
                        func.coalesce(func.sum(WasteRecord.quantity), 0),
                        func.coalesce(func.sum(WasteRecord.disposed_quantity), 0),
                    ),
                    filters,
                )
                .group_by(column)
                .all()
            )
            return [
                {
                    "value": value,
                    "label": ENUM_GROUPS[group_key].label(value),
                    "count": count,
                    "generated": to_float(generated) or 0,
                    "disposed": to_float(disposed) or 0,
                }
                for value, count, generated, disposed in rows
            ]

        total_count = cls._apply_filters(
            db.session.query(func.count(WasteRecord.id)), filters
        ).scalar() or 0

        unit_rows = (
            cls._apply_filters(
                db.session.query(
                    WasteRecord.unit,
                    func.coalesce(func.sum(WasteRecord.quantity), 0),
                    func.coalesce(func.sum(WasteRecord.disposed_quantity), 0),
                ),
                filters,
            )
            .group_by(WasteRecord.unit)
            .all()
        )
        by_unit = [
            {
                "unit": unit,
                "unit_label": ENUM_GROUPS["waste_unit"].label(unit),
                "generated": to_float(generated) or 0,
                "disposed": to_float(disposed) or 0,
                "remaining": round((to_float(generated) or 0) - (to_float(disposed) or 0), 2),
            }
            for unit, generated, disposed in unit_rows
        ]

        return {
            "total_count": total_count,
            "by_unit": by_unit,
            "by_type": _group(WasteRecord.waste_type, "waste_type"),
            "by_method": _group(WasteRecord.disposal_method, "waste_disposal_method"),
        }

    @classmethod
    def monthly(cls, filters):
        """按产生月份 × 绿地 × 计量单位汇总产生量与处置量。

        差额（产生量 − 处置量）不为零的行单独放入 mismatches 返回，
        对应台账「产生量与处置量对不上」的提示。
        """

        rows = (
            cls._apply_filters(
                db.session.query(
                    WasteRecord.green_space_id,
                    WasteRecord.unit,
                    WasteRecord.generate_date,
                    func.coalesce(func.sum(WasteRecord.quantity), 0),
                    func.coalesce(func.sum(WasteRecord.disposed_quantity), 0),
                ),
                filters,
            )
            .group_by(WasteRecord.green_space_id, WasteRecord.unit, WasteRecord.generate_date)
            .all()
        )

        buckets = defaultdict(lambda: [0.0, 0.0])
        for green_space_id, unit, generate_date, generated, disposed in rows:
            key = (f"{generate_date:%Y-%m}", green_space_id, unit)
            buckets[key][0] += to_float(generated) or 0
            buckets[key][1] += to_float(disposed) or 0

        space_ids = {key[1] for key in buckets}
        spaces = {
            space.id: space.to_brief()
            for space in db.session.query(GreenSpace).filter(GreenSpace.id.in_(space_ids)).all()
        } if space_ids else {}

        monthly_rows = []
        for (month, green_space_id, unit), (generated, disposed) in buckets.items():
            remaining = round(generated - disposed, 2)
            monthly_rows.append({
                "month": month,
                "green_space_id": green_space_id,
                "green_space": spaces.get(green_space_id),
                "unit": unit,
                "unit_label": ENUM_GROUPS["waste_unit"].label(unit),
                "generated": round(generated, 2),
                "disposed": round(disposed, 2),
                "remaining": remaining,
                "is_mismatched": remaining != 0,
            })
        monthly_rows.sort(
            key=lambda row: (row["month"], row["green_space_id"], row["unit"]), reverse=True
        )

        return {
            "rows": monthly_rows,
            "mismatches": [row for row in monthly_rows if row["is_mismatched"]],
        }
