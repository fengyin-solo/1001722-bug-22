"""点检记录业务规则：状态流转、字段校验与筛选口径都收在这里。

状态机只能沿下列方向单向推进，每个动作都校验上一步状态，不允许回退：
    待点检 --开始点检--> 点检中 --提交结果--> 已提交 --退回重检--> 已退回（终态）
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "spotcheck"
REQUIRED_FIELDS = ["点检单号", "关联计划", "点检设备"]
STATUS_FIELD = "点检状态"
ABNORMAL_COUNT_FIELD = "异常项数"
CONCLUSION_FIELD = "点检结论"
ORDER_NO_FIELD = "点检单号"

# 只有这两种状态还需要继续处理；已提交、已退回都不再占用待处理口径
PENDING_STATUSES = ["待点检", "点检中"]

# 动作 -> (必须处于的上一步状态, 推进后的状态)，保证单向流转
ACTION_RULES: dict[str, dict[str, str]] = {
    "开始点检": {"from": "待点检", "to": "点检中"},
    "提交结果": {"from": "点检中", "to": "已提交"},
    "退回重检": {"from": "已提交", "to": "已退回"},
}


def parse_abnormal_count(value: Any) -> int | None:
    """把录入的异常项数解析成非负整数；空值、布尔或非法文本一律视为未填写。"""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = int(text)
    except ValueError:
        return None
    return number if number >= 0 else None


class SpotcheckService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get(ORDER_NO_FIELD, ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = PENDING_STATUSES[0]
        entry[STATUS_FIELD] = PENDING_STATUSES[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(
        self,
        entry_id: int,
        action: str,
        values: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, str]:
        values = values or {}
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"点检记录 {entry_id} 不存在或已归档"
        rule = ACTION_RULES.get(action)
        if rule is None:
            return None, f"动作「{action}」不属于点检记录可执行范围"

        current = str(entry.get("status") or "")
        if current != rule["from"]:
            return None, f"点检记录当前为「{current}」，需处于「{rule['from']}」才能{action}，状态不能回退"

        target = rule["to"]
        abnormal = bool(entry.get("abnormal"))

        if action == "提交结果":
            # 异常项数是复核结论的必填项：空值或非非负整数都不能提交
            count = parse_abnormal_count(values.get(ABNORMAL_COUNT_FIELD))
            if count is None:
                return None, "提交前必须填写异常项数（0 或正整数），空记录不能提交"
            entry[ABNORMAL_COUNT_FIELD] = count
            conclusion = str(values.get(CONCLUSION_FIELD) or "").strip()
            if conclusion:
                entry[CONCLUSION_FIELD] = conclusion
            # 异常标记以复核录入的异常项数为准，提交后固化，不再被后续动作清空
            abnormal = count > 0

        # 只更新状态相关字段，点检单号等历史信息原样保留
        entry["status"] = target
        entry[STATUS_FIELD] = target
        entry["pending"] = target in PENDING_STATUSES
        entry["abnormal"] = abnormal
        return entry, f"点检记录已{action}"
