from collections import namedtuple
from app.sensor.sht40.base_sensor import check_value

# differential input (bool)
# resolution in bits (int)
# reference voltage in volts (float)
# number of analog inputs (channels)
adc_base_props = namedtuple("adc_props", "ref_voltage resolution channels differential_channels")
# ADC channel info tuple: number(channel number):int, is_differential(differential mode):bool
adc_channel_info = namedtuple("adc_channel_info", "number is_differential")
# ADC channels count information tuple
# channels - number of single ended channels
# differential_channels - number of differential channels
adc_channels = namedtuple("adc_channels", "channels differential_channels")
# ADC main properties: reference voltage in Volts, current bit resolution,
# maximum bit resolution, current channel number, number of single ended channels,
# maximum single ended channels, maximum differential channels,
# current sample rate in Hz
adc_general_props = namedtuple(
    "adc_general_props", "ref_voltage resolution max_resolution current_channel channels diff_channels"
)
# Basic raw settings common to all ADCs
adc_general_raw_props = namedtuple("adc_general_raw_props", "sample_rate gain_amplifier single_shot_mode")

# ADC initialization parameters
# reference_voltage - reference voltage in Volts
# max_resolution - maximum bit resolution. Resolution is often dynamic(!)
# Depends on analog-to-digital conversion frequency _data_rate (Hz)
# channels - number of single ended channels
# differential_channels - number of differential channels
# differential_mode - If true, this is a differential ADC. For get_lsb method.
adc_init_props = namedtuple(
    "adc_init_props", "reference_voltage max_resolution channels differential_channels differential_mode"
)
# For get_raw_value_ex method
# value - raw ADC value
# low_limit - True if ADC reading is at bottom of scale (underflow)
# hi_limit - True if ADC reading is at top of scale (overflow)
raw_value_ex = namedtuple("raw_value_ex", "value low_limit hi_limit")


# Computes raw limit values read from ADC register
def _get_reg_raw_limits(adc_resolution: int, differential: bool) -> raw_value_ex:
    if differential:
        # for differential ADCs
        _base = 2 ** (adc_resolution - 1)
        return raw_value_ex(value=0, low_limit=_base, hi_limit=_base - 1)
    # for single ended ADCs
    return raw_value_ex(value=0, low_limit=0, hi_limit=2**adc_resolution - 1)


class ADC:
    def __init__(self, init_props: adc_init_props, model: str = None):
        """reference_voltage - reference voltage in Volts;
        max_resolution - maximum ADC resolution in bits;
        channels - number of input analog channels;
        differential_channels - number of input analog differential channels;
        model - ADC model as a string"""
        self.init_props = init_props
        adc_ip = self.init_props
        if adc_ip.reference_voltage <= 0 or adc_ip.channels < 0 or adc_ip.differential_channels < 0:
            raise ValueError(
                f"Invalid parameter! Reference voltage, V: {adc_ip.reference_voltage}; Number of channels: {adc_ip.channels}/{adc_ip.differential_channels}"
            )
        # current number of analog-to-digital conversions! RAW value!
        # for writing to register
        self._curr_raw_data_rate = None
        # current ADC resolution in bits
        self._curr_resolution = None
        # current channel number. Range 0..self._channels/self._diff_channels. Check in method check_channel_number
        self._curr_channel = None
        # if True, then self._curr_channel is a differential channel, otherwise it is a single ended channel
        self._is_diff_channel = None
        # current gain coefficient (raw). For writing to ADC register
        self._curr_raw_gain = None  # RAW!
        # actual current gain coefficient.
        # assign it in the subclass by recalculating from self._curr_gain. See method Ads1115.get_correct_gain
        self._real_gain = None
        # conversion mode. if True, then ADC performs conversion on request,
        # otherwise ADC performs conversions automatically at a certain frequency (_curr_data_rate)
        self._single_shot_mode = None
        # low power mode
        self._low_pwr_mode = None
        # string model name of ADC
        self._model_name = model

    @property
    def model(self) -> str:
        """String model name of ADC"""
        return self._model_name

    def get_general_props(self) -> adc_general_props:
        """Returns main properties of ADC"""
        ipr = self.init_props
        return adc_general_props(
            ipr.reference_voltage,
            self.current_resolution,
            ipr.max_resolution,
            self._curr_channel,
            ipr.channels,
            ipr.differential_channels,
        )

    def get_general_raw_props(self) -> adc_general_raw_props:
        """Returns main raw properties of ADC, read from register"""
        return adc_general_raw_props(
            sample_rate=self._curr_raw_data_rate,
            gain_amplifier=self._curr_raw_gain,
            single_shot_mode=self._single_shot_mode,
        )

    def get_specific_props(self):
        """Returns specific properties of ADC, preferably as a named tuple.
        To be overridden in subclass"""
        raise NotImplemented

    def check_channel_number(self, value: int, diff: bool) -> int:
        """Checks the ADC input analog channel number(value) for correctness.
        If diff is True, then the channel is differential(!).
        value should be in range 0..self._channels/self._diff_channels"""
        ipr = self.init_props
        _max = ipr.differential_channels if diff else ipr.channels
        check_value(
            value, range(_max), f"Invalid ADC channel number: {value}; diff: {diff}. Valid range: 0..{_max - 1}"
        )
        return value

    def check_gain_raw(self, gain_raw: int) -> int:
        """Checks raw gain for correctness. Raises exception on error!
        Returns gain_raw on success! To be overridden in subclass."""
        raise NotImplemented

    def check_data_rate_raw(self, data_rate_raw: int) -> int:
        """Checks raw data_rate for correctness. Raises exception on error!
        Returns data_rate_raw on success! To be overridden in subclass."""
        raise NotImplemented

    def get_lsb(self) -> float:
        """Returns the least significant bit value in Volts depending on current ADC settings.
        gain - gain coefficient of the input divider of ADC, should be greater than zero!"""
        ipr = self.init_props
        _k = 2 if ipr.differential_mode else 1
        return _k * ipr.reference_voltage / (self.gain * 2**self.current_resolution)

    def get_conversion_cycle_time(self) -> int:
        """Returns the conversion time in [us/ms] of analog value to digital depending on current ADC settings.
        To be overridden for each ADC!"""
        raise NotImplemented

    @property
    def general_properties(self) -> adc_general_props:
        return self.get_general_props()

    @property
    def value(self) -> float:
        """Returns the value of the current channel in Volts"""
        return self.get_value(raw=False)

    def get_raw_value(self) -> int:
        """Returns the raw ADC value.
        To be overridden in subclasses!"""
        raise NotImplemented

    def get_raw_value_ex(self, delta: int = 5) -> raw_value_ex:
        """Returns the raw ADC value and overflow flags.
        To be overridden in subclasses!
        delta - 'gap'"""
        raw = self.get_raw_value()
        limits = _get_reg_raw_limits(self.current_resolution, self.init_props.differential_mode)
        return raw_value_ex(
            value=raw,
            low_limit=raw in range(limits.low_limit, 1 + delta + limits.low_limit),
            hi_limit=raw in range(limits.hi_limit - delta, 1 + limits.hi_limit),
        )

    def raw_value_to_real(self, raw_val: int) -> float:
        """Converts raw ADC value from register to value in Volts"""
        return raw_val * self.get_lsb()

    def gain_raw_to_real(self, raw_gain: int) -> float:
        """Converts raw gain value to real gain.
        To be overridden in subclass!"""
        raise NotImplemented

    def get_value(self, raw: bool = True) -> float:
        """Returns the value of the current channel in Volts if raw is False, in code if raw is True"""
        val = self.get_raw_value()
        if raw:
            return val
        return self.raw_value_to_real(val)

    def get_resolution(self, raw_data_rate: int) -> int:
        """Returns the bit resolution of ADC depending on the sampling rate (raw value!).
        To be overridden in subclass!"""
        raise NotImplemented

    def get_current_channel(self) -> adc_channel_info:
        """Returns information about the current active ADC channel"""
        return adc_channel_info(number=self._curr_channel, is_differential=self._is_diff_channel)

    @property
    def channel(self) -> adc_channel_info:
        """Returns information about the current channel"""
        return self.get_current_channel()

    def __len__(self) -> int:
        """Returns the number of ADC analog channels depending on the type of current channel.
        If the current channel is differential, returns the number of differential channels, otherwise
        returns the number of single ended channels"""
        ipr = self.init_props
        return ipr.differential_channels if self._is_diff_channel else ipr.channels

    def start_measurement(
        self, single_shot: bool, data_rate_raw: int, gain_raw: int, channel: int, differential_channel: bool
    ):
        """Starts single-shot(single_shot is True) or continuous(single_shot is False) measurement.
        data_rate_raw - ADC sampling rate in samples per second, RAW parameter, see datasheet bit field!
        gain_raw - gain coefficient of input analog voltage, RAW parameter, see datasheet bit field!
        channel - analog input number. From 0 to self._channels/self._diff_channels - 1
        differential_channel - if True, then the channel with number channel is differential(!)
        Note! Always call the raw_config_to_adc_properties method as the last line of this method
        to write values to the corresponding class fields!
        This method is unlikely to need overriding, but it can be done if necessary."""
        self.check_gain_raw(gain_raw=gain_raw)  # check for correctness
        self.check_data_rate_raw(data_rate_raw=data_rate_raw)  # check for correctness
        self.check_channel_number(channel, differential_channel)  # check for correctness
        #
        self._single_shot_mode = single_shot
        self._curr_raw_data_rate = data_rate_raw
        self._curr_raw_gain = gain_raw
        self._curr_channel = channel
        self._curr_resolution = self.get_resolution(data_rate_raw)
        self._is_diff_channel = differential_channel
        # overridden for each ADC, methods
        _raw_cfg = self.adc_properties_to_raw_config()
        self.set_raw_config(_raw_cfg)
        # read ADC config and update class fields
        _raw_cfg = self.get_raw_config()  # read ADC settings
        self.raw_config_to_adc_properties(_raw_cfg)  # update class instance fields
        # recalculate to real gain
        self._real_gain = self.gain_raw_to_real(self._curr_raw_gain)

    def raw_config_to_adc_properties(self, raw_config: int):
        """Returns current sensor settings from the number returned by get_raw_config(!) to class fields(!).
        raw_config -> adc_properties.
        To be overridden in subclass!"""
        raise NotImplemented

    def adc_properties_to_raw_config(self) -> int:
        """Converts ADC properties from class fields to raw ADC configuration.
        adc_properties -> raw_config.
        To be overridden in subclass!"""
        raise NotImplemented

    def get_raw_config(self) -> int:
        """Returns(reads) current sensor settings from registers(configuration) as a number.
        To be overridden in subclass!"""
        raise NotImplemented

    def set_raw_config(self, value: int):
        """Writes settings(value) to the internal memory/register of the sensor.
        To be overridden in subclass!"""
        raise NotImplemented

    def raw_sample_rate_to_real(self, raw_sample_rate: int) -> float:
        """Converts raw sampling rate value to [Hz].
        To be overridden in subclass!"""
        raise NotImplemented

    @property
    def sample_rate(self) -> float:
        """Returns the current number of samples per second"""
        return self.raw_sample_rate_to_real(self.current_sample_rate)

    @property
    def current_sample_rate(self) -> int:
        """Returns the current raw(!) number of ADC samples"""
        return self._curr_raw_data_rate

    @property
    def current_raw_gain(self) -> int:
        """Returns the current raw(!) gain coefficient of ADC"""
        return self._curr_raw_gain

    @property
    def gain(self) -> float:
        """Returns the current real gain coefficient of ADC"""
        return self._real_gain

    @property
    def current_resolution(self) -> int:
        """Returns the current(!) bit resolution of ADC"""
        return self._curr_resolution

    @property
    def single_shot_mode(self) -> bool:
        """Returns True if ADC is set to single shot conversion mode,
        otherwise continuous conversion mode"""
        return self._single_shot_mode
