import pytest

from lattice_workers.rabbitmq_surface_worker import RabbitMqSurfaceWorker


class Channel:
    def __init__(self):
        self.acks = []
        self.nacks = []

    def basic_ack(self, delivery_tag):
        self.acks.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.nacks.append((delivery_tag, requeue))


class Consumer:
    def __init__(self, error=None):
        self.error = error
        self.messages = []

    def consume(self, message):
        self.messages.append(message)
        if self.error:
            raise self.error


def test_successful_delivery_is_acknowledged_after_consumer_returns():
    channel = Channel()
    consumer = Consumer()

    RabbitMqSurfaceWorker(consumer).handle(channel, 7, b'{"jobId":"job-1"}')

    assert consumer.messages == [{"jobId": "job-1"}]
    assert channel.acks == [7]
    assert channel.nacks == []


def test_invalid_json_is_dead_lettered_without_requeue():
    channel = Channel()

    RabbitMqSurfaceWorker(Consumer()).handle(channel, 8, b'not-json')

    assert channel.acks == []
    assert channel.nacks == [(8, False)]


def test_retryable_consumer_failure_is_requeued_and_propagated():
    channel = Channel()

    with pytest.raises(RuntimeError, match="broker unavailable"):
        RabbitMqSurfaceWorker(Consumer(RuntimeError("broker unavailable"))).handle(channel, 9, b'{"jobId":"job-1"}')

    assert channel.acks == []
    assert channel.nacks == [(9, True)]