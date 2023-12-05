import os
import traceback
from enum import Enum
from importlib import util


class STATIC_CONVERSION_TYPES(Enum):
    # datetime functions
    CONVERT_TIMEZONE = "convert_timezone"
    ASSIGN_TIMEZONE = "assign_timezone"
    ASSIGN_UTC_TIMEZONE = "assign_utc_timezone"
    PARSE_DATETIME = "parse_datetime"

    # sql rule functions
    SQL_QUERY = "sql_query"
    SQL_CONDITION = "sql_condition"

    # column rename function
    RENAME_COLUMN = "rename_column"

    # unnest operation
    UNNEST_COLUMN = "unnest"

    # lookup operation
    LOOKUP = "lookup"

    # value mapping function
    MAP_VALUES = "map_values"

    # allows setting static values
    ASSIGN_STATIC_VALUE = "static_value"

    # apply default values if column not present
    APPLY_DEFAULT_IF_COLUMN_MISSING = "apply_default_if_column_missing"

    # set column dtypes
    SET_COLUMN_DTYPES = "set_column_dtypes"


class Base:
    """Basic resource class. Concrete resources will inherit from this one"""

    plugins = []

    # For every class that inherits from the current,
    # the class name will be added to plugins
    def __init_subclass__(cls, **kwargs):
        print("init subclass", cls)
        super().__init_subclass__(**kwargs)
        cls.plugins.append(cls)
        print(cls.plugins)


# Small utility to automatically load modules
def load_module(path):
    name = os.path.split(path)[-1]
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Get current path
path = os.path.abspath(__file__)
dirpath = os.path.dirname(path)

for fname in os.listdir(dirpath):
    # Load only "real modules"
    if (
        not fname.startswith(".")
        and not fname.startswith("__")
        and fname.endswith(".py")
    ):
        load_module(os.path.join(dirpath, fname))
__all__ = ["STATIC_CONVERSION_TYPES", "Base"]
