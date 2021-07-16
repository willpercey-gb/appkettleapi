DEBUG_MSG = True
DEBUG_PRINT_STAT_MSG = False  # print status messages
DEBUG_PRINT_KEEP_CONNECT = False  # print "keelconnect" packets
SEND_ENCRYPTED = False  # use AES encryted comms with kettle
MSGLEN = 3200  # max msg length: this needs to be long enough to allow a few msg to be received

KETTLE_SOCKET_CONNECT_ATTEMPTS = 3
KETTLE_SOCKET_TIMEOUT_SECS = 60
KEEP_WARM_MINS = 30  # Default keep warm amount

ENCRYPT_HEADER = bytes([0x23, 0x23, 0x38, 0x30])
PLAIN_HEADER = bytes([0x23, 0x23, 0x30, 0x30])
MSG_KEEP_CONNECT = b"##000bKeepConnect&&"
MSG_KEEP_CONNECT_FREQ_SECS = (
    30  # sends a KeepConnect to keep connection live (e.g. app open)
)
UDP_IP_BCAST = "255.255.255.255"
UDP_PORT = 15103

MQTT_BASE = "appKettle"
MQTT_CMD_TOPIC = "cmnd/" + MQTT_BASE

# AES secrets:
SECRET_KEY = b"ay3$&dw*ndAD!9)<"
SECRET_IV = b"7e3*WwI(@Dczxcue"