""" Common utilities """
import datetime
import json
import json.encoder
import random
import uuid

COMPACT_SEPARATORS = (",", ":")

DATE_TIME_FORMAT="%Y-%m-%dT%H:%M:%SZ"

def mk_uuid():
    """ Returns a string representation of a v4 UUID """
    return str(uuid.uuid4())

def nowutc(stringify = False) -> datetime.datetime:
    """ Returns the current time in UTC, either as a string (when stringify is
        True) or datetime.
    """
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    return now.strftime(DATE_TIME_FORMAT) if stringify else now

def str_to_datetime(datetime_str):
    """ Converts the given datetime_str to a datetime.datetime object (in UTC) """
    datetime_obj = datetime.datetime.strptime(datetime_str, DATE_TIME_FORMAT)
    return datetime_obj.replace(tzinfo=datetime.timezone.utc)

class Serde:
    """
    Serialization/deserialization utilities.
    """

    @staticmethod
    def serialize_json_value(value: any):
        """
        Serializes the given JSON value to string
        """
        return Serde.to_json(value).encode('utf-8') if value else None

    @staticmethod
    def deserialize_json_value(value: bytes):
        """
        Deserializes the given value to JSON
        """
        return json.loads(value.decode('utf-8')) if value else None

    @staticmethod
    def to_json(obj, **kwargs):
        """
        Encodes the given object to JSON, trying several techniques depending
        on the 'type' of the given object.

        - datetime.datetime - Converts to ISO-formatted string
        - set[Any] - Converts to list[Any]
        - other - Attempts to call other.to_json()
        """
        try:
            if isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()

            if isinstance(obj, set):
                return json.dumps(list(obj),
                                  separators=COMPACT_SEPARATORS,
                                  default=Serde.to_json,
                                  **kwargs)

            if isinstance(obj, dict):
                return json.dumps(obj,
                                  separators=COMPACT_SEPARATORS,
                                  default=Serde.to_json,
                                  **kwargs)

            return obj.to_json()
        except AttributeError:
            # pylint: disable-next=raise-missing-from
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class Range:
    """ Represents range criteria """
    def __init__(self, range_min=0.0, range_max=1.0, inclusive=True, **kwargs):
        self.min = range_min
        self.max = range_max
        self._min_inclusive = kwargs.get('min-inclusive') if 'min-inclusive' in kwargs else inclusive
        self._max_inclusive = kwargs.get('max-inclusive') if 'max-inclusive' in kwargs else inclusive

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Range):
            return self.min == other.min and self.max == other.max
        return False

    def __contains__(self, value) -> bool:
        min_test = value >= self.min if self._min_inclusive else value > self.min
        max_test = value <= self.max if self._max_inclusive else value < self.max
        return min_test and max_test

    def random(self, as_int=False):
        """ Returns a random number within this range """
        while True:
            # Returns a number in [self.min, self.max] (i.e. inclusivity is implied)
            value = random.uniform(self.min, self.max)
            value = int(value) if as_int else value

            # Therefore, using our __contains__, loop until the number meets the
            # inclusivity criteria of this instance...
            if value in self:
                return value

    def to_json(self):
        """ Returns a JSON representation of this range """
        return {"min": self.min, "max": self.max}
