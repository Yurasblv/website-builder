import typer

from .done import app as done_app
from .ready import app as ready_app
from .status import app as status_app

app = typer.Typer()

app.add_typer(done_app)
app.add_typer(ready_app)
app.add_typer(status_app)
