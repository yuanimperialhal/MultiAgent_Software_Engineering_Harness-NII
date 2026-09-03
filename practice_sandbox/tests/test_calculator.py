import unittest
from calculator import add


class TestAdd(unittest.TestCase):
    """Test cases for the add function."""

    def test_positive_integers(self):
        self.assertEqual(add(2, 3), 5)

    def test_negative_integers(self):
        self.assertEqual(add(-1, -4), -5)

    def test_zero_values(self):
        self.assertEqual(add(0, 5), 5)
        self.assertEqual(add(-3, 0), -3)
        self.assertEqual(add(0, 0), 0)

    def test_floats(self):
        self.assertAlmostEqual(add(1.5, 2.5), 4.0)
        self.assertAlmostEqual(add(-1.1, -2.2), -3.3)

    def test_mixed_types(self):
        self.assertEqual(add(2, 3.0), 5.0)
        self.assertAlmostEqual(add(1.5, 2), 3.5)


if __name__ == "__main__":
    unittest.main()
