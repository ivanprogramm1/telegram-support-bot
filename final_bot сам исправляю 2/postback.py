from fastapi import FastAPI, Request
from datetime import datetime
from db import upsert_trader_field
from config import POSTBACK_SECRET

app = FastAPI()


@app.get("/")
async def health_check():
    # Простой эндпоинт, чтобы Railway видел, что сервис живой
    return {"status": "ok"}


@app.get("/postback")
async def receive_postback(request: Request):
    """
    Принимает постбеки от Pocket Partners.

    Настройте в кабинете Pocket Partners URL постбека вида:

    Регистрация:
    https://ВАШ-ДОМЕН/postback?event=reg&trader_id={trader_id}&country={country}&date_time={date_time}&link_type={link_type}

    Подтверждение email:
    https://ВАШ-ДОМЕН/postback?event=email_confirm&trader_id={trader_id}

    FTD (первый депозит):
    https://ВАШ-ДОМЕН/postback?event=ftd&trader_id={trader_id}&sumdep={sumdep}&date_time={date_time}

    Повторный депозит:
    https://ВАШ-ДОМЕН/postback?event=redeposit&trader_id={trader_id}&sumdep={sumdep}

    Комиссия:
    https://ВАШ-ДОМЕН/postback?event=commission&trader_id={trader_id}&commission={commission}

    Вывод средств:
    https://ВАШ-ДОМЕН/postback?event=withdrawal&trader_id={trader_id}&wdr_sum={wdr_sum}&status={status}

    Если задан POSTBACK_SECRET в переменных окружения — добавьте в конец
    каждого URL &secret=ВАШ_СЕКРЕТ, иначе запрос будет отклонён.
    """
    params = dict(request.query_params)

    if POSTBACK_SECRET:
        if params.get("secret") != POSTBACK_SECRET:
            return {"status": "error", "reason": "invalid secret"}

    trader_id = params.get("trader_id")
    if not trader_id:
        return {"status": "error", "reason": "trader_id is required"}

    event = params.get("event", "")
    now = datetime.utcnow().isoformat()

    fields = {}

    if event == "reg":
        fields["reg_date"] = params.get("date_time", now)
        fields["country"] = params.get("country", "")
        fields["link_type"] = params.get("link_type", "")
        fields["verified"] = "No"

    elif event == "email_confirm":
        fields["activity_date"] = params.get("date_time", now)

    elif event == "ftd":
        fields["ftd_amount"] = params.get("sumdep", "")
        fields["ftd_date"] = params.get("date_time", now)
        fields["count_of_deposits"] = "1"
        fields["sum_of_deposits"] = params.get("sumdep", "")

    elif event == "redeposit":
        # Копим сумму депозитов и счётчик. Для простоты — читаем текущие,
        # прибавляем новую сумму (в проде лучше делать это одним SQL-запросом).
        from db import get_trader

        existing = await get_trader(trader_id)
        prev_sum = float(existing.get("sum_of_deposits") or 0) if existing else 0
        prev_count = int(existing.get("count_of_deposits") or 0) if existing else 0
        new_dep = float(params.get("sumdep", 0) or 0)

        fields["sum_of_deposits"] = str(prev_sum + new_dep)
        fields["count_of_deposits"] = str(prev_count + 1)
        fields["activity_date"] = params.get("date_time", now)

    elif event == "commission":
        fields["commission"] = params.get("commission", "")

    elif event == "withdrawal":
        fields["activity_date"] = params.get("date_time", now)
        # Статус вывода можно логировать отдельно при желании расширения схемы

    else:
        return {"status": "error", "reason": f"unknown event: {event}"}

    await upsert_trader_field(trader_id, **fields)

    return {"status": "ok", "trader_id": trader_id, "event": event}
