import unittest

from agents.implementer.prompt import IMPLEMENTER_SYSTEM_PROMPT


class ImplementerPromptContractTests(unittest.TestCase):
    def test_does_not_expand_business_api_for_a_broken_test(
        self,
    ) -> None:
        self.assertIn(
            "TesterReport 是诊断证据，不是必须照做的命令",
            IMPLEMENTER_SYSTEM_PROMPT,
        )
        self.assertIn(
            "不能为了错误测试扩展业务 API",
            IMPLEMENTER_SYSTEM_PROMPT,
        )
        self.assertIn(
            "优先修复测试代码",
            IMPLEMENTER_SYSTEM_PROMPT,
        )


if __name__ == "__main__":
    unittest.main()
