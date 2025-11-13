import typer
from asgiref.sync import async_to_sync

from .utils import get_count_in_progress

app = typer.Typer()


@app.command()
def status():
    func = async_to_sync(get_count_in_progress)
    num = func()

    _ready = num == 0
    color = typer.colors.GREEN if _ready else typer.colors.RED
    typer.secho(_ready, fg=color)
