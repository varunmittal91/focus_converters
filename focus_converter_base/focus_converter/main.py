import io
import json
import os

from PIL import Image
from focus_validator.validator import Validator
from rich import print

from focus_converter.common.cli_options import *
from focus_converter.converter import FocusConverter
from focus_converter.data_loaders.data_loader import DataFormats

app = typer.Typer(name="FOCUS converters", add_completion=False)


@app.command("convert")
def main(
    provider: PROVIDER_OPTION,
    export_path: EXPORT_PATH_OPTION,
    data_format: DATA_FORMAT_OPTION,
    data_path: DATA_PATH,
    parquet_data_format: PARQUET_DATA_FORMAT_OPTION = None,
    export_include_source_columns: EXPORT_INCLUDE_SOURCE_COLUMNS = True,
    column_prefix: Annotated[
        str,
        typer.Option(
            help="Optional prefix to add to generated column names",
            rich_help_panel="Column Prefix",
        ),
    ] = (None,),
    converted_column_prefix: Annotated[
        str,
        typer.Option(
            help="Optional prefix to add to generated column names",
            rich_help_panel="Column Prefix",
        ),
    ] = ((None,),),
    validate: Annotated[
        bool,
        typer.Option(
            help="Validate generated data to match FOCUS spec.",
            rich_help_panel="Validation",
        ),
    ] = False,
):
    # compute function for conversion

    if data_format == DataFormats.PARQUET and parquet_data_format is None:
        raise typer.BadParameter("parquet_data_format required")

    converter = FocusConverter(
        column_prefix=column_prefix, converted_column_prefix=converted_column_prefix
    )
    converter.load_provider_conversion_configs()
    converter.load_data(
        data_path=data_path,
        data_format=data_format,
        parquet_data_format=parquet_data_format,
    )
    converter.configure_data_export(
        export_path=export_path,
        export_include_source_columns=export_include_source_columns,
    )
    converter.prepare_horizontal_conversion_plan(provider=provider)
    converter.convert()

    if validate:
        for segment_file_name in os.listdir(export_path):
            file_path = os.path.join(export_path, segment_file_name)
            print(file_path)
            validator = Validator(
                data_filename=file_path,
                output_type="console",
                output_destination=None,
            )
            validator.load()
            validator.validate()
            break


@app.command("explain")
def explain(
    provider: PROVIDER_OPTION,
):
    # function to show conversion plan
    converter = FocusConverter()
    converter.load_provider_conversion_configs()
    converter.prepare_horizontal_conversion_plan(provider=provider)

    image = Image.open(io.BytesIO(converter.explain()))
    image.show()


@app.command("list-providers")
def list_providers():
    converter = FocusConverter()
    converter.load_provider_conversion_configs()
    print(json.dumps({"providers": list(converter.plans.keys())}, indent=4))


if __name__ == "__main__":
    app()
