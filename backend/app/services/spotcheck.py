"""点检记录业务规则：状态流转、字段校验与筛选口径都收在这里。

状态只能单向推进：待点检 → 点检中 → 已提交，已提交之后由复核环节给出结论，
复核通过进入已复核，复核不通过则退回重检（已退回为终态）。任何动作都不允许
把记录往回拨，也不允许改写历史点检单号。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "spotcheck"
REQUIRED_FIELDS = ["点检单号", "关联计划", "点检设备"]
STATUS_ORDER = ["待点检", "点检中", "已提交", "已复核", "已退回"]

# 动作 -> 目标状态
ACTION_RULES = {"开始点检": "点检中", "提交结果": "已提交", "复核通过": "已复核", "退回重检": "已退回"}
# 动作 -> 允许执行该动作的当前状态（上一步）；不在表里的状态一律拒绝，保证单向推进
PREV_STATUS = {
    "开始点检": {"待点检"},
    "提交结果": {"点检中"},
    "复核通过": {"已提交"},
    "退回重检": {"已提交"},
}
# 已复核、已退回是终态；其余状态都还在流程中（已提交表示待复核）
TERMINAL_STATUSES = {"已复核", "已退回"}

# 动作执行时允许顺带更新的字段白名单；点检单号等历史字段不在其中，永远不会被覆盖
ACTION_EDITABLE_FIELDS = {"点检人员", "点检日期", "点检结论", "异常项数", "复核结论"}
SUBMIT_REQUIRED_FIELDS = ["异常项数"]


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
            rows = [row for row in rows if keyword in str(row.get("点检单号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return [self._normalize(dict(row)) for row in rows[start:start + size]], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        return self._normalize(dict(entry)) if entry is not None else None

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        code = str(values.get("点检单号")).strip()
        if any(str(row.get("点检单号") or "").strip() == code for row in store.rows(MODULE)):
            return None, [f"点检单号 {code} 已存在，历史单号不能重复登记"]
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["点检状态"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return self._normalize(dict(entry)), []

    def run_action(
        self,
        entry_id: int,
        action: str,
        values: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"点检记录 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于点检记录可执行范围"

        current = str(entry.get("status") or "")
        allowed = PREV_STATUS.get(action, set())
        if current not in allowed:
            expected = "、".join(sorted(allowed)) if allowed else "无"
            return None, f"当前状态为「{current}」，仅「{expected}」的记录可执行{action}，状态不能回退"

        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"

        values = values or {}
        if action == "提交结果":
            count, error = self._parse_abnormal_count(values.get("异常项数", entry.get("异常项数")))
            if error:
                return None, error
            entry["异常项数"] = count
            # 异常标记由异常项数决定，提交时落定，后续复核/退回不再重置
            entry["abnormal"] = count > 0

        # 仅允许白名单字段随动作更新，历史点检单号等字段原样保留
        for field, value in values.items():
            if field in ACTION_EDITABLE_FIELDS and value is not None and str(value).strip() != "":
                entry[field] = value

        if action == "退回重检" and not str(entry.get("复核结论") or "").strip():
            entry["复核结论"] = "复核不通过，退回重检"
        if action == "复核通过" and not str(entry.get("复核结论") or "").strip():
            entry["复核结论"] = "复核通过"

        entry["status"] = target
        entry["点检状态"] = target
        entry["pending"] = target not in TERMINAL_STATUSES
        return self._normalize(dict(entry)), f"点检记录已{action}"

    @staticmethod
    def _parse_abnormal_count(raw: Any) -> tuple[int | None, str]:
        """异常项数必须是已填写的非负整数；为空的记录不允许提交。"""
        if raw is None or str(raw).strip() == "":
            return None, "异常项数为空，点检结果未填写完整，不能提交"
        try:
            count = int(str(raw).strip())
        except (TypeError, ValueError):
            return None, f"异常项数「{raw}」不是合法数字，不能提交"
        if count < 0:
            return None, "异常项数不能为负数，请核对后再提交"
        return count, ""

    @staticmethod
    def _normalize(entry: dict[str, Any]) -> dict[str, Any]:
        """列表与详情共用同一出口：点检状态展示列始终与真实 status 保持一致。"""
        status = entry.get("status")
        if status:
            entry["点检状态"] = status
        return entry
