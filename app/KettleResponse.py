import struct

from app.Protocol import calc_msg_checksum, format_hex_msg_string
from const.protocol import *


class KettleResponse:

    def unpack_response(self, msg, print_msg=False, print_stat_msg=False, print_keep_connect=True):
        """Decides which function should format the message

        Args:
            print_stat_msg: print the heartbeat status messages ('aa0018...'). Useful to set to False
                to filter out heartbeat status when debugging conversations betweeen app and kettle
            print_keep_connect: print the KeepConnect messages sent/received
        """
        if msg == "KeepConnect":
            if print_keep_connect:
                print("KeepConnect")
            return None

        if not isinstance(msg, dict):
            print("Unkwn binary msg:", msg)
            return None

        if "wifi_cmd" in msg:
            return self.unpack_command(msg["data3"], print_msg, print_stat_msg, "K")

        if "app_cmd" in msg:
            return self.unpack_command(msg["data2"], print_msg, print_stat_msg, "A")

        print("Unkwn dict msg:", msg)
        return None

    def unpack_command(self, msg, print_msg=True, print_stat_msg=True, cmd_sender="U"):
        """Formats a message received from the kettle.

           Returns a json dict with the data parsed
        """

        msg_bytes = bytes.fromhex(msg)

        cmd_header = self.unpack_bytes(msg_bytes[:15], CMD_HEADER_STRUCT)

        if len(msg_bytes) != (cmd_header["length"] + 3):
            # +3: 3 bytes for the heading are not included in "length" field
            print("Length does not match the received packet, ignoring msg:", msg)
            return {"": ""}

        msg_checksum = calc_msg_checksum(msg)
        cmd_checksum = int.from_bytes(
            msg_bytes[-1:], byteorder="big"
        )  # last byte = checksum byte

        if cmd_checksum != msg_checksum:
            print("Bad checksum, ignoring msg:", msg)
            return {"": ""}

        cmd_name = "UNKN"
        cmd_ack = None
        cmd_frame = None

        if cmd_header["length"] >= 14:  # short commands don't have an ack byte
            cmd_ack = {"ack": msg_bytes[15:16]}

        cmd_name, cmd_frame_parser_struct = CMD_PARSER.get(cmd_header["cmd"], ("unk", ""))

        if cmd_header["length"] >= 16:  # longer commands have a cmd frame
            cmd_frame = self.unpack_bytes(msg_bytes[16:-1], cmd_frame_parser_struct)

        # form dictionary with all the info we parsed:
        cmd_dict = cmd_header
        if cmd_frame is not None:
            cmd_dict.update(cmd_frame)
        if cmd_ack is not None:
            cmd_dict.update(cmd_ack)

        cmd_dict["cmd"] = cmd_name
        if "status" in cmd_dict:
            cmd_dict["status"] = STATES_MAP[cmd_frame["status"]]
            cmd_dict.update({"power": ONOFF_MAP[cmd_frame["status"]]})

        if cmd_name == "K_ON":
            cmd_dict.update({"power": "ON"})

        if cmd_name == "KOFF":
            cmd_dict.update({"power": "OFF"})

        if print_msg and (print_stat_msg or cmd_name != "STAT"):
            ## prepare the spacing for the space formatted debug print of msg ##
            msg_parser_struct = (
                    CMD_HEADER_STRUCT
                    + ((("cmd_ack", "c"),) if cmd_ack is not None else (("", ""),))
                    + (cmd_frame_parser_struct if cmd_frame is not None else (("", ""),))
                    + (("checksum", "B"),)
            )
            print(cmd_sender, "-", cmd_name, sep="", end=": ")
            print(format_hex_msg_string(msg, msg_parser_struct))

        return cmd_dict

    def unpack_bytes(self, msg_bytes, parser_struct):
        """Returns a dictionary parsing the message with the relevant format"""
        parser_format = ">" + "".join(  # ">" = big endian
            [x for _, x in parser_struct]  # extract second item in each tuple
        )
        cmd_values = struct.unpack(parser_format, msg_bytes)
        cmd_keys = [key for key, fmt in parser_struct if "x" not in fmt]
        # extract first item in each tuple as long as format is not "x" (skip)
        if len(cmd_keys) == len(cmd_values):
            return dict(zip(cmd_keys, cmd_values))

        print("Error unpacking")
        return {"": ""}
