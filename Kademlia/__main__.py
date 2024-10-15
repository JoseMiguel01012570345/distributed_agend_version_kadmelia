import sys
from KademliaNode import KademliaNode
from KBucket import Node, sha1_hash
import os
import time

default_nodes = [
    ("172.18.0.2", 8080),
    ("172.18.0.3", 8080),
    ("172.18.0.4", 8080),
    ("172.18.0.8", 8080),
    ("172.18.0.5", 8080),
    ("172.18.0.9", 8080),
]


def main():
    ip = os.getenv("NODE_IP", "127.0.0.1")  # Valor por defecto es 127.0.0.1
    port = int(os.getenv("NODE_PORT", "8080"))
    node = KademliaNode(ip, port)
    node.start()
    print(node.ping(Node("0.0.0.0", 0)))
    # for ip, port in default_nodes:
    #     print(node.ping(Node(ip, port)))
    while True:
        file_direction = input("ip: ")
        node.store_a_file(file_direction)
        time.sleep(1)


if __name__ == "__main__":
    main()
