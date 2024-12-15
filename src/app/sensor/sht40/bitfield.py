# micropython
# MIT license
# Copyright (c) 2024 Roman Shevchik   goctaprog@gmail.com
"""Bit field representation"""
from collections import namedtuple
from app.sensor.sht40.base_sensor import check_value, get_error_str

# Bit field information as a named tuple
# name: str - name
# position: range - position in bit numbers. position.start = first bit, position.stop-1 = last bit
# valid_values: [range, tuple] - range of valid values, if validation not required, pass None
# description: str - readable description of value stored in bit field, if description not needed, pass None
bit_field_info = namedtuple("bit_field_info", "name position valid_values description")


def _bitmask(bit_rng: range) -> int:
    """returns bitmask for occupied bits"""
    # if bit_rng.step < 0 or bit_rng.start <= bit_rng.stop:
    #    raise ValueError(f"_bitmask: {bit_rng.start}; {bit_rng.stop}; {bit_rng.step}")
    return sum(map(lambda x: 2**x, bit_rng))


class BitFields:
    """Storage for bit field information with index access.
    _source - tuple of named tuples describing bit fields;"""

    def _check(self, fields_info: tuple[bit_field_info, ...]):
        """Checks for correctness of information!"""
        for field_info in fields_info:
            if 0 == len(field_info.name):
                raise ValueError(f"Zero length of bit field name string!; position: {field_info.position}")
            if 0 == len(field_info.position):
                raise ValueError(f"Zero length ('in bits') of bit field!; name: {field_info.name}")

    def __init__(self, fields_info: tuple[bit_field_info, ...]):
        self._check(fields_info)
        self._fields_info = fields_info
        self._idx = 0
        # name of the bit field that will be a parameter in get_value/set_value methods
        self._active_field_name = fields_info[0].name
        # value from which bit fields will be extracted
        self._source_val = 0

    def _by_name(self, name: str) -> [bit_field_info, None]:
        """returns bit field information by its name (name field of named tuple) or None"""
        items = self._fields_info
        for item in items:
            if name == item.name:
                return item

    def _get_field(self, key: [str, int, None]) -> [bit_field_info, None]:
        """for internal use"""
        fi = self._fields_info
        _itm = None
        if isinstance(key, int):
            _itm = fi[key]
        if isinstance(key, str):
            _itm = self._by_name(key)
        return _itm

    def get_field_value(self, field_name: str = None, validate: bool = False) -> [int, bool]:
        """returns bit field value by its name(self.field_name) from self.source."""
        f_name = self.field_name if field_name is None else field_name
        item = self._get_field(f_name)
        if item is None:
            raise ValueError(f"get_field_value. Field with name {f_name} does not exist!")
        pos = item.position
        bitmask = _bitmask(pos)
        val = (self.source & bitmask) >> pos.start  # extract bit range with mask and shift right
        if item.valid_values and validate:
            raise NotImplemented("If you decided to validate the field value upon return, do it yourself!!!")
        if 1 == len(pos):
            return 0 != val  # bool
        return val  # int

    def set_field_value(
        self, value: int, source: [int, None] = None, field: [str, int, None] = None, validate: bool = True
    ) -> int:
        """Writes value to bit range defined by field in source.
        Returns value with modified bit field.
        If field is None, the field name is taken from self._active_field_name property.
        If source is None, the value of the field to be modified is changed in self._source_val property"""
        item = self._get_field(key=field)  #   *
        rng = item.valid_values
        if rng and validate:
            # print(f"DBG: value: {value}; rng: {rng}")
            check_value(value, rng, get_error_str(self.field_name, value, rng))
        pos = item.position
        bitmask = _bitmask(pos)
        src = self._get_source(source) & ~bitmask  # clear bit range
        src |= (value << pos.start) & bitmask  # set bits in specified range
        # print(f"DBG:set_field_value: {value}; {source}; {field}")
        if source is None:
            self._source_val = src
            # print(f"DBG:set_field_value: self._source_val: {self._source_val}")
        return src

    def __getitem__(self, key: [int, str]) -> [int, bool]:
        """returns bit field value from self.source by its name/index"""
        _bfi = self._get_field(key)
        return self.get_field_value(_bfi.name)

    def __setitem__(self, field_name: str, value: [int, bool]):
        """Magic method, calls set_field_value.
        Before calling it, you need to set BitField source properties"""
        self.set_field_value(value=value, source=None, field=field_name, validate=True)  #   *

    def _get_source(self, source: [int, None]) -> int:
        return source if source else self._source_val

    @property
    def source(self) -> int:
        """value from which bit fields will be extracted/modified"""
        return self._source_val

    @source.setter
    def source(self, value):
        """value from which bit fields will be extracted/modified"""
        self._source_val = value

    @property
    def field_name(self) -> str:
        """name of the bit field whose value is extracted/modified by get_value/set_value methods if their
        field parameter is None"""
        return self._active_field_name

    @field_name.setter
    def field_name(self, value):
        """name of the bit field whose value is extracted/modified by get_value/set_value methods if their
        field parameter is None"""
        self._active_field_name = value

    def __len__(self) -> int:
        return len(self._fields_info)

    # iterator protocol
    def __iter__(self):
        return self

    def __next__(self) -> bit_field_info:
        ss = self._fields_info
        try:
            self._idx += 1
            return ss[self._idx - 1]
        except IndexError:
            self._idx = 0  # to allow repeated iteration!
            raise StopIteration
