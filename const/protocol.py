# states: 0 = kettle not on base, 2 = on the base "standby" mode (display off, app shows "zzz")
#         3 = on base ready to go, 4 = heating on
STATES_MAP = ("Not on base", "TBD?", "Standby", "Ready", "Heating", "Keep Warm")
ONOFF_MAP = ("OFF", "OFF", "OFF", "OFF", "ON", "OFF")
ACK_OK = b"\xc8"

CMD_HEADER_STRUCT = (
    ("head", "c"),
    ("length", "h"),
    ("b03", "B"),
    ("pad", "xxxx"),
    ("pad", "x"),
    ("b090A", "h"),
    ("seq", "B"),
    ("cmd", "c"),
    ("pad", "xx"),
)

CMD_STATUS_STRUCT = (
    ("pad", "x"),
    ("status", "B"),
    ("keep_warm_secs", "h"),
    ("temperature", "B"),
    ("target_temp", "B"),
    ("volume", "h"),
    ("pad", "xx"),
)

CMD_ON_STRUCT = (
    ("target_temp", "B"),
    ("keep_warm_secs", "B"),
    ("pad", "xx"),
)

CMD_UNKNOWN_STRUCT = (("unk", "Command not yet parsed / unknown"),)

CMD_PARSER = {
    b"\x36": ("STAT", CMD_STATUS_STRUCT),
    b"\x39": ("K_ON", CMD_ON_STRUCT),
    b"\x3A": ("KOFF", None),  # this cmd has no frame
    b"\x41": ("WAKE", None),  # this cmd has no frame
    b"\x43": ("TIM1", CMD_UNKNOWN_STRUCT),  # something to do with timers
    b"\x44": ("TIM2", CMD_UNKNOWN_STRUCT),  # something to do with timers
    b"\xa4": ("INIT", None),  # this is the initial connection msg - ignored
}
