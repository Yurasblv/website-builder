import typer
from asgiref.sync import async_to_sync

from app.db.redis import redis_pool

app = typer.Typer()


@app.command()
def ready():
    redis = async_to_sync(redis_pool.get_redis)()

    redis_set = async_to_sync(redis.set)

    if redis_set("ready_to_deploy", "1"):
        typer.secho("true", fg=typer.colors.GREEN)
    else:
        typer.secho("false", fg=typer.colors.RED)
