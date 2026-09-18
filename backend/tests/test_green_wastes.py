"""绿化废弃物处置台账接口与业务规则测试。"""

from datetime import date


def waste_payload(space_id, **overrides):
    payload = {
        "green_space_id": space_id,
        "waste_type": "branch",
        "quantity": 3.5,
        "unit": "ton",
        "produce_date": "2026-03-12",
        "source_detail": "行道树整形修剪枝条",
        "operator": "王海涛",
    }
    payload.update(overrides)
    return payload


def full_update_payload(waste, **overrides):
    """PUT 为全量校验，按已有记录构造完整请求体后再叠加处置字段。"""

    payload = waste_payload(
        waste.green_space_id,
        waste_type=waste.waste_type,
        quantity=float(waste.quantity),
        unit=waste.unit,
        produce_date=waste.produce_date.isoformat(),
        source_detail=waste.source_detail,
        operator=waste.operator,
    )
    payload.update(overrides)
    return payload


# ------------------------------------------------------------ 登记与补录
def test_create_waste_defaults_to_pending(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/green-wastes", waste_payload(space.id)), 201)
    assert data["waste_no"].startswith("WA-")
    assert data["status"] == "pending"
    assert data["status_label"] == "暂存待处置"
    assert data["quantity"] == 3.5
    assert data["pending_quantity"] == 3.5
    assert data["disposal_quantity"] is None
    assert data["disposal_method"] is None
    assert data["waste_type_label"] == "修剪枝条"
    assert data["unit_label"] == "吨"


def test_full_disposal_without_quantity_defaults_to_all(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/green-wastes", waste_payload(
        space.id,
        disposal_method="mulch",
        disposal_date="2026-03-13",
        receiver="就地处置",
        disposal_note="粉碎后覆盖树穴",
    )), 201)
    assert data["status"] == "disposed"
    assert data["disposal_quantity"] == 3.5
    assert data["pending_quantity"] == 0
    assert data["disposal_method_label"] == "粉碎还田"


def test_partial_disposal_leaves_pending_balance(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/green-wastes", waste_payload(
        space.id,
        disposal_method="offsite",
        disposal_quantity=2.0,
        disposal_date="2026-03-12",
        vehicle_no="浙A·3K21挂",
        receiver="杭州绿能环保发电厂",
    )), 201)
    assert data["status"] == "disposed"
    assert data["disposal_quantity"] == 2.0
    assert data["pending_quantity"] == 1.5


def test_record_disposal_later_via_update(api, make_waste):
    waste = make_waste()
    data = api.data(api.put(f"/api/v1/green-wastes/{waste.id}", full_update_payload(
        waste,
        disposal_method="recycle",
        disposal_date="2026-03-15",
        vehicle_no="浙A·8D65挂",
        receiver="余杭区园林废弃物资源化利用中心",
    )))
    assert data["status"] == "disposed"
    assert data["disposal_quantity"] == data["quantity"]
    assert data["pending_quantity"] == 0


# ------------------------------------------------------------ 校验
def test_disposal_quantity_cannot_exceed_produced(api, make_space):
    space = make_space()
    response = api.post("/api/v1/green-wastes", waste_payload(
        space.id,
        disposal_method="offsite",
        disposal_quantity=4,
        disposal_date="2026-03-12",
    ))
    assert response.status_code == 422
    assert "disposal_quantity" in response.get_json()["data"]


def test_method_requires_disposal_date(api, make_space):
    space = make_space()
    response = api.post("/api/v1/green-wastes", waste_payload(
        space.id, disposal_method="mulch"
    ))
    assert response.status_code == 422
    assert "disposal_date" in response.get_json()["data"]


def test_disposal_date_requires_method(api, make_space):
    space = make_space()
    response = api.post("/api/v1/green-wastes", waste_payload(
        space.id, disposal_date="2026-03-12"
    ))
    assert response.status_code == 422
    assert "disposal_method" in response.get_json()["data"]


def test_disposal_date_cannot_precede_produce_date(api, make_space):
    space = make_space()
    response = api.post("/api/v1/green-wastes", waste_payload(
        space.id, disposal_method="offsite", disposal_date="2026-03-10"
    ))
    assert response.status_code == 422
    assert "早于产生日期" in response.get_json()["data"]["disposal_date"]


def test_produce_date_cannot_precede_established_date(api, make_space):
    space = make_space(established_date=date(2020, 1, 1))
    response = api.post("/api/v1/green-wastes", waste_payload(
        space.id, produce_date="2019-12-31"
    ))
    assert response.status_code == 422
    assert "produce_date" in response.get_json()["data"]


def test_invalid_enum_and_missing_required(api, make_space):
    space = make_space()
    response = api.post("/api/v1/green-wastes", waste_payload(
        space.id, waste_type="hazardous", quantity=0
    ))
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "waste_type" in details and "quantity" in details


def test_record_must_belong_to_same_green_space(api, make_record, make_space):
    record = make_record()
    other_space = make_space(name="无关绿地")
    response = api.post("/api/v1/green-wastes",
                        waste_payload(other_space.id, maintenance_record_id=record.id))
    assert response.status_code == 422
    assert "不属于所选绿地" in response.get_json()["data"]["maintenance_record_id"]


# ------------------------------------------------------------ 汇总与差异
def test_summary_balances_produced_disposed_and_pending(api, make_waste):
    waste = make_waste(quantity=5, produce_date=date(2026, 3, 10))
    space = waste.green_space
    make_waste(space=space, quantity=3, produce_date=date(2026, 4, 2))
    # 第一条补录为全部处置
    api.data(api.put(f"/api/v1/green-wastes/{waste.id}", full_update_payload(
        waste,
        disposal_method="mulch",
        disposal_date="2026-03-11",
    )))

    data = api.data(api.get("/api/v1/green-wastes/summary", green_space_id=space.id))
    assert data["total_count"] == 2
    assert data["pending_count"] == 1
    assert data["total_quantity"] == 8.0
    assert data["total_disposed_quantity"] == 5.0
    assert data["total_pending_quantity"] == 3.0

    months = {row["month"]: row for row in data["by_month"]}
    assert months["2026-03"]["produced"] == 5.0
    assert months["2026-03"]["pending"] == 0
    assert months["2026-04"]["produced"] == 3.0
    assert months["2026-04"]["pending"] == 3.0
    assert [row["month"] for row in data["unbalanced"]["months"]] == ["2026-04"]

    spaces = data["by_green_space"]
    assert len(spaces) == 1
    assert spaces[0]["produced"] == 8.0
    assert spaces[0]["disposed"] == 5.0
    assert spaces[0]["pending"] == 3.0
    assert data["unbalanced"]["green_spaces"][0]["green_space_id"] == space.id

    methods = {row["value"]: row for row in data["by_method"]}
    assert methods["mulch"]["disposed"] == 5.0
    assert methods[None]["count"] == 1


def test_summary_respects_month_filter(api, make_waste):
    waste = make_waste(quantity=4, produce_date=date(2026, 3, 20))
    space = waste.green_space
    make_waste(space=space, quantity=6, produce_date=date(2026, 4, 5))

    data = api.data(api.get("/api/v1/green-wastes/summary", month="2026-04"))
    assert data["total_quantity"] == 6.0
    assert [row["month"] for row in data["by_month"]] == ["2026-04"]


# ------------------------------------------------------------ 列表与删除
def test_list_filters_by_green_space_status_and_method(api, make_waste):
    waste = make_waste(quantity=4, produce_date=date(2026, 3, 5))
    space = waste.green_space
    make_waste(space=space, quantity=2, produce_date=date(2026, 4, 8))
    api.data(api.put(f"/api/v1/green-wastes/{waste.id}", full_update_payload(
        waste,
        disposal_method="recycle",
        disposal_date="2026-03-06",
    )))

    pending = api.data(api.get("/api/v1/green-wastes", green_space_id=space.id, status="pending"))
    assert pending["meta"]["total"] == 1
    assert pending["items"][0]["status"] == "pending"

    disposed = api.data(api.get("/api/v1/green-wastes", green_space_id=space.id,
                                status="disposed", disposal_method="recycle"))
    assert disposed["meta"]["total"] == 1
    assert disposed["items"][0]["disposal_method"] == "recycle"

    march = api.data(api.get("/api/v1/green-wastes", green_space_id=space.id, month="2026-03"))
    assert march["meta"]["total"] == 1

    # 列表响应自带汇总
    assert pending["summary"]["total_pending_quantity"] == 2.0


def test_list_invalid_filter_values_are_ignored(api, make_waste):
    make_waste()
    data = api.data(api.get("/api/v1/green-wastes", status="unknown", month="bad"))
    assert data["meta"]["total"] == 1


def test_delete_waste(api, make_waste):
    waste = make_waste()
    api.delete(f"/api/v1/green-wastes/{waste.id}")
    assert api.get(f"/api/v1/green-wastes/{waste.id}").status_code == 404


def test_green_space_delete_protection_counts_waste(api, make_waste):
    waste = make_waste()
    response = api.delete(f"/api/v1/green-spaces/{waste.green_space_id}")
    assert response.status_code == 409
    assert response.get_json()["data"]["green_waste"] == 1

    api.data(api.delete(f"/api/v1/green-spaces/{waste.green_space_id}", force=True))
    assert api.get(f"/api/v1/green-wastes/{waste.id}").status_code == 404
