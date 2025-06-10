from dateutil.parser import isoparse
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
last_order_time = datetime.now(timezone('Asia/Seoul')) - timedelta(seconds=5)
is_operating = False

@app.post("/start")
def start_operation():
    global is_operating
    is_operating = True
    return {"status": "ok"}

# 주문 생성
# 주문 생성 - 수정된 버전
@app.get("/orders")
def get_orders():
    global order_id_counter, last_order_time

    if not is_operating:
        return orders

    now = datetime.now(timezone('Asia/Seoul'))
    if (now - last_order_time).total_seconds() >= 5:
        # --- 로직 변경 시작 ---

        # 새 주문의 시작 시간을 결정합니다.
        # 대기 중인 주문이 없다면 '현재 시간', 있다면 '마지막 주문의 예상 완료 시간'을 기준으로 합니다.
        if orders:
            last_order_predicted_time = isoparse(orders[-1]["predicted"])
            # 만약 마지막 주문이 이미 끝났어야 할 시간이라면, 현재 시간을 시작점으로 합니다.
            start_time = max(now, last_order_predicted_time)
        else:
            start_time = now

        menu_count = random.randint(1, 3)
        menus = random.choices(list(MENU_TIME.keys()), k=menu_count)
        duration_total = sum([MENU_TIME[m] for m in menus])
        
        # 새로운 예상 완료 시간은 '결정된 시작 시간' + '음료 제조 시간'이 됩니다.
        predicted = start_time + timedelta(seconds=duration_total)
        

        order = {
            "order_id": order_id_counter,
            "menus": menus,
            "time": now.isoformat(), 
            "predicted": predicted.isoformat()
        }
        orders.append(order)
        print(f"[주문 생성] {order}")
        order_id_counter += 1
        last_order_time = now

    return orders

# 지연 추가
@app.post("/delay")
def delay_order(order_id: int = Query(...), minutes: int = Query(...)):
    target_index = None

    for idx, order in enumerate(orders):
        if order["order_id"] == order_id:
            target_index = idx
            predicted_dt = isoparse(order["predicted"])
            new_time = predicted_dt + timedelta(minutes=minutes)
            order["predicted"] = new_time.isoformat()
            break

    if target_index is None:
        return {"status": "error", "message": "Order not found"}

    for i in range(target_index + 1, len(orders)):
        pred = isoparse(orders[i]["predicted"])
        new_pred = pred + timedelta(minutes=minutes)
        orders[i]["predicted"] = new_pred.isoformat()

    return {"status": "ok", "new_predicted": orders[target_index]["predicted"]}

# 제조 완료 처리
@app.post("/complete")
def complete_order(order_id: int = Query(...)):
    now = datetime.now(timezone('Asia/Seoul'))
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    for order in orders:
        if order["order_id"] == order_id:
            order["actual"] = now_str

            predicted_time = isoparse(order["predicted"])
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("web_server:app", host="0.0.0.0", port=port)
