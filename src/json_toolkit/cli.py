"""
CLI interface for json-toolkit.
"""

import click

from .core import _dumps_json, format_json, minify_json, query_path, validate_json


@click.group()
@click.version_option()
def main():
    """JSON Toolkit - Powerful JSON processing toolkit."""
    pass


@main.command()
@click.option("-i", "--input", required=True, help="Input JSON file")
@click.option("-o", "--output", required=True, help="New output JSON file (must not exist)")
@click.option("--indent", type=int, default=2, help="Indentation spaces")
@click.option("--sort", is_flag=True, help="Sort keys alphabetically")
def format(input, output, indent, sort):
    """Format JSON file with pretty printing."""
    try:
        format_json(input, output, indent=indent, sort_keys=sort)
    except (OSError, ValueError, TypeError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"✅ Formatted -> {output}")


@main.command()
@click.option("-i", "--input", required=True, help="Input JSON file")
@click.option("-o", "--output", required=True, help="New minified JSON file (must not exist)")
def minify(input, output):
    """Minify JSON file (remove all whitespace)."""
    try:
        size = minify_json(input, output)
    except (OSError, ValueError, TypeError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"✅ Minified -> {output} ({size} bytes)")


@main.command()
@click.option("-i", "--input", required=True, help="Input JSON file")
@click.option(
    "--reject-duplicates",
    is_flag=True,
    help="Fail when an object repeats a key. The default keeps the last value.",
)
@click.pass_context
def validate(ctx, input, reject_duplicates):
    """Validate JSON file syntax."""
    valid, error = validate_json(input, reject_duplicate_keys=reject_duplicates)
    if valid:
        click.echo("✅ Valid JSON")
        return
    click.echo(f"❌ Invalid JSON: {error}", err=True)
    ctx.exit(1)


@main.command()
@click.option("-i", "--input", required=True, help="Input JSON file")
@click.option("-p", "--path", required=True, help="Dot-separated path (e.g. 'user.name')")
def query(input, path):
    """Query JSON by dot-separated path."""
    try:
        result = query_path(input, path)
        click.echo(_dumps_json(result, indent=2))
    except (OSError, ValueError, TypeError) as error:
        raise click.ClickException(str(error)) from error


if __name__ == "__main__":
    main()
