"""绿化废弃物处置台账模型。"""

from decimal import Decimal

from ..constants import DISPOSAL_METHOD, GREEN_WASTE_TYPE, GREEN_WASTE_UNIT, WASTE_STATUS
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class GreenWaste(TimestampMixin, db.Model):
    """绿化废弃物处置记录：修剪、除草、清理等产生的废弃物及其处置去向。

    登记时先记录「产生」，处置完成后补录「处置」信息；未补录处置的记录
    视为暂存待处置，产生量与处置量的差额即待处置量。
    """

    __tablename__ = "green_waste"

    id = db.Column(db.Integer, primary_key=True)
    waste_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="CASCADE"), nullable=False, index=True
    )
    maintenance_record_id = db.Column(
        db.Integer,
        db.ForeignKey("maintenance_record.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # 产生侧
    waste_type = db.Column(db.String(32), nullable=False, index=True)
    quantity = db.Column(quantity_column(), nullable=False, default=0)
    unit = db.Column(db.String(16), nullable=False, default="ton")
    produce_date = db.Column(db.Date, nullable=False, index=True)
    source_detail = db.Column(db.String(128))
    operator = db.Column(db.String(64))
    remark = db.Column(db.Text)
    # 处置侧（补录前可整体为空）
    disposal_method = db.Column(db.String(16), index=True)
    disposal_quantity = db.Column(quantity_column())
    disposal_date = db.Column(db.Date, index=True)
    vehicle_no = db.Column(db.String(32))
    receiver = db.Column(db.String(96))
    disposal_note = db.Column(db.String(255))

    green_space = db.relationship("GreenSpace", back_populates="wastes", lazy="joined")
    record = db.relationship("MaintenanceRecord", back_populates="wastes")

    @property
    def is_disposed(self):
        return bool(self.disposal_method and self.disposal_date)

    @property
    def disposed_quantity(self):
        """已处置量：未补录处置为 0；补录处置但未填处置量时视为全部处置。"""

        if not self.is_disposed:
            return Decimal("0")
        if self.disposal_quantity is None:
            return Decimal(str(self.quantity or 0))
        return Decimal(str(self.disposal_quantity))

    @property
    def pending_quantity(self):
        pending = Decimal(str(self.quantity or 0)) - self.disposed_quantity
        return max(pending, Decimal("0"))

    def to_dict(self, detail=False):
        status = "disposed" if self.is_disposed else "pending"
        data = {
            "id": self.id,
            "waste_no": self.waste_no,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "maintenance_record_id": self.maintenance_record_id,
            "record": (
                {
                    "id": self.record.id,
                    "record_no": self.record.record_no,
                    "record_date": format_date(self.record.record_date),
                }
                if self.record
                else None
            ),
            "waste_type": self.waste_type,
            "waste_type_label": GREEN_WASTE_TYPE.label(self.waste_type),
            "quantity": to_float(self.quantity),
            "unit": self.unit,
            "unit_label": GREEN_WASTE_UNIT.label(self.unit),
            "produce_date": format_date(self.produce_date),
            "source_detail": self.source_detail,
            "operator": self.operator,
            "disposal_method": self.disposal_method,
            "disposal_method_label": (
                DISPOSAL_METHOD.label(self.disposal_method) if self.disposal_method else None
            ),
            "disposal_quantity": to_float(self.disposal_quantity) if self.is_disposed else None,
            "disposal_date": format_date(self.disposal_date),
            "vehicle_no": self.vehicle_no,
            "receiver": self.receiver,
            "disposal_note": self.disposal_note,
            "status": status,
            "status_label": WASTE_STATUS.label(status),
            "pending_quantity": to_float(self.pending_quantity),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data
