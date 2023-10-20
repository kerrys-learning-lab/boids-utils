"""
Exceptions raised by the pubsub module
"""

class NoSuchTopicPublisher(RuntimeError):
    """
    Raised when a caller attempts to retrieve and use a TopicPublisher
    which has not been configured.
    """

class NoSuchTopicConsumer(RuntimeError):
    """
    Raised when a caller attempts to subscribe to a topic which has not
    been configured.
    """
