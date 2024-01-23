#!/bin/bash

python -m focus_converter.main convert \
    --provider azure \
    --data-format csv \
    --data-path "tests/provider_config_tests/azure/sample-anonymous-ea-export-dataset.csv" \
    --export-path "./azure_conversion" \
    --no-export-include-source-columns
