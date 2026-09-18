"""绿化废弃物处置记录校验规则。"""

from ..constants import WASTE_DISPOSAL_METHOD, WASTE_TYPE, WASTE_UNIT
from .common import PayloadValidator


def validate_waste_record(payload):
    return (
        PayloadValidator(payload)
        .integer("green_space_id", "来源绿地", required=True, min_value=1)
        .enum("waste_type", "废弃物类型", group=WASTE_TYPE, required=True)
        .date("generate_date", "产生日期", required=True)
        .number("quantity", "产生量", required=True, min_value=0.01, max_value=999999)
        .enum("unit", "计量单位", group=WASTE_UNIT, default="ton")
        .enum("disposal_method", "处置方式", group=WASTE_DISPOSAL_METHOD, required=True)
        .number("disposed_quantity", "处置量", min_value=0, max_value=999999, default=0)
        .date("disposed_date", "处置日期")
        .string("transport_vehicle", "运输车辆", max_length=64)
        .string("destination", "去向", max_length=128)
        .string("operator", "登记人", max_length=64)
        .text("remark", "备注", max_length=2000)
        .done()
    )
