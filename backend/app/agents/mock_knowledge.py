"""Keyword-based knowledge used ONLY in mock mode (no LLM API key).

This is deliberately simple, transparent heuristics, not AI. It lets the whole
workflow run end-to-end for development and demos, and every output produced
from it is labelled `is_mock`.
"""

import re

ROLE_PATTERNS: list[tuple[str, str]] = [
    (r"\bemployees?\b", "Employee"),
    (r"\bmanagers?\b", "Manager"),
    (r"\bhr\b|\bhuman resources\b", "HR Administrator"),
    (r"\badmin(istrator)?s?\b|\badministration\b", "Administrator"),
    (r"\bcustomers?\b", "Customer"),
    (r"\bsuppliers?\b|\bvendors?\b", "Supplier"),
    (r"\bwarehouse\b|\bstock(keeper)?\b|\binventory\b", "Inventory Clerk"),
    (r"\bstudents?\b", "Student"),
    (r"\bteachers?\b|\binstructors?\b", "Teacher"),
    (r"\bpatients?\b", "Patient"),
    (r"\bdoctors?\b", "Doctor"),
]


def _fields(*specs: tuple[str, str, bool, str]) -> list[dict]:
    return [
        {"name": n, "type": t, "required": r, "description": d} for n, t, r, d in specs
    ]


# (regex, entity spec, only-if-no-entity-named) — order matters.
ENTITY_CATALOGUE: list[tuple[str, dict, str | None]] = [
    (r"\bemployees?\b|\bstaff\b", {
        "name": "Employee", "description": "A person employed by the organisation.",
        "fields": _fields(
            ("full_name", "str", True, "Employee full name"),
            ("email", "str", True, "Work email address"),
            ("department", "str", True, "Department name"),
            ("job_title", "str", False, "Job title"),
            ("manager_id", "int", False, "Employee id of the line manager"),
        ),
        "relationships": ["Employee (manager) 1..* Employee"],
    }, None),
    (r"\bleave\b", {
        "name": "LeaveRequest", "description": "An employee's application for leave.",
        "fields": _fields(
            ("employee_id", "int", True, "Applicant"),
            ("leave_type", "str", True, "e.g. annual, sick, unpaid"),
            ("start_date", "date", True, "First day of leave"),
            ("end_date", "date", True, "Last day of leave"),
            ("reason", "str", False, "Reason given by the employee"),
            ("status", "str", True, "pending / approved / rejected"),
        ),
        "relationships": ["Employee 1..* LeaveRequest"],
    }, None),
    (r"\bbalances?\b", {
        "name": "LeaveBalance", "description": "Remaining leave entitlement per type.",
        "fields": _fields(
            ("employee_id", "int", True, "Owner of the balance"),
            ("leave_type", "str", True, "Leave type"),
            ("total_days", "float", True, "Annual entitlement in days"),
            ("used_days", "float", True, "Days already taken"),
        ),
        "relationships": ["Employee 1..* LeaveBalance"],
    }, None),
    (r"\battendance\b", {
        "name": "AttendanceRecord", "description": "Daily attendance entry.",
        "fields": _fields(
            ("employee_id", "int", True, "Employee"),
            ("work_date", "date", True, "Date"),
            ("attendance_status", "str", True, "present / absent / on_leave"),
            ("hours_worked", "float", False, "Hours worked"),
        ),
        "relationships": ["Employee 1..* AttendanceRecord"],
    }, None),
    (r"\bproducts?\b|\binventory\b|\bitems?\b", {
        "name": "Product", "description": "A product held in inventory.",
        "fields": _fields(
            ("product_name", "str", True, "Product name"),
            ("sku", "str", True, "Stock keeping unit"),
            ("category", "str", False, "Product category"),
            ("unit_price", "float", True, "Unit price"),
            ("reorder_level", "int", True, "Quantity that triggers reordering"),
        ),
        "relationships": [],
    }, None),
    (r"\bsuppliers?\b|\bvendors?\b", {
        "name": "Supplier", "description": "A company that supplies products.",
        "fields": _fields(
            ("company_name", "str", True, "Supplier name"),
            ("contact_email", "str", True, "Contact email"),
            ("phone", "str", False, "Phone number"),
        ),
        "relationships": ["Supplier 1..* PurchaseOrder"],
    }, None),
    (r"\bwarehouses?\b|\blocations?\b", {
        "name": "Warehouse", "description": "A storage location.",
        "fields": _fields(
            ("warehouse_name", "str", True, "Warehouse name"),
            ("address", "str", True, "Address"),
        ),
        "relationships": ["Warehouse 1..* StockLevel"],
    }, None),
    (r"\bstock\b|\binventory levels?\b", {
        "name": "StockLevel", "description": "Quantity of a product at a warehouse.",
        "fields": _fields(
            ("product_id", "int", True, "Product"),
            ("warehouse_id", "int", True, "Warehouse"),
            ("quantity", "int", True, "Units on hand"),
        ),
        "relationships": ["Product 1..* StockLevel"],
    }, None),
    (r"\bpurchase orders?\b|\borders?\b|\bpurchasing\b", {
        "name": "PurchaseOrder", "description": "An order placed with a supplier.",
        "fields": _fields(
            ("supplier_id", "int", True, "Supplier"),
            ("product_id", "int", True, "Product ordered"),
            ("quantity", "int", True, "Units ordered"),
            ("order_status", "str", True, "draft / placed / received"),
            ("order_date", "date", True, "Order date"),
        ),
        "relationships": ["Supplier 1..* PurchaseOrder", "Product 1..* PurchaseOrder"],
    }, None),
    (r"\bcustomers?\b|\bclients?\b", {
        "name": "Customer", "description": "A customer of the business.",
        "fields": _fields(
            ("customer_name", "str", True, "Customer name"),
            ("email", "str", True, "Email"),
            ("phone", "str", False, "Phone"),
        ),
        "relationships": [],
    }, None),
    (r"\bregistration\b|\blogin\b|\busers?\b|\baccounts?\b|\bsign[- ]?up\b", {
        "name": "UserAccount", "description": "An application user account.",
        "fields": _fields(
            ("display_name", "str", True, "Display name"),
            ("email", "str", True, "Login email"),
            ("role", "str", True, "Application role"),
        ),
        "relationships": [],
    }, "Employee"),
]

FALLBACK_ENTITY = {
    "name": "Record", "description": "Generic business record (no domain entities detected).",
    "fields": _fields(
        ("title", "str", True, "Title"),
        ("details", "str", False, "Details"),
        ("record_status", "str", True, "Status"),
    ),
    "relationships": [],
}

AUTH_PATTERN = r"\blogin\b|\blog in\b|\bregistration\b|\bsign[- ]?(up|in)\b|\bauthenticat"
REPORT_PATTERN = r"\breports?\b|\breporting\b|\banalytics\b|\bdashboards?\b"


def normalize(text: str) -> str:
    return " ".join(text.split())


def extract_features(text: str) -> list[str]:
    """Split a requirement like 'Build X with a, b, and c.' into ['a', 'b', 'c']."""
    clean = normalize(text)
    match = re.search(r"\b(?:with|including|supporting|that supports)\b(.+)", clean, re.I)
    if not match:
        match = re.search(r"\bfor\b(.+)", clean, re.I)
    body = (match.group(1) if match else clean).strip().rstrip(".")
    parts = re.split(r",|;|\n|\.\s|\band\b", body)
    features: list[str] = []
    for part in parts:
        feature = part.strip(" .-:").removeprefix("also ").strip()
        if len(feature) >= 3 and feature.lower() not in (f.lower() for f in features):
            features.append(feature)
    return features[:25] or [clean[:200]]


def detect_roles(text: str) -> list[str]:
    roles = [role for pattern, role in ROLE_PATTERNS if re.search(pattern, text, re.I)]
    return list(dict.fromkeys(roles))


def detect_entities(text: str) -> list[dict]:
    found: list[dict] = []
    for pattern, spec, unless in ENTITY_CATALOGUE:
        if re.search(pattern, text, re.I):
            if unless and any(entity["name"] == unless for entity in found):
                continue
            if all(entity["name"] != spec["name"] for entity in found):
                found.append(spec)
    return found or [FALLBACK_ENTITY]


def mentions(pattern: str, text: str) -> bool:
    return re.search(pattern, text, re.I) is not None


def pick_role(feature: str, roles: list[str]) -> str:
    lowered = feature.lower()
    for role in roles:
        key = role.split()[0].lower()
        if key in lowered or (key == "hr" and "hr" in lowered.split()):
            return role
    if "approv" in lowered:
        return next((r for r in roles if r in ("Manager", "Administrator")), roles[0])
    if "report" in lowered or "admin" in lowered:
        return next((r for r in roles if "Admin" in r), roles[0])
    return roles[0]
