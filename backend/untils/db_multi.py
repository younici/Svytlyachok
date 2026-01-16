import untils.subcription as sub
import redis_db
import db.orm.utils as db

async def delete_tg_sub(id: int):
    subAnsw = sub.forget_telegram_subscription(id)
    redisAnsw = await redis_db.delete_tg_subscription(id)
    dbAnsw = await db.delete_tg_subscriber(id)
    return subAnsw, redisAnsw, dbAnsw

async def delete_web_sub(endpoint):
    subAnsw = sub.forget_push_subscription(endpoint)
    redisAnsw = await redis_db.delete_push_subscription(endpoint)
    dbAnsw = await db.delete_sub(endpoint)
    return subAnsw, redisAnsw, dbAnsw