import typer
from asgiref.sync import async_to_sync

from app.db.redis import redis_pool

app = typer.Typer()


@app.command()
def done():
    redis = async_to_sync(redis_pool.get_redis)()

    redis_del = async_to_sync(redis.delete)
    redis_del("ready_to_deploy")

    typer.secho("Deploy flag cleared after deployment", fg=typer.colors.GREEN)
