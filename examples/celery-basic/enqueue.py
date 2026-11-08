import sys
import uuid

from celery import current_app
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

    task = TASKS[sys.argv[1]]
    order_id = str(uuid.uuid4())

    print("Broker:", task.app.conf.broker_url)
    print("Task:", task.name)

    result = task.apply_async(args=[order_id])

    print("Scenario:", sys.argv[1])
    print("Order ID:", order_id)
    print("Celery task ID:", result.id)
    print("Task state:", result.state)


if __name__ == "__main__":
    main()