import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from pipeline import parse_number, div
class PipelineTests(unittest.TestCase):
    def test_parse_number(self):
        self.assertEqual(parse_number("1,234"),1234)
        self.assertEqual(parse_number("(123)"),-123)
        self.assertIsNone(parse_number("-"))
    def test_div(self):
        self.assertEqual(div(10,2),5)
        self.assertIsNone(div(10,0))
if __name__=="__main__": unittest.main()
