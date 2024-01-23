#!/bin/bash

python -m focus_converter.main convert \
    --provider aws-cur \
    --data-format csv \
    --data-path "tests/provider_config_tests/aws/sample-anonymous-aws-export-dataset.csv" \
    --export-path "./aws_conversion" \
    --no-export-include-source-columns
