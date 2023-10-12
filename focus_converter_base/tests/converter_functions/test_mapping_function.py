import os
import tempfile
from unittest import TestCase
from uuid import uuid4

import pandas as pd
import polars as pl
from jinja2 import Template
from pydantic import ValidationError

from focus_converter.configs.base_config import ConversionPlan
from focus_converter.conversion_functions.column_functions import ColumnFunctions

VALUE_MAPPING_SAMPLE_TEMPLATE_YAML_JINJA = """
plan_name: sample
priority: 1
column: {{ random_column_alias }}
conversion_type: map_values
focus_column: Region
conversion_args:
    default_value: 4_not_mapped
    value_list:
        - key: "1"
          value: 1_mapped
        - key: "2"
          value: 2_mapped
        - key: "3"
          value: 3_mapped
"""

VALUE_MAPPING_SAMPLE_TEMPLATE_YAML_JINJA_WITH_NULL_IGNORE = """
plan_name: sample
priority: 1
column: {{ random_column_alias }}
conversion_type: map_values
focus_column: Region
conversion_args:
    apply_default_if_null: false
    default_value: 4_not_mapped
    value_list:
        - key: "1"
          value: 1_mapped
        - key: "2"
          value: 2_mapped
        - key: "3"
          value: 3_mapped
"""

VALUE_MAPPING_SAMPLE_TEMPLATE_MISSING_VALUE_YAML = """
plan_name: sample
priority: 1
column: test_column
conversion_type: map_values
focus_column: Region
"""

VALUE_MAPPING_SAMPLE_TEMPLATE_YAML = Template(VALUE_MAPPING_SAMPLE_TEMPLATE_YAML_JINJA)


# noinspection DuplicatedCode
class TestMappingFunction(TestCase):
    def test_map_not_defined(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_file_path = os.path.join(temp_dir, "D001_S001.yaml")

            with open(sample_file_path, "w") as fd:
                fd.write(VALUE_MAPPING_SAMPLE_TEMPLATE_MISSING_VALUE_YAML)

            with self.assertRaises(ValidationError) as cm:
                ConversionPlan.load_yaml(sample_file_path)
            self.assertEqual(len(cm.exception.errors()), 1)
            self.assertEqual(cm.exception.errors()[0]["loc"], ("conversion_args",))

    def test_mapping_value(self):
        random_column_alias = str(uuid4())
        generated_yaml = VALUE_MAPPING_SAMPLE_TEMPLATE_YAML.render(
            random_column_alias=random_column_alias
        )

        df = pd.DataFrame(
            [
                {"index_value": "1", random_column_alias: "1"},
                {"index_value": "2", random_column_alias: "2"},
                {"index_value": "3", random_column_alias: "3"},
                {"index_value": "4", random_column_alias: "4"},
                {"index_value": "5", random_column_alias: None},
            ]
        )
        pl_df = pl.from_dataframe(df).lazy()

        with tempfile.TemporaryDirectory() as temp_dir:
            sample_file_path = os.path.join(temp_dir, "D001_S001.yaml")

            with open(sample_file_path, "w") as fd:
                fd.write(generated_yaml)

            conversion_plan = ConversionPlan.load_yaml(sample_file_path)
            sample_col = ColumnFunctions.map_values(
                plan=conversion_plan, column_alias=random_column_alias
            )

            modified_pl_df = pl_df.with_columns([sample_col]).collect()
            for index_value, mapped_value in modified_pl_df.iter_rows():
                if index_value == "1":
                    self.assertEqual(mapped_value, "1_mapped")
                elif index_value == "2":
                    self.assertEqual(mapped_value, "2_mapped")
                elif index_value == "3":
                    self.assertEqual(mapped_value, "3_mapped")
                elif index_value == "4":
                    self.assertEqual(mapped_value, "4_not_mapped")
                elif index_value == "5":
                    self.assertEqual(mapped_value, "4_not_mapped")
                else:
                    raise self.failureException(
                        f"Invalid value, map function not mapped, key: {index_value}, value: {mapped_value}"
                    )

    def test_mapping_value_with_null_default_false(self):
        random_column_alias = str(uuid4())
        generated_random_column_alias = str(uuid4())
        generated_yaml = Template(
            VALUE_MAPPING_SAMPLE_TEMPLATE_YAML_JINJA_WITH_NULL_IGNORE
        ).render(random_column_alias=random_column_alias)

        df = pd.DataFrame(
            [
                {"index_value": "1", random_column_alias: "1"},
                {"index_value": "2", random_column_alias: "2"},
                {"index_value": "3", random_column_alias: "3"},
                {"index_value": "4", random_column_alias: "4"},
                {"index_value": "5", random_column_alias: None},
            ]
        )
        pl_df = pl.from_dataframe(df).lazy()

        with tempfile.TemporaryDirectory() as temp_dir:
            sample_file_path = os.path.join(temp_dir, "D001_S001.yaml")

            with open(sample_file_path, "w") as fd:
                fd.write(generated_yaml)

            conversion_plan = ConversionPlan.load_yaml(sample_file_path)
            sample_col = ColumnFunctions.map_values(
                plan=conversion_plan, column_alias=generated_random_column_alias
            )

            modified_pl_df = pl_df.with_columns([sample_col]).collect()
            for index_value, _, mapped_value in modified_pl_df.iter_rows():
                if index_value == "1":
                    self.assertEqual(mapped_value, "1_mapped")
                elif index_value == "2":
                    self.assertEqual(mapped_value, "2_mapped")
                elif index_value == "3":
                    self.assertEqual(mapped_value, "3_mapped")
                elif index_value == "4":
                    self.assertEqual(mapped_value, "4_not_mapped")
                elif index_value == "5":
                    self.assertIsNone(mapped_value)
                else:
                    raise self.failureException(
                        f"Invalid value, map function not mapped, key: {index_value}, value: {mapped_value}"
                    )
