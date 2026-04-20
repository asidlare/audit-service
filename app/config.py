import os


class Config:
    CASSANDRA_HOSTS = os.getenv("CASSANDRA_HOSTS").split(",")


config = Config
