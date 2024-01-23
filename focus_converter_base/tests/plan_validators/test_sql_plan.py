import os
import tempfile
from unittest import TestCase

import polars as pl

from focus_converter.converter import FocusConverter

SAMPLE_SQL_PLAN = """
plan_name: Test plan to ensure default value is assigned without triggering column not found error
conversion_type: sql_condition
conversion_args:
    conditions:
        - WHEN sample_column = 'matched_value' THEN 'Matched'
    default_value: default_value
column: NA
focus_column: ChargeSubcategory
"""


class TestSQLPlan(TestCase):
    def test_default_value_column_validator(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # adds a folder for a test provider so that the conversion configs can be loaded
            test_provider = "test_provider"
            os.mkdir(f"{temp_dir}/{test_provider}")

            plan_file_path = f"{temp_dir}/{test_provider}/sample_plan_S001.yaml"
            with open(plan_file_path, "w") as f:
                f.write(SAMPLE_SQL_PLAN)

            lf = pl.DataFrame(
                {
                    "sample_column": ["matched_value", "unmatched_value"],
                }
            ).lazy()

            focus_converter = FocusConverter()
            focus_converter.load_provider_conversion_configs(base_dir=temp_dir)
            focus_converter.prepare_horizontal_conversion_plan(provider=test_provider)
            df = focus_converter.__process_lazy_frame__(lf=lf).collect()

            # assert matched value is assigned
            self.assertEqual(
                list(df["ChargeSubcategory"]), ["Matched", "default_value"]
            )
