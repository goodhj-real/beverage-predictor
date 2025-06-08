from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime, timedelta
from pytz import timezone
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

@app.get("/")
def root():
    return FileResponse(os.path.join("frontend", "index.html"))

# 전역 설정
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
last_order_time = datetime.now(timezone('Asia/Seoul'))

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

# 지연 추가 (해당 주문 이후 전부 밀림)
@app.post("/delay")
def delay_order(order_id: int = Query(...), minutes: int = Query(...)):
    target_index = None

    for idx, order in enumerate(orders):
        if order["order_id"] == order_id:
            target_index = idx
            predicted_dt = datetime.strptime(order["predicted"], "%Y-%m-%d %H:%M:%S")
            new_time = predicted_dt + timedelta(minutes=minutes)
            order["predicted"] = new_time.strftime("%Y-%m-%d %H:%M:%S")
            break

    if target_index is None:
        return {"status": "error", "message": "Order not found"}

    for i in range(target_index + 1, len(orders)):
        pred = datetime.strptime(orders[i]["predicted"], "%Y-%m-%d %H:%M:%S")
        new_pred = pred + timedelta(minutes=minutes)
        orders[i]["predicted"] = new_pred.strftime("%Y-%m-%d %H:%M:%S")

    return {"status": "ok", "new_predicted": orders[target_index]["predicted"]}

# 제조 완료 처리
@app.post("/complete")
def complete_order(order_id: int = Query(...)):
    now = datetime.now(timezone('Asia/Seoul'))
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    for order in orders:
        if order["order_id"] == order_id:
            order["actual"] = now_str

            predicted_time = timezone('Asia/Seoul').localize(
                 datetime.strptime(order["predicted"], "%Y-%m-%d %H:%M:%S")
            )
            diff = (now - predicted_time).total_seconds()

            completed_orders.append({
                "order_id": order_id,
                "menus": order["menus"],
                "predicted": order["predicted"],
                "actual": now_str,
                "delay_seconds": round(diff, 1)
            })

            if diff >= 0:
                print(f"[제조 완료] 주문 {order_id} 늦음 → {now_str} (지연 {diff:.1f}초)")
            else:
                print(f"[제조 완료] 주문 {order_id} 빠름 → {now_str} (예상보다 {-diff:.1f}초 빠름)")

            return {"status": "ok", "completed": now_str}

    return {"status": "error", "message": "Order not found"}

# 요약 분석
@app.get("/summary")
def summary():
    if not completed_orders:
        return {"status": "empty", "message": "완료된 주문이 없습니다."}

    summary_list = []
    total_accuracy = 0
    total_delay = 0
    max_tolerated = 180

    for record in completed_orders:
        delay = record["delay_seconds"]
        status = "늦음" if delay > 0 else "빠름"
        accuracy = max(0, 1 - abs(delay) / max_tolerated)

        total_accuracy += accuracy
        total_delay += delay

        summary_list.append({
            "order_id": record["order_id"],
            "menus": record["menus"],
            "predicted": record["predicted"],
            "actual": record["actual"],
            "delay_seconds": delay,
            "status": status
        })

    average_accuracy = (total_accuracy / len(completed_orders)) * 100
    average_delay = total_delay / len(completed_orders)

    return {
        "status": "ok",
        "average_accuracy_percent": round(average_accuracy, 1),
        "average_delay_seconds": round(average_delay, 1),
        "orders": summary_list
    }
