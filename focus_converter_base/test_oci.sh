#!/bin/bash

python -m focus_converter.main convert \
    --provider oci \
    --data-format csv \
    --data-path "tests/provider_config_tests/oci/reports_cost-csv_0000000030000269.csv" \
    --export-path "./oci_conversion" \
    --no-export-include-source-columns
