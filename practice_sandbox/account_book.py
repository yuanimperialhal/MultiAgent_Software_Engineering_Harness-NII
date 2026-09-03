import datetime
import json
import os
import sys
import tempfile


class AccountRecord:
    """
    表示一条收支记录。
    """
    def __init__(self, date: str, record_type: str, amount: float, note: str = "", category: str = ""):
        # Validate record_type
        if record_type not in ("income", "expense"):
            raise ValueError("record_type must be 'income' or 'expense'")
        # Validate amount
        if amount < 0:
            raise ValueError("amount must be non-negative")
        # Validate date format
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be in 'YYYY-MM-DD' format")
        # Validate category
        if not isinstance(category, str):
            raise ValueError("category must be a string")
        if not category.strip():
            raise ValueError("category must be non-empty")
        if len(category.strip()) > 20:
            raise ValueError("category length must be <= 20")
        self.date = date
        self.type = record_type  # 'income' or 'expense'
        self.amount = amount
        self.note = note
        self.category = category.strip()

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "type": self.type,
            "amount": self.amount,
            "note": self.note,
            "category": self.category
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AccountRecord":
        # Extract and validate category
        category = data.get("category", "")
        if not isinstance(category, str):
            raise ValueError("category must be a string in record data")
        if not category.strip():
            raise ValueError("category must be non-empty in record data")
        if len(category.strip()) > 20:
            raise ValueError("category length must be <= 20 in record data")
        return cls(
            date=data["date"],
            record_type=data["type"],
            amount=float(data["amount"]),
            note=data.get("note", ""),
            category=category
        )


class AccountBook:
    """
    简易记账本管理器，所有数据暂存于内存。
    """
    def __init__(self):
        self._records = []

    def add_record(self, date: str, record_type: str, amount: float, note: str = "", category: str = "") -> None:
        """
        添加一条收支记录。
        """
        if record_type not in ("income", "expense"):
            raise ValueError("record_type must be 'income' or 'expense'")
        if amount < 0:
            raise ValueError("amount must be non-negative")
        # Basic date format check: YYYY-MM-DD
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be in 'YYYY-MM-DD' format")
        record = AccountRecord(date, record_type, amount, note, category)
        self._records.append(record)

    def get_all(self) -> list[AccountRecord]:
        """
        获取全部记录（按添加顺序）。
        """
        return self._records.copy()

    def query_by_date_range(self, start_date: str, end_date: str) -> list[AccountRecord]:
        """
        按日期范围查询（包含起止日），格式：YYYY-MM-DD。
        """
        try:
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date range must be in 'YYYY-MM-DD' format")
        if start > end:
            raise ValueError("start_date must be <= end_date")

        result = []
        for r in self._records:
            try:
                r_date = datetime.datetime.strptime(r.date, "%Y-%m-%d")
                if start <= r_date <= end:
                    result.append(r)
            except ValueError:
                continue  # skip invalid date
        return result

    def query_by_type(self, record_type: str) -> list[AccountRecord]:
        """
        按类型查询（'income' 或 'expense'）。
        """
        if record_type not in ("income", "expense"):
            raise ValueError("record_type must be 'income' or 'expense'")
        return [r for r in self._records if r.type == record_type]

    def query_by_category(self, category: str) -> list[AccountRecord]:
        """
        按分类查询（精确匹配，区分大小写）。
        """
        if not isinstance(category, str) or not category.strip():
            raise ValueError("category must be a non-empty string")
        return [r for r in self._records if r.category == category.strip()]

    def get_summary(self) -> dict:
        """
        返回汇总统计：总收入、总支出、余额。
        """
        total_income = sum(r.amount for r in self._records if r.type == "income")
        total_expense = sum(r.amount for r in self._records if r.type == "expense")
        balance = total_income - total_expense
        return {
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "balance": round(balance, 2)
        }

    def save_to_file(self, filepath: str) -> None:
        """
        原子化保存当前所有记录到 JSON 文件。
        """
        import tempfile
        import os
        data = [r.to_dict() for r in self._records]
        # Write to temporary file first
        temp_fd, temp_path = tempfile.mkstemp(suffix=".json", dir=os.path.dirname(filepath) or None)
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Atomically replace
            os.replace(temp_path, filepath)
        except Exception:
            # Clean up temp file on error
            os.close(temp_fd)
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def load_from_file(self, filepath: str) -> None:
        """
        从 JSON 文件加载记录；失败时静默设为空列表。
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise TypeError("JSON root must be an array")
            loaded_records = []
            for item_data in data:
                try:
                    record = AccountRecord.from_dict(item_data)
                    loaded_records.append(record)
                except (ValueError, KeyError, TypeError):
                    # Skip invalid record
                    continue
            self._records = loaded_records
        except FileNotFoundError:
            # File doesn't exist → empty state
            self._records = []
        except (json.JSONDecodeError, TypeError) as e:
            # Corrupted or malformed → warn and reset
            import warnings
            warnings.warn(f"Failed to load {filepath}: {e}. Initializing empty records.")
            self._records = []


def safe_float_input(prompt: str) -> float:
    while True:
        try:
            return float(input(prompt).strip())
        except ValueError:
            print("❌ 请输入一个有效的数字。")


def safe_date_input(prompt: str) -> str:
    while True:
        s = input(prompt).strip()
        try:
            datetime.datetime.strptime(s, "%Y-%m-%d")
            return s
        except ValueError:
            print("❌ 日期格式错误，请输入 YYYY-MM-DD 格式。")


def get_nonempty_input(prompt: str) -> str:
    while True:
        s = input(prompt).strip()
        if s:
            return s
        print("❌ 输入不能为空，请重新输入。")


def handle_add(args, book):
    try:
        book.add_record(
            date=args.date,
            record_type=args.type,
            amount=args.amount,
            note=args.note,
            category=args.category
        )
        print("✅ 记录已添加。")
    except ValueError as e:
        print(f"❌ 输入错误：{e}")


def handle_list(args, book):
    if args.date_range:
        try:
            start, end = args.date_range
            records = book.query_by_date_range(start, end)
            list_records(records, f"{start} 至 {end} 的记录")
        except ValueError as e:
            print(f"❌ 查询错误：{e}")
    else:
        records = book.get_all()
        list_records(records, "所有收支记录")


def handle_summary(args, book):
    summary = book.get_summary()
    print(f"\n📊 汇总统计：")
    print(f"   总收入：¥{summary['total_income']:.2f}")
    print(f"   总支出：¥{summary['total_expense']:.2f}")
    print(f"   余额：  ¥{summary['balance']:.2f}")
    print("-" * 30)


def list_records(records: list[AccountRecord], title: str):
    print(f"\n{title} ({len(records)} 条)：")
    print("-" * 90)
    if not records:
        print("(暂无数据)")
        return
    for r in records:
        type_icon = "💰" if r.type == "income" else "💸"
        print(f"{type_icon} {r.date:<10} | {r.type:<8} | ¥{r.amount:<10.2f} | {r.category:<12} | {r.note}")
    print("-" * 90)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="每日记账软件 CLI")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # Add command
    add_parser = subparsers.add_parser("add", help="添加收支记录")
    add_parser.add_argument("--date", required=True, help="日期（YYYY-MM-DD）")
    add_parser.add_argument("--amount", type=float, required=True, help="金额")
    add_parser.add_argument("--type", choices=["income", "expense"], required=True, help="类型（income/expense）")
    add_parser.add_argument("--category", default="", help="分类（默认为空）")
    add_parser.add_argument("--note", default="", help="备注（默认为空）")

    # List command
    list_parser = subparsers.add_parser("list", help="列出收支记录")
    list_parser.add_argument("--date-range", nargs=2, metavar=("START", "END"), help="日期范围（YYYY-MM-DD YYYY-MM-DD）")

    # Summary command
    subparsers.add_parser("summary", help="查看汇总统计")

    args = parser.parse_args()

    # Initialize book and load data
    book = AccountBook()
    book.load_from_file("data.json")

    # Dispatch
    if args.command == "add":
        handle_add(args, book)
    elif args.command == "list":
        handle_list(args, book)
    elif args.command == "summary":
        handle_summary(args, book)
    else:
        parser.print_help()
        sys.exit(1)

    # Save before exit
    try:
        book.save_to_file("data.json")
    except Exception as e:
        print(f"⚠️  警告：保存失败，数据可能未持久化：{e}")


if __name__ == "__main__":
    main()