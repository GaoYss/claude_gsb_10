"""绿化废弃物处置记录接口测试。"""

from datetime import date


def waste_payload(space_id, **overrides):
    payload = {
        "green_space_id": space_id,
        "waste_type": "branch",
        "generate_date": "2026-03-16",
        "quantity": 2.5,
        "unit": "ton",
        "disposal_method": "recycle",
        "disposed_quantity": 2.5,
        "disposed_date": "2026-03-18",
        "transport_vehicle": "浙A3D567",
        "destination": "绿源生物质燃料厂",
        "operator": "王海涛",
    }
    payload.update(overrides)
    return payload


def test_create_waste_record(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/waste-records", waste_payload(space.id)), 201)
    assert data["record_no"].startswith("WR-")
    assert data["quantity"] == 2.5
    assert data["disposed_quantity"] == 2.5
    assert data["remaining_quantity"] == 0
    assert data["disposal_status"] == "cleared"
    assert data["waste_type_label"] == "枝条枝干"
    assert data["disposal_method_label"] == "资源利用"
    assert data["unit_label"] == "吨"


def test_partial_disposal_shows_remaining(api, make_space):
    space = make_space()
    data = api.data(
        api.post("/api/v1/waste-records", waste_payload(space.id, disposed_quantity=1)), 201
    )
    assert data["remaining_quantity"] == 1.5
    assert data["disposal_status"] == "partial"


def test_disposed_quantity_cannot_exceed_generated(api, make_space):
    space = make_space()
    response = api.post("/api/v1/waste-records",
                        waste_payload(space.id, quantity=2, disposed_quantity=3))
    assert response.status_code == 422
    assert "处置量不能大于产生量" in response.get_json()["data"]["disposed_quantity"]


def test_transport_requires_vehicle_and_destination(api, make_space):
    space = make_space()
    response = api.post("/api/v1/waste-records",
                        waste_payload(space.id, disposal_method="transport",
                                      transport_vehicle=None, destination=None))
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "transport_vehicle" in details and "destination" in details


def test_mulch_does_not_require_vehicle(api, make_space):
    space = make_space()
    data = api.data(
        api.post("/api/v1/waste-records",
                 waste_payload(space.id, disposal_method="mulch",
                               transport_vehicle=None, destination="绿地内就地粉碎还田")),
        201,
    )
    assert data["disposal_method"] == "mulch"
    assert data["transport_vehicle"] is None


def test_generate_date_not_before_established(api, make_space):
    space = make_space()
    response = api.post("/api/v1/waste-records",
                        waste_payload(space.id, generate_date="2010-01-01"))
    assert response.status_code == 422
    assert "建成日期" in response.get_json()["data"]["generate_date"]


def test_disposed_date_not_before_generate_date(api, make_space):
    space = make_space()
    response = api.post("/api/v1/waste-records",
                        waste_payload(space.id, generate_date="2026-03-16",
                                      disposed_date="2026-03-15"))
    assert response.status_code == 422
    assert "处置日期不能早于产生日期" in response.get_json()["data"]["disposed_date"]


def test_enums_are_validated(api, make_space):
    space = make_space()
    response = api.post("/api/v1/waste-records",
                        waste_payload(space.id, waste_type="plastic", disposal_method="burn",
                                      unit="bag"))
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "waste_type" in details and "disposal_method" in details and "unit" in details


def test_update_recomputes_remaining(api, make_waste):
    waste = make_waste(quantity=4, disposed_quantity=1)
    assert waste.remaining_quantity == 3
    data = api.data(api.put(f"/api/v1/waste-records/{waste.id}", {
        "green_space_id": waste.green_space_id,
        "waste_type": "branch",
        "generate_date": "2026-03-16",
        "quantity": 4,
        "unit": "ton",
        "disposal_method": "recycle",
        "disposed_quantity": 4,
        "disposed_date": "2026-03-19",
    }))
    assert data["remaining_quantity"] == 0
    assert data["disposal_status"] == "cleared"
    assert data["record_no"] == waste.record_no


def test_update_to_transport_without_vehicle_is_rejected(api, make_waste):
    waste = make_waste(disposal_method="mulch", transport_vehicle=None, destination=None)
    response = api.put(f"/api/v1/waste-records/{waste.id}", {
        "green_space_id": waste.green_space_id,
        "waste_type": "branch",
        "generate_date": "2026-03-16",
        "quantity": 2.5,
        "unit": "ton",
        "disposal_method": "transport",
        "disposed_quantity": 2.5,
    })
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "transport_vehicle" in details and "destination" in details


def test_delete_waste_record(api, make_waste):
    waste = make_waste()
    api.data(api.delete(f"/api/v1/waste-records/{waste.id}"))
    assert api.get(f"/api/v1/waste-records/{waste.id}").status_code == 404


def test_list_filters(api, make_waste, make_space):
    space_a = make_space(name="甲绿地")
    space_b = make_space(name="乙绿地")
    waste = make_waste(space=space_a, waste_type="branch", disposal_method="recycle",
                       destination="绿源生物质燃料厂")
    make_waste(space=space_a, waste_type="leaf", disposal_method="transport",
               transport_vehicle="浙A8F219", destination="城北绿化废弃物消纳场")
    make_waste(space=space_b, waste_type="grass", disposal_method="mulch",
               transport_vehicle=None, destination="绿地内就地粉碎还田")

    data = api.data(api.get("/api/v1/waste-records", waste_type="branch"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["id"] == waste.id

    data = api.data(api.get("/api/v1/waste-records", disposal_method="transport"))
    assert data["meta"]["total"] == 1

    data = api.data(api.get("/api/v1/waste-records", keyword="绿源"))
    assert data["meta"]["total"] == 1

    data = api.data(api.get("/api/v1/waste-records", green_space_id=space_a.id))
    assert data["meta"]["total"] == 2

    data = api.data(api.get("/api/v1/waste-records", date_from="2026-04-01"))
    assert data["meta"]["total"] == 0


def test_summary_groups_by_unit_type_and_method(api, make_waste):
    make_waste(waste_type="branch", disposal_method="recycle", quantity=2.5, disposed_quantity=2)
    make_waste(waste_type="branch", disposal_method="mulch", quantity=1.5, disposed_quantity=1.5,
               transport_vehicle=None, destination=None)
    make_waste(waste_type="leaf", disposal_method="recycle", quantity=6, unit="cubic_meter",
               disposed_quantity=3)

    data = api.data(api.get("/api/v1/waste-records/summary"))
    assert data["total_count"] == 3

    by_unit = {row["unit"]: row for row in data["by_unit"]}
    assert by_unit["ton"]["generated"] == 4.0
    assert by_unit["ton"]["disposed"] == 3.5
    assert by_unit["ton"]["remaining"] == 0.5
    assert by_unit["cubic_meter"]["generated"] == 6.0
    assert by_unit["cubic_meter"]["remaining"] == 3.0

    by_type = {row["value"]: row for row in data["by_type"]}
    assert by_type["branch"]["count"] == 2
    assert by_type["leaf"]["count"] == 1

    by_method = {row["value"]: row for row in data["by_method"]}
    assert by_method["recycle"]["count"] == 2
    assert by_method["mulch"]["count"] == 1


def test_monthly_reconciliation_flags_mismatch(api, make_waste, make_space):
    space = make_space(name="对账绿地")
    # 3 月：产生 2.5 吨，全部处置 → 平账
    make_waste(space=space, generate_date=date(2026, 3, 5), quantity=2.5, disposed_quantity=2.5)
    # 3 月：产生 1 吨，未处置 → 与上一笔同月同单位合计后仍有差额
    make_waste(space=space, generate_date=date(2026, 3, 20), quantity=1, disposed_quantity=0,
               disposed_date=None)
    # 4 月：产生 6 立方米，部分处置 → 差额 2
    make_waste(space=space, generate_date=date(2026, 4, 2), quantity=6, unit="cubic_meter",
               disposed_quantity=4, disposed_date=date(2026, 4, 5))
    # 另一处绿地不参与对账绿地的汇总行
    make_waste(space=make_space(name="无关绿地"), generate_date=date(2026, 3, 10),
               quantity=3, disposed_quantity=3)

    data = api.data(api.get("/api/v1/waste-records/monthly", green_space_id=space.id))
    rows = {(row["month"], row["unit"]): row for row in data["rows"]}

    march_ton = rows[("2026-03", "ton")]
    assert march_ton["generated"] == 3.5
    assert march_ton["disposed"] == 2.5
    assert march_ton["remaining"] == 1.0
    assert march_ton["is_mismatched"] is True

    april_cubic = rows[("2026-04", "cubic_meter")]
    assert april_cubic["remaining"] == 2.0
    assert april_cubic["is_mismatched"] is True

    # 差额行单独提示，且只包含当前绿地的差额
    assert len(data["mismatches"]) == 2
    assert all(row["green_space_id"] == space.id for row in data["mismatches"])
    assert all(row["remaining"] != 0 for row in data["mismatches"])


def test_green_space_delete_protection_counts_waste(api, make_waste):
    waste = make_waste()
    space_id = waste.green_space_id

    response = api.delete(f"/api/v1/green-spaces/{space_id}")
    assert response.status_code == 409
    assert response.get_json()["data"]["waste_record"] == 1

    data = api.data(api.delete(f"/api/v1/green-spaces/{space_id}", force="true"))
    assert data["waste_record"] == 1
    assert api.get(f"/api/v1/waste-records/{waste.id}").status_code == 404
