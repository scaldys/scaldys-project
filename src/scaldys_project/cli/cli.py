# -*- coding: utf-8 -*-

import logging

import typer
from rich.logging import RichHandler

import scaldys_project.cli.commands.cmd_build as cmd_build
import scaldys_project.cli.commands.cmd_check as cmd_check
import scaldys_project.cli.commands.cmd_ci as cmd_ci
import scaldys_project.cli.commands.cmd_test as cmd_test
from scaldys_project.cli.utils import console

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console, show_path=False, markup=True)],
)

app = typer.Typer(help="Scaldys Builder", no_args_is_help=True)

app.add_typer(cmd_build.build_app, name="build")
app.add_typer(cmd_ci.ci_app, name="ci")
app.command("check")(cmd_check.check)
app.command("test")(cmd_test.test)
