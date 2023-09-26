import logging
import os
from operator import attrgetter
from typing import List, Dict

import polars as pl
from pkg_resources import resource_filename

from focus_converter.configs.base_config import ConversionPlan
from focus_converter.configs.network_simulator import NetworkSimulator
from focus_converter.conversion_functions import STATIC_CONVERSION_TYPES
from focus_converter.conversion_functions.column_functions import ColumnFunctions
from focus_converter.conversion_functions.datetime_functions import (
    DateTimeConversionFunctions,
)
from focus_converter.conversion_functions.sql_functions import SQLFunctions
from focus_converter.data_loaders.data_exporter import DataExporter
from focus_converter.data_loaders.data_loader import DataLoader

# TODO: Make this path configurable so that we can load from a directory outside of the project
BASE_CONVERSION_CONFIGS = resource_filename("focus_converter", "conversion_configs")


class FocusConverter:
    plans: Dict[str, List[ConversionPlan]]
    data_loader: DataLoader
    data_exporter: DataExporter = None

    # set of plan variables for horizontal transformation plans
    h_collected_columns: List[str]  # collected columns
    h_column_exprs: List[pl.col]  # column expressions
    h_sql_queries: List[str]  # sql_queries

    # temporary columns to be removed from final dataset
    __temporary_columns__: List[str]

    def __init__(self):
        self.__network__ = NetworkSimulator()
        self.__temporary_columns__ = []

    def load_provider_conversion_configs(self):
        plans = {}

        for provider in os.listdir(BASE_CONVERSION_CONFIGS):
            # collect all plans specific to vendor
            provider_plans: List[ConversionPlan] = []

            provider_base_path = os.path.join(BASE_CONVERSION_CONFIGS, provider)
            for provider_config_name in os.listdir(provider_base_path):
                provider_config_path = os.path.join(
                    provider_base_path, provider_config_name
                )
                logging.debug(f"Reading plan from path: {provider_config_name}")
                provider_plans.append(ConversionPlan.load_yaml(provider_config_path))

            plans[provider] = sorted(
                provider_plans,
                key=attrgetter("dimension_id", "priority"),
                reverse=False,
            )
        self.plans = plans

    def load_data(self, *args, **kwargs):
        self.data_loader = DataLoader(*args, **kwargs)

    def configure_data_export(self, *args, **kwargs):
        self.data_exporter = DataExporter(*args, **kwargs)

    def prepare_horizontal_conversion_plan(self, provider):
        # final set of columns produced after this transform step
        self.h_collected_columns = collected_columns = []

        # column expressions that will be applied to loaded lazy frame in order
        self.h_column_exprs = column_exprs = []

        # sql queries collected to be applied on the lazy frame
        self.h_sql_queries = sql_queries = []

        # add provider by default to our column expressions
        column_exprs.append(ColumnFunctions.add_provider(provider=provider))

        for plan in self.plans[provider]:
            # column name generated with temporary prefix
            if plan.column_prefix:
                column_alias = f"{plan.column_prefix}_{plan.focus_column.value}"
                self.__temporary_columns__.append(column_alias)
            else:
                column_alias = plan.focus_column.value

            self.__network__.add_conversion_node(plan=plan)

            # add column to plan to collect these dimensions to be added in the computed dataframe
            collected_columns.append(plan.focus_column.value)

            match plan.conversion_type:
                case STATIC_CONVERSION_TYPES.CONVERT_TIMEZONE:
                    column_exprs.append(
                        DateTimeConversionFunctions.convert_timezone(
                            plan=plan, column_alias=column_alias
                        )
                    )
                case STATIC_CONVERSION_TYPES.ASSIGN_TIMEZONE:
                    column_exprs.append(
                        DateTimeConversionFunctions.assign_timezone(
                            plan=plan, column_alias=column_alias
                        )
                    )
                case STATIC_CONVERSION_TYPES.ASSIGN_UTC_TIMEZONE:
                    column_exprs.append(
                        DateTimeConversionFunctions.assign_utc_timezone(
                            plan=plan, column_alias=column_alias
                        )
                    )
                case STATIC_CONVERSION_TYPES.RENAME_COLUMN:
                    column_exprs.append(
                        ColumnFunctions.rename_column_functions(
                            plan=plan, column_alias=column_alias
                        )
                    )
                case STATIC_CONVERSION_TYPES.SQL_QUERY:
                    sql_queries.append(
                        SQLFunctions.eval_sql_query(
                            plan=plan, column_alias=column_alias
                        )
                    )
                case STATIC_CONVERSION_TYPES.SQL_CONDITION:
                    sql_queries.append(
                        SQLFunctions.eval_sql_conditions(
                            plan=plan, column_alias=column_alias
                        )
                    )
                case STATIC_CONVERSION_TYPES.PARSE_DATETIME:
                    column_exprs.append(
                        DateTimeConversionFunctions.parse_datetime(
                            plan=plan, column_alias=column_alias
                        )
                    )
                case STATIC_CONVERSION_TYPES.UNNEST_COLUMN:
                    column_exprs.append(
                        ColumnFunctions.unnest(plan=plan, column_alias=column_alias)
                    )
                case _:
                    raise NotImplementedError(
                        f"Plan: {plan.conversion_type} not implemented"
                    )
        return column_exprs

    @staticmethod
    def __apply_sql_queries__(
        lf: pl.LazyFrame, sql_context: pl.SQLContext, sql_queries
    ):
        for sql_query in sql_queries:
            lf = sql_context.execute(sql_query, eager=False)
        return lf

    @staticmethod
    def __apply_column_expressions__(
        lf: pl.LazyFrame, column_expressions: List[pl.col]
    ):
        for expr in column_expressions:
            lf = lf.with_columns(expr)
        return lf

    def explain(self):
        # get batched data lazy frame, build the plan and then break
        return self.__network__.show_graph()

    def apply_plan(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        # creates lazy frame using the config, actual computation happens in collect

        lf = self.__apply_column_expressions__(
            lf=lf, column_expressions=self.h_column_exprs
        )

        sql_context = SQLFunctions.create_sql_context(lf=lf)
        lf = self.__apply_sql_queries__(
            lf=lf, sql_context=sql_context, sql_queries=self.h_sql_queries
        )

        # drop temporary columns from the final dataset
        lf = lf.drop(self.__temporary_columns__)

        return lf

    def convert(self):
        error = None

        for lf in self.data_loader.data_scanner():
            try:
                lf = self.apply_plan(lf=lf)
                self.data_exporter.collect(
                    lf=lf, collected_columns=list(set(self.h_collected_columns))
                )
            except Exception as e:
                error = e
                break

        if error is not None:
            # cleanup data export now that we have to close all subprocesses
            if self.data_exporter:
                self.data_exporter.close()

            raise error
