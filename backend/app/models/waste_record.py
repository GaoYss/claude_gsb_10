"""绿化废弃物处置记录模型。"""

from ..constants import WASTE_DISPOSAL_METHOD, WASTE_TYPE, WASTE_UNIT
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class WasteRecord(TimestampMixin, db.Model):
    """绿化废弃物处置台账：修剪与清理废弃物的产生与处置去向登记。"""

    __tablename__ = "waste_record"

    id = db.Column(db.Integer, primary_key=True)
    record_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="CASCADE"), nullable=False, index=True
    )
    waste_type = db.Column(db.String(32), nullable=False, index=True)
    generate_date = db.Column(db.Date, nullable=False, index=True)
    quantity = db.Column(quantity_column(), nullable=False, default=0)
    unit = db.Column(db.String(16), nullable=False, default="ton")
    disposal_method = db.Column(db.String(16), nullable=False, index=True)
    disposed_quantity = db.Column(quantity_column(), nullable=False, default=0)
    disposed_date = db.Column(db.Date)
    transport_vehicle = db.Column(db.String(64))
    destination = db.Column(db.String(128))
    operator = db.Column(db.String(64))
    remark = db.Column(db.Text)

    green_space = db.relationship("GreenSpace", back_populates="waste_records", lazy="joined")

    @property
    def remaining_quantity(self):
        """产生量与处置量的差额（待处置量）。"""

        remaining = (self.quantity or 0) - (self.disposed_quantity or 0)
        return round(remaining, 2)

    @property
    def disposal_status(self):
        """处置进度：未处置 / 部分处置 / 已处置清。"""

        if (self.disposed_quantity or 0) <= 0:
            return "pending"
        if self.remaining_quantity > 0:
            return "partial"
        return "cleared"

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "record_no": self.record_no,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "waste_type": self.waste_type,
            "waste_type_label": WASTE_TYPE.label(self.waste_type),
            "generate_date": format_date(self.generate_date),
            "quantity": to_float(self.quantity),
            "unit": self.unit,
            "unit_label": WASTE_UNIT.label(self.unit),
            "disposal_method": self.disposal_method,
            "disposal_method_label": WASTE_DISPOSAL_METHOD.label(self.disposal_method),
            "disposed_quantity": to_float(self.disposed_quantity),
            "disposed_date": format_date(self.disposed_date),
            "remaining_quantity": to_float(self.remaining_quantity),
            "disposal_status": self.disposal_status,
            "transport_vehicle": self.transport_vehicle,
            "destination": self.destination,
            "operator": self.operator,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data
