import json
import sys

from app.Protocol import unpack_msg
from const.kettle import *
import socket
import time

from lib.helpers import json_encode


class KettleSocket:
    """ This class deals with the connection, encryption and decryption
        of messages sent by an AppKettle
    """

    def __init__(self, sock=None, imei=""):
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(KETTLE_SOCKET_TIMEOUT_SECS)
        else:
            self.sock = sock

        self.connected = False
        self.imei = imei
        self.stat = ""

    def connect(self, host_port):
        """ Attempts to connect to the Kettle """
        attempts = KETTLE_SOCKET_CONNECT_ATTEMPTS
        print("Attempting to connect to socket...")
        while attempts and self.connected is False:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(KETTLE_SOCKET_TIMEOUT_SECS)
                self.sock.connect(host_port)
                self.keep_connect()
                self.connected = True
                return
            except (TimeoutError, OSError) as err:
                print("Socket error: ", err, " | ", attempts, "attempts remaining")
                self.kettle_probe()  # run kettle probe to try to wake up the kettle
                attempts -= 1
                self.connected = False

        print("Socket timeout")
        self.connected = False

    def kettle_probe(self):
        """Sends a UDP "probe" message to see what the kettle returns.
        Kettle responds with information about the kettle including the name

        Returns: json string with info about the kettle

        Example probe message: "Probe#2020-05-05-10-47-15-2"
        """

        for i in range(1, 4):
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
            rcv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
            send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            for _i in range(1, 4):
                # send 4 packets
                prb = time.strftime("Probe#%Y-%m-%d-%H-%M-%S", time.localtime())
                send_sock.sendto(str.encode(prb, "ascii"), (UDP_IP_BCAST, UDP_PORT))

            send_sock.close()
            print("Sent broadcast messages, waiting to hear back from kettle...", i)
            rcv_sock.bind(("", UDP_PORT))  # listen on all ports
            rcv_sock.settimeout(5)  # 5 sec timeout for this probe
            try:
                data, address = rcv_sock.recvfrom(1024)
            except socket.timeout:
                rcv_sock.close()
                continue

            data = data.decode("ascii")
            rcv_sock.close()

            msg = data.split("#")
            # pprint(msg)
            msg_json = json.loads(msg[6])  # item 6 has a JSON message with some info
            msg_json.update({"imei": msg[0]})
            msg_json.update({"version": msg[3]})
            msg_json.update({"kettleIP": address[0]})

            print("Discovered kettle with following parameters:")
            print("- Name:", msg_json["AP_ssid"])
            print("- IP:", msg_json["kettleIP"])
            print("- IMEI:", msg_json["imei"])
            print("- Wifi SSID:", msg_json["devRouter"])
            print("- Software version:", msg_json["version"])
            if DEBUG_MSG:
                print(
                    "- Device Status:", msg_json["deviceStatus"]
                )  # same format as status msg

            self.stat = msg_json
            return msg_json

    def keep_connect(self):
        """ Sends a ping message to keep connection going """
        if DEBUG_PRINT_KEEP_CONNECT:
            print("A: KeepConnect")

        try:
            self.sock.sendall(MSG_KEEP_CONNECT)
        except OSError as err:
            print("Socket error (keep connect):", err)
            self.connected = False
            return

    def close(self):
        """ Tidy up function to close scoket """
        print("Closing socket...")
        self.sock.close()

    def send(self, msg):
        """ Send a message to the kettle using socket.sendall() """
        try:
            sent = self.sock.sendall(msg)
        except OSError as err:
            print("Socket error (send):", err)
            self.connected = False
            return
        if sent is not None:
            self.connected = False
            raise RuntimeError("Socket connection broken")

    def receive(self):
        """ Called back from main event loop, receives a message and then parses it

        Messages are received until '&&' (message terminator), and then parsed
        """
        chunks = []
        bytes_recd = 0
        chunk = b""
        while (
            bytes_recd < MSGLEN
            and chunks[-2:] != [b"&", b"&"]
            and self.connected is True
        ):
            try:
                chunk = self.sock.recv(1)
                chunks.append(chunk)
                bytes_recd = bytes_recd + len(chunk)
            except socket.error:
                print("Socket connection broken?",)
                self.connected = False
                return None
            if chunk == b"":
                print("Socket connection broken / no data")
                self.connected = False
                return None

        # this is necessary so it works also when streaming tcpdump traffic,
        # it filters out anything before b"##" (e.g. TCP packet headers)
        frame = b"".join(chunks).partition(b"##")
        frame = frame[1] + frame[2]

        if frame[:4] == ENCRYPT_HEADER:
            res = self.decrypt(frame[6:-2])
        elif frame[:4] == PLAIN_HEADER:
            res = frame[6:-2]
        else:
            res = frame
            if len(frame) > 0:
                print("Response not recognised", frame)

        try:
            res = res.decode("ascii")
            return json_encode(res.rstrip("\x00"))
        except UnicodeDecodeError:
            return None

    @staticmethod
    def decrypt(ciphertext):
        """ AES decryption of text received in ciphertext

        Text lenght needs to be a multiple of 16 bytes
        """
        try:
            cipher_spec = AES.new(SECRET_KEY, AES.MODE_CBC, SECRET_IV)
            return cipher_spec.decrypt(ciphertext)
        except ValueError:
            print("Not 16-byte boundary data")
            return ciphertext
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    # pads with 0x00 as this is what the kettle wants rather than some other padding algorithm
    @staticmethod
    def pad(data_to_pad, block):
        """ Pads data with 0x00 to match block size """
        extra = len(data_to_pad) % block
        if extra > 0:
            return data_to_pad + (b"\x00" * (block - extra))
        return data_to_pad

    def encrypt(self, plaintext):
        """ AES encryption of plaintext """
        try:
            cipher_spec = AES.new(SECRET_KEY, AES.MODE_CBC, SECRET_IV)
            return cipher_spec.encrypt(self.pad(plaintext, AES.block_size))
        except ValueError:
            print("Not 16-byte boundary data: ", plaintext)
            return plaintext
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    def send_enc(self, data2, encrypt=False):
        """ Sends a data2 command encoded with header and termination characters
            Can send Encrypted but can also send plain
            Note: commands in clear also work
        """
        msg = '{{"app_cmd":"62","imei":"{imei}","SubDev":"","data2":"{data2}"}}'.format(
            imei=self.imei, data2=data2
        )
        if encrypt:
            content = self.encrypt(msg.encode())
            header = ENCRYPT_HEADER
        else:
            content = msg.encode()
            header = PLAIN_HEADER
        encoded_msg = header + bytes("%0.2X" % len(content), "utf-8") + content + b"&&"
        self.send(encoded_msg)
        if DEBUG_MSG:
            unpack_msg(json_encode(msg))
