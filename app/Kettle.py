from app.Protocol import calc_msg_checksum, unpack_msg
from const.kettle import *
from app.Socket import KettleSocket


class Kettle:
    def __init__(self, socket: KettleSocket):
        self.socket = socket
        self.payload = {
            "cmd": "unk",
            "status": "unk",
            "keep_warm_secs": 0,
            "keep_warm_onoff": False,
            "temperature": 0,
            "target_temp": 0,
            "set_target_temp": 100,
            "volume": 0,
            "power": "OFF",
            "seq": 0,  # sequence
        }

    def tick(self):
        """Increments seq by 1. To be called when sending something to kettle"""
        self.payload["seq"] = (self.payload["seq"] + 1) % 0xFF  # cap at 1 byte

    def turn_on(self, temp=None):
        if self.payload["status"] != "Ready":
            self.wake()

        if temp is None:
            temp = self.payload["set_target_temp"]

        msg = "AA001200000000000003B7{seq}39000000{temp}{kw}0000".format(
            temp=("%0.2X" % temp),
            kw=("%0.2X" % (KEEP_WARM_MINS * self.payload["keep_warm_onoff"])),
            seq=("%0.2x" % self.payload["seq"]),
        )

        msg = calc_msg_checksum(msg, append=True)
        return self.socket.send_enc(msg, SEND_ENCRYPTED)

    def wake(self):
        """Wake up kettle (status goes to "Ready") and display comes on"""
        self.tick()
        msg = "AA000D00000000000003B7{seq}410000".format(
            seq=("%0.2x" % self.payload["seq"])
        )
        msg = calc_msg_checksum(msg, append=True)
        return self.socket.send_enc(msg, SEND_ENCRYPTED)

    def turn_off(self):
        """Turn off the kettle"""
        self.tick()
        msg = "AA000D00000000000003B7{seq}3A0000".format(
            seq=("%0.2x" % self.payload["seq"])
        )
        msg = calc_msg_checksum(msg, append=True)
        return self.socket.send_enc(msg)

    def update_status(self, msg):
        """Parses a wifi_cmd message to match this class status with the phisical kettle"""
        try:
            cmd_dict = unpack_msg(
                msg, DEBUG_MSG, DEBUG_PRINT_STAT_MSG, DEBUG_PRINT_KEEP_CONNECT
            )
        except ValueError:
            print("Error in decoding: ", cmd_dict)
            return

        if isinstance(msg, (str, bytes, type(None))):
            # decoding didn't return anything interesting for us
            return

        if "data3" in msg:
            try:
                self.payload.update(cmd_dict)
            except ValueError:
                print("Error in data3 cmd_dict: ", cmd_dict)
                return
        elif "data2" in msg:
            # this means it's a message we sent. Only useful for debugging tcpdump traffic
            pass
        else:
            print("Unparsed Json message: ", cmd_dict)
            # unparsed data2/3 status or a message we didn't understand

