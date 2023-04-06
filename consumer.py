import json
from kafka.structs import TopicPartition
from kafka import KafkaConsumer

ORDER_KAFKA_TOPIC = "test"

consumer = KafkaConsumer(
    ORDER_KAFKA_TOPIC, 
    bootstrap_servers="kafka1:29092",api_version=(0, 10, 1),
    value_deserializer=lambda v: json.dumps(v).encode("utf-8"),
    auto_offset_reset='earliest'
)


partitions = consumer.partitions_for_topic(ORDER_KAFKA_TOPIC)
for p in partitions:
    topic_partition = TopicPartition(ORDER_KAFKA_TOPIC, p)
    # Seek offset 0
    consumer.seek(partition=topic_partition, offset=0)
    for msg in consumer:
        print(msg.value.decode("utf-8"))