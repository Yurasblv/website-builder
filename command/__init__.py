import warnings

import typer

from .deploy import app as deploy_app

warnings.filterwarnings("ignore", category=UserWarning)
app = typer.Typer()

app.add_typer(deploy_app, name="deploy")
