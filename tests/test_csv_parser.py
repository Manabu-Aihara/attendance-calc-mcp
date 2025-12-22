import unittest
import os
from app.csv_parser import parse_csv

class TestCsvParser(unittest.TestCase):

    def setUp(self):
        # Create a dummy CSV file for testing
        self.test_csv_path = "test_data.csv"
        self.test_csv_content = """社員ID,勤務形態,実働時間計,リアル実働時間,年休(全日),年休(半日),時間外,時間休,中抜け
1001,通常,8.0,8.0,0,0,1.0,0,0
1002,時短,6.0,6.0,0,0,0,0,0
1001,通常,7.5,7.5,0.5,0,0,0,0
"""
        with open(self.test_csv_path, "w", encoding="utf-8") as f:
            f.write(self.test_csv_content)

        self.test_csv_path_with_missing_header = "test_data_missing_header.csv"
        # リアル実働時間 is missing
        self.test_csv_content_with_missing_header = """社員ID,勤務形態,実働時間計,年休(全日),年休(半日),時間外,時間休,中抜け
1001,通常,8.0,0,0,1.0,0,0
"""
        with open(self.test_csv_path_with_missing_header, "w", encoding="utf-8") as f:
            f.write(self.test_csv_content_with_missing_header)

        self.test_csv_path_empty_lines = "test_data_empty_lines.csv"
        self.test_csv_content_empty_lines = """社員ID,勤務形態,実働時間計,リアル実働時間,年休(全日),年休(半日),時間外,時間休,中抜け
1001,通常,8.0,8.0,0,0,1.0,0,0

1002,時短,6.0,6.0,0,0,0,0,0
"""
        with open(self.test_csv_path_empty_lines, "w", encoding="utf-8") as f:
            f.write(self.test_csv_content_empty_lines)

    def tearDown(self):
        # Clean up the dummy CSV file after testing
        if os.path.exists(self.test_csv_path):
            os.remove(self.test_csv_path)
        if os.path.exists(self.test_csv_path_with_missing_header):
            os.remove(self.test_csv_path_with_missing_header)
        if os.path.exists(self.test_csv_path_empty_lines):
            os.remove(self.test_csv_path_empty_lines)

    def test_parse_csv_default_mapping(self):
        records, errors = parse_csv(self.test_csv_path)
        self.assertEqual(len(records), 3)
        self.assertEqual(len(errors), 0)
        self.assertEqual(records[0]["staff_id"], "1001")
        self.assertEqual(records[0]["work_type"], "通常")
        self.assertEqual(records[0]["actual_work_time"], "8.0")
        self.assertEqual(records[0]["real_time"], "8.0")
        self.assertEqual(records[0]["overtime_hours"], "1.0")


    def test_parse_csv_custom_mapping(self):
        custom_mapping = {
            "社員ID": "employee_id",
            "勤務形態": "work_schedule",
            "実働時間計": "total_hours",
            "リアル実働時間": "real_hours",
        }
        records, errors = parse_csv(self.test_csv_path, header_mapping=custom_mapping)
        self.assertEqual(len(records), 3)
        self.assertEqual(len(errors), 0)
        self.assertEqual(records[0]["employee_id"], "1001")
        self.assertEqual(records[0]["work_schedule"], "通常")
        self.assertEqual(records[0]["total_hours"], "8.0")
        self.assertEqual(records[0]["real_hours"], "8.0")


    def test_parse_csv_file_not_found(self):
        records, errors = parse_csv("non_existent_file.csv")
        self.assertEqual(len(records), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("File not found", errors[0])

    def test_parse_csv_missing_expected_header(self):
        # We need a header mapping that includes the missing header
        custom_mapping_for_missing = {
            "社員ID": "staff_id",
            "勤務形態": "work_type",
            "実働時間計": "actual_work_time",
            "リアル実働時間": "real_time", # This one is missing in the file
        }
        records, errors = parse_csv(self.test_csv_path_with_missing_header, header_mapping=custom_mapping_for_missing)
        self.assertEqual(len(records), 0)
        # There should be one error per line for the missing header
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing expected header 'リアル実働時間'", errors[0])


    def test_parse_csv_empty_lines(self):
        records, errors = parse_csv(self.test_csv_path_empty_lines)
        self.assertEqual(len(records), 2)
        self.assertEqual(len(errors), 0)
        self.assertEqual(records[0]["staff_id"], "1001")
        self.assertEqual(records[1]["staff_id"], "1002")

if __name__ == '__main__':
    unittest.main()

