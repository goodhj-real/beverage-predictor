from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime, timedelta
from pytz import timezone
import random, os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return FileResponse(os.path.join("frontend", "index.html"))

# 전역 변수들
MENU_TIME = {
    "아메리카노": 60,
    "카페라떼": 90,
    "바닐라라떼": 100,
    "콜드브루": 80,
    "초코라떼": 120
}
orders = []
completed_orders = []
order_id_counter = 1
last_order_time = datetime.now(timezone('Asia/Seoul'))  # 전역 선언 위치 맞게!

# 주문 생성
@app.get("/orders")
def get_orders():
    global order_id_counter, last_order_time

    now = datetime.now(timezone('Asia/Seoul'))
    if (now - last_order_time).total_seconds() >= 5:
        menu_count = random.randint(1, 3)
        menus = random.choices(list(MENU_TIME.keys()), k=menu_count)
        duration_total = sum([MENU_TIME[m] for m in menus])
        predicted = now + timedelta(seconds=duration_total)

        order = {
            "order_id": order_id_counter,
            "menus": menus,
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "predicted": predicted.strftime("%Y-%m-%d %H:%M:%S")
        }
        orders.append(order)
        print(f"[주문 생성] {order}")
        order_id_counter += 1
        last_order_time = now

    return orders
