"""内存数据仓库：给每个业务模块准备一份可筛选、可流转的示例数据。

真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。
"""
from __future__ import annotations

from typing import Any

from app.seed import SEED_ROWS


class Store:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {
            name: [dict(row) for row in rows] for name, rows in SEED_ROWS.items()
        }

    def module_names(self) -> list[str]:
        return sorted(self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def overview(self) -> dict[str, object]:
        modules: list[dict[str, object]] = []
        for name in self.module_names():
            rows = self.rows(name)
            modules.append({
                "name": name,
                "created": len(rows),
                "pending": sum(1 for row in rows if row.get("pending")),
                "abnormal": sum(1 for row in rows if row.get("abnormal")),
            })
        # 点检记录复核结论汇总：已提交的记录待复核，复核通过/退回的结论分别计数
        spotcheck_rows = self.rows("spotcheck")
        spotcheck_review = {
            "pending_review": sum(1 for row in spotcheck_rows if row.get("status") == "已提交"),
            "approved": sum(1 for row in spotcheck_rows if row.get("status") == "已复核"),
            "rejected": sum(1 for row in spotcheck_rows if row.get("status") == "已退回"),
            "abnormal_committed": sum(1 for row in spotcheck_rows if row.get("abnormal")),
            "latest": [
                {
                    "点检单号": row.get("点检单号"),
                    "点检状态": row.get("status"),
                    "复核结论": row.get("复核结论") or "—",
                }
                for row in spotcheck_rows
                if row.get("status") in {"已复核", "已退回"}
            ][-5:],
        }
        cards = [
            {"label": "业务模块", "value": len(modules)},
            {"label": "今日新增", "value": sum(int(item["created"]) for item in modules)},
            {"label": "待处理", "value": sum(int(item["pending"]) for item in modules)},
            {"label": "异常量", "value": sum(int(item["abnormal"]) for item in modules)},
            {"label": "点检待复核", "value": spotcheck_review["pending_review"]},
        ]
        return {"cards": cards, "modules": modules, "spotcheck_review": spotcheck_review}


store = Store()
