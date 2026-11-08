import sys
import uuid

from tasks import fail_order, process_order, retry_order

TASKS = {
    "success": process_order,
    "failure": fail_order,
    "retry": retry_order,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in TASKS:
        print("Usage: python enqueue.py [success|failure|retry]")
        raise SystemExit(1)

    scenario = sys.argv[1]
    order_id = str(uuid.uuid4())

    task = TASKS[scenario].delay(order_id)

    print(f"Scenario: {scenario}")
    print(f"Order ID: {order_id}")
    print(f"Celery task ID: {task.id}")


if __name__ == "__main__":
    main()