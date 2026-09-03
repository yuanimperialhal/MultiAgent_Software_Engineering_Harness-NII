import json
import os
import sys
from datetime import datetime


# === 数据模型层 ===

class TodoItem:
    """
    封装单条待办事项的数据结构与基础验证。

    Args:
        id (int): 待办事项唯一整数ID。
        title (str): 标题，必填，非空字符串。
        desc (str): 描述，可选，默认为空字符串。
        due_date (str | None): 截止日期，格式为 'YYYY-MM-DD'，可选；非法格式将被拒绝。
        status (str): 状态，必须为 'pending' 或 'completed'。
    """

    def __init__(self, id: int, title: str, desc: str = "", due_date: str | None = None, status: str = "pending"):
        if not isinstance(id, int) or id < 1:
            raise ValueError("id must be a positive integer")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")
        if status not in ("pending", "completed"):
            raise ValueError("status must be 'pending' or 'completed'")
        if due_date is not None and not self.is_valid_due_date(due_date):
            raise ValueError(f"invalid due_date format: '{due_date}'. Expected 'YYYY-MM-DD'.")

        self.id = id
        self.title = title.strip()
        self.desc = desc.strip()
        self.due_date = due_date
        self.status = status
        self.created_at = datetime.now().isoformat()
        self.completed_at = datetime.now().isoformat() if status == "completed" else None

    def is_valid_due_date(self, date_str: str) -> bool:
        """
        校验截止日期字符串是否符合 YYYY-MM-DD 格式且为合法日期。

        Returns:
            bool: 校验通过返回 True，否则 False。
        """
        if not isinstance(date_str, str):
            return False
        parts = date_str.split("-")
        if len(parts) != 3:
            return False
        try:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            # Use datetime constructor for full validation (handles leap years, etc.)
            datetime(year, month, day)
            return True
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> dict:
        """序列化为字典，用于 JSON 序列化。"""
        return {
            "id": self.id,
            "title": self.title,
            "desc": self.desc,
            "due_date": self.due_date,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TodoItem":
        """从字典反序列化为 TodoItem 实例。"""
        required_keys = {"id", "title", "status"}
        if not required_keys.issubset(data.keys()):
            missing = required_keys - set(data.keys())
            raise ValueError(f"missing required keys in task data: {missing}")
        # Use get with defaults for optional fields
        return cls(
            id=int(data["id"]),
            title=str(data["title"]),
            desc=str(data.get("desc", "")),
            due_date=data.get("due_date"),
            status=str(data["status"]),
        )


# === 业务逻辑层 ===

TODO_FILE = "todos.json"  # Planner 指定的统一文件名


class TodoManager:
    """
    核心业务逻辑管理器：CRUD、状态管理、ID生成、查询过滤。
    不负责IO或用户交互。
    """

    def __init__(self):
        self._tasks = []
        self._next_id = 1
        self.load_from_file(TODO_FILE)

    def add_item(self, title: str, desc: str = "", due_date: str | None = None) -> int:
        """
        新增一条待办事项。

        Args:
            title: 标题（必填）。
            desc: 描述（可选）。
            due_date: 截止日期（可选，格式 YYYY-MM-DD）。
        Returns:
            int: 新增项的 ID。

        Raises:
            ValueError: 标题为空或 due_date 格式非法。
        """
        if not title or not title.strip():
            raise ValueError("Title cannot be empty.")
        new_id = self._next_id
        self._next_id += 1
        item = TodoItem(new_id, title, desc, due_date)
        self._tasks.append(item)
        return new_id

    def get_all(self) -> list[TodoItem]:
        """获取全部待办事项（按ID升序）"""
        return sorted(self._tasks, key=lambda x: x.id)

    def get_by_status(self, status: str) -> list[TodoItem]:
        """按状态筛选待办事项。"""
        if status not in ("pending", "completed"):
            raise ValueError("status must be 'pending' or 'completed'")
        return [t for t in self._tasks if t.status == status]

    def mark_completed(self, item_id: int) -> bool:
        """
        将指定ID的待办事项标记为已完成。

        Returns:
            bool: 成功返回 True，ID不存在或已为 completed 则返回 False。
        """
        for task in self._tasks:
            if task.id == item_id:
                if task.status == "completed":
                    return False
                task.status = "completed"
                task.completed_at = datetime.now().isoformat()
                try:
                    self.save_to_file(TODO_FILE)  # ✅ Auto-save on state change
                except RuntimeError as e:
                    print(f"⚠️  警告：保存失败，状态变更可能未持久化：{e}")
                return True
        return False

    def delete_item(self, item_id: int) -> bool:
        """
        删除指定ID的待办事项。

        Returns:
            bool: 成功返回 True，ID不存在则返回 False。
        """
        for i, task in enumerate(self._tasks):
            if task.id == item_id:
                self._tasks.pop(i)
                return True
        return False

    def save_to_file(self, filepath: str):
        """持久化所有任务到 JSON 文件。"""
        try:
            data = [t.to_dict() for t in self._tasks]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"Failed to save tasks to {filepath}: {e}")

    def load_from_file(self, filepath: str):
        """从 JSON 文件加载任务列表。若文件不存在或损坏，则初始化为空列表。"""
        if not os.path.exists(filepath):
            self._tasks = []
            self._next_id = 1
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON root must be an array")
            loaded_tasks = []
            max_id = 0
            for item_data in data:
                try:
                    item = TodoItem.from_dict(item_data)
                    loaded_tasks.append(item)
                    if item.id > max_id:
                        max_id = item.id
                except (ValueError, KeyError, TypeError) as e:
                    # Skip invalid items, log warning?
                    continue
            self._tasks = loaded_tasks
            self._next_id = max_id + 1 if loaded_tasks else 1
        except json.JSONDecodeError as e:
            # Corrupted file → treat as empty
            print(f"Warning: Failed to load {filepath}, using empty list: {e}")
            self._tasks = []
            self._next_id = 1
        except Exception as e:
            # Any other I/O error → fallback to empty
            print(f"Warning: Failed to load {filepath}, using empty list: {e}")
            self._tasks = []
            self._next_id = 1

    def search_by_keyword(self, keyword: str) -> list[TodoItem]:
        """
        根据关键词搜索待办事项（匹配标题和描述）。

        Args:
            keyword (str): 搜索关键词，不区分大小写。

        Returns:
            list[TodoItem]: 匹配的待办事项列表。
        """
        if not isinstance(keyword, str) or not keyword.strip():
            return []
        keyword_lower = keyword.lower()
        result = []
        for item in self._tasks:
            if keyword_lower in item.title.lower() or keyword_lower in item.desc.lower():
                result.append(item)
        return result


# === 交互层 ===

def show_menu():
    """打印主菜单。"""
    print("\n=== Todo CLI ===")
    print("1. 新增待办事项")
    print("2. 查看全部待办事项")
    print("3. 查看待办中事项")
    print("4. 查看已完成事项")
    print("5. 标记为已完成")
    print("6. 显示帮助信息")
    print("7. 删除待办事项")
    print("8. 搜索待办事项")
    print("0. 退出")
    print("-" * 20)


def get_nonempty_input(prompt: str) -> str:
    """获取非空输入，空则重试。"""
    while True:
        s = input(prompt).strip()
        if s:
            return s
        print("输入不能为空，请重新输入。")


def get_optional_input(prompt: str) -> str | None:
    """获取可选输入，空则返回 None。"""
    s = input(prompt).strip()
    return s if s else None


def safe_int_input(prompt: str) -> int:
    """安全读取整数输入，失败则重试。"""
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("请输入一个有效的整数。")


def list_tasks(tasks: list[TodoItem], title: str):
    """格式化打印任务列表。"""
    print(f"\n{title} ({len(tasks)} 条)：")
    print("-" * 80)
    if not tasks:
        print("(暂无数据)")
        return
    for task in tasks:
        due_str = task.due_date if task.due_date else "-"
        desc_str = task.desc[:40] + "..." if len(task.desc) > 40 else task.desc
        status_icon = "✅" if task.status == "completed" else "❌"
        print(f"{status_icon}[{task.id}] {task.title:<20} | {task.status:<10} | {due_str:<12} | {desc_str}")
    print("-" * 80)


def show_help():
    """显示详细帮助信息。"""
    print("\n💡 使用帮助：")
    print("  • 新增待办事项：输入标题（必填），可选填写描述和截止日期（YYYY-MM-DD）。")
    print("  • 查看各类事项：支持查看全部、待办中、已完成三种视图。")
    print("  • 标记为已完成：输入待办事项 ID 即可将其状态更新为 'completed'。")
    print("  • 删除待办事项：输入待办事项 ID 即可将其从列表中移除。")
    print("  • 退出程序：选择 '0' 或按 Ctrl+C。")
    print("  • 输入校验：所有输入均经过合法性检查（如空标题、非法日期等），错误时会提示。")
    print("  • 数据持久化：所有操作自动保存至 todos.json，重启后数据不丢失。\n")


def run_cli():
    """主交互循环。"""
    manager = TodoManager()

    while True:
        show_menu()
        try:
            choice = input("请选择操作 (0-8): ").strip()

            if choice == "0":
                print("再见！")
                manager.save_to_file(TODO_FILE)
                break
            elif choice == "1":
                print("\n--- 新增待办事项 ---")
                title = get_nonempty_input("标题：")
                desc = get_optional_input("描述（可空）：")
                due_date = get_optional_input("截止日期（YYYY-MM-DD，可空）：")
                try:
                    new_id = manager.add_item(title, desc, due_date)
                    print(f"✅ 已新增，ID：{new_id}")
                except ValueError as e:
                    print(f"❌ 输入错误：{e}")
                except Exception as e:
                    print(f"❌ 未知错误：{e}")
                # Remove redundant save here — add_item does NOT auto-save; only CLI exit & state-change ops do
            elif choice == "2":
                tasks = manager.get_all()
                list_tasks(tasks, "全部待办事项")
            elif choice == "3":
                tasks = manager.get_by_status("pending")
                list_tasks(tasks, "待办中事项")
            elif choice == "4":
                tasks = manager.get_by_status("completed")
                list_tasks(tasks, "已完成事项")
            elif choice == "5":
                print("\n--- 标记为已完成 ---")
                item_id = safe_int_input("请输入待办ID：")
                if manager.mark_completed(item_id):
                    print(f"✅ ID {item_id} 已标记为已完成。")
                else:
                    print(f"❌ ID {item_id} 不存在或已是已完成状态。")
                # save_to_file now happens inside mark_completed — no need to duplicate here
            elif choice == "6":
                show_help()
            elif choice == "7":
                print("\n--- 删除待办事项 ---")
                item_id = safe_int_input("请输入待办ID：")
                if manager.delete_item(item_id):
                    print(f"✅ ID {item_id} 已删除。")
                else:
                    print(f"❌ ID {item_id} 不存在。")
            elif choice == "8":
                print("\n--- 搜索待办事项 ---")
                keyword = get_nonempty_input("请输入关键词：")
                tasks = manager.search_by_keyword(keyword)
                list_tasks(tasks, f"搜索结果（关键词：'{keyword}'）")
            else:
                print("❌ 无效选择，请输入 0-8 之间的数字。")

        except KeyboardInterrupt:
            print("\n\n程序被用户中断。")
            manager.save_to_file(TODO_FILE)
            break
        except EOFError:
            print("\n\n输入流结束。")
            manager.save_to_file(TODO_FILE)
            break
        except Exception as e:
            print(f"❌ 程序运行异常：{e}")


if __name__ == "__main__":
    run_cli()