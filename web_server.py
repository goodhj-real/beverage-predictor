from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime, timedelta
import random, os

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# index.html 반환
@app.get("/")
def root():
    return FileResponse(os.path.join("frontend", "index.html"))

# 메뉴별 소요 시간 설정 (초)
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

# 주문 생성
@app.get("/orders")
def get_orders():
    global order_id_counter

    if random.random() < 0.3:
        menu_count = random.randint(1, 3)
        menus = random.choices(list(MENU_TIME.keys()), k=menu_count)
        duration_total = sum([MENU_TIME[m] for m in menus])

        now = datetime.now()
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

    return orders

# 지연 추가
@app.post("/delay")
def delay_order(order_id: int = Query(...), minutes: int = Query(...)):
    for order in orders:
        if order["order_id"] == order_id:
            predicted_dt = datetime.strptime(order["predicted"], "%Y-%m-%d %H:%M:%S")
            new_time = predicted_dt + timedelta(minutes=minutes)
            order["predicted"] = new_time.strftime("%Y-%m-%d %H:%M:%S")
            return {"status": "ok", "new_predicted": order["predicted"]}
    return {"status": "error", "message": "Order not found"}

# 완료 처리
@app.post("/complete")
def complete_order(order_id: int = Query(...)):
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    for order in orders:
        if order["order_id"] == order_id:
            order["actual"] = now_str

            predicted_time = datetime.strptime(order["predicted"], "%Y-%m-%d %H:%M:%S")
            diff = (now - predicted_time).total_seconds()

            if diff >= 0:
                completed_orders.append({
                    "order_id": order_id,
                    "menus": order["menus"],
                    "predicted": order["predicted"],
                    "actual": now_str,
                    "delay_seconds": diff
                })
                print(f"[제조 완료] 주문 {order_id} 늦음 → {now_str} (지연 {diff:.1f}초)")
            else:
                print(f"[제조 완료] 주문 {order_id} 빠름 → {now_str} (예상보다 {-diff:.1f}초 빠름)")

            return {"status": "ok", "completed": now_str}

    return {"status": "error", "message": "Order not found"}

# 모니터링 분석 요약
@app.get("/summary")
def summary():
    if not completed_orders:
        return {"status": "empty", "message": "완료된 주문이 없습니다."}

    max_tolerated = 180
    total_accuracy = 0
    total_delay = 0

    for record in completed_orders:
        delay = record["delay_seconds"]
        accuracy = max(0, 1 - delay / max_tolerated)
        total_accuracy += accuracy
        total_delay += delay

    average_accuracy = (total_accuracy / len(completed_orders)) * 100
    average_delay = total_delay / len(completed_orders)

    return {
        "status": "ok",
        "average_accuracy_percent": round(average_accuracy, 1),
        "average_delay_seconds": round(average_delay, 1)
    }
