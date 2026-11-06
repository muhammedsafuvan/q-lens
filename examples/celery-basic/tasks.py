from app import app


@app.task(name="orders.process")
def process_order(order_id: str):
    print(f"Processing order: {order_id}")

    return {
        "order_id": order_id,
        "status": "completed",
    }


@app.task(name="orders.fail")
def fail_order(order_id: str):
    print(f"Processing order that will fail: {order_id}")

    raise RuntimeError(f"Unable to process order {order_id}")


@app.task(
    bind=True,
    name="orders.retry",
    max_retries=1,
)
def retry_order(self, order_id: str):
    print(
        f"Processing order: {order_id}, "
        f"attempt: {self.request.retries + 1}"
    )

    if self.request.retries == 0:
        raise self.retry(
            exc=RuntimeError("Temporary payment gateway failure"),
            countdown=2,
        )

    return {
        "order_id": order_id,
        "status": "completed_after_retry",
        "attempt": self.request.retries + 1,
    }