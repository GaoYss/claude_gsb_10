"""绿化废弃物处置记录校验规则。"""

from ..constants import DISPOSAL_METHOD, GREEN_WASTE_TYPE, GREEN_WASTE_UNIT
from .common import PayloadValidator


def validate_green_waste(payload):
    return (
        PayloadValidator(payload)
        # 产生信息
        .integer("green_space_id", "来源绿地", required=True, min_value=1)
        .integer("maintenance_record_id", "关联养护记录", min_value=1)
        .enum("waste_type", "废弃物类型", group=GREEN_WASTE_TYPE, required=True)
        .number("quantity", "产生数量", required=True, min_value=0.01, max_value=999999)
        .enum("unit", "计量单位", group=GREEN_WASTE_UNIT, default="ton")
        .date("produce_date", "产生日期", required=True)
        .string("source_detail", "产生环节", max_length=128)
        .string("operator", "登记人", max_length=64)
        # 处置信息（可整体留空，补录时填写）
        .enum("disposal_method", "处置方式", group=DISPOSAL_METHOD)
        .number("disposal_quantity", "处置数量", min_value=0, max_value=999999)
        .date("disposal_date", "处置日期")
        .string("vehicle_no", "运输车辆", max_length=32)
        .string("receiver", "接收/去向单位", max_length=96)
        .string("disposal_note", "去向说明", max_length=255)
        .text("remark", "备注", max_length=2000)
        .done()
    )
