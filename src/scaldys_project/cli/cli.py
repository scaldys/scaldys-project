
import logging

import typer
from rich.logging import RichHandler

from scaldys_project.cli.commands import (
    cmd_build,
    cmd_check,
    cmd_ci,
    cmd_format,
    cmd_init,
    cmd_publish,
    cmd_test,
)
from scaldys_project.cli.utils import console

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console, show_path=False, markup=True)],
)

app = typer.Typer(help="Scaldys Project", no_args_is_help=True)

app.add_typer(cmd_build.build_app, name="build")
app.add_typer(cmd_ci.ci_app, name="ci")
app.add_typer(cmd_format.format_app, name="format")
app.command("check")(cmd_check.check)
app.command("init")(cmd_init.init)
app.command("publish")(cmd_publish.publish)
app.command("test")(cmd_test.test)
