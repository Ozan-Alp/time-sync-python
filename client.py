import datetime
import socket
import struct
import time
import queue
import threading
import select
import subprocess
taskQueue = queue.Queue()
stopFlag = False
command_run=False# terminal komutlarini uygulama
serverIp = "192.168.2.2"  # Replace with the server's IP address inspectrone icin server 192.168.2.2
serverPort = 9999  # Replace with the server's port number

def system_to_ntp_time(timestamp):#timestamp=time.time 

        return timestamp + NTP.NTP_DELTA# NTP_DELTA PC  1900den bugune kadarki gunlerin time degerini hesapliyor, timestampin ustune ekliyor.

def _to_int(timestamp):

    return int(timestamp)

def _to_frac(timestamp, n=32):

    return int(abs(timestamp - _to_int(timestamp)) * 2**n)

def _to_time(integ, frac, n=32):

    return integ + float(frac)/2**n	

class NTPException(Exception):

    pass

class NTP:# sabit degiskenler
    """Helper class defining constants."""

    _SYSTEM_EPOCH = datetime.date(*time.gmtime(0)[0:3])
    """system epoch"""
    _NTP_EPOCH = datetime.date(1900, 1, 1)
    """NTP epoch"""
    NTP_DELTA = (_SYSTEM_EPOCH - _NTP_EPOCH).days * 24 * 3600
    """delta between system and NTP time"""

    REF_ID_TABLE = {
            'DNC': "DNC routing protocol",
            'NIST': "NIST public modem",
            'TSP': "TSP time protocol",
            'DTS': "Digital Time Service",
            'ATOM': "Atomic clock (calibrated)",
            'VLF': "VLF radio (OMEGA, etc)",
            'callsign': "Generic radio",
            'LORC': "LORAN-C radionavidation",
            'GOES': "GOES UHF environment satellite",
            'GPS': "GPS UHF satellite positioning",
    }
    """reference identifier table"""

    STRATUM_TABLE = {
        0: "unspecified",
        1: "primary reference",
    }
    """stratum table"""

    MODE_TABLE = {
        0: "unspecified",
        1: "symmetric active",
        2: "symmetric passive",
        3: "client",
        4: "server",
        5: "broadcast",
        6: "reserved for NTP control messages",
        7: "reserved for private use",
    }
    """mode table"""

    LEAP_TABLE = {
        0: "no warning",
        1: "last minute has 61 seconds",
        2: "last minute has 59 seconds",
        3: "alarm condition (clock not synchronized)",
    }
    """leap indicator table"""

class NTPPacket:


    _PACKET_FORMAT = "!B B B b 11I"
    
    """packet format to pack/unpack"""

    def __init__(self, version=2, mode=3, tx_timestamp=0):
        """Constructor.

        Parameters:
        version      -- NTP version
        mode         -- packet mode (client, server)
        tx_timestamp -- packet transmit timestamp
        """
        self.leap = 0
        """leap second indicator"""
        self.version = version
        """version"""
        self.mode = mode
        """mode"""
        self.stratum = 0
        """stratum"""
        self.poll = 0
        """poll interval"""
        self.precision = 0
        """precision"""
        self.root_delay = 0
        """root delay"""
        self.root_dispersion = 0
        """root dispersion"""
        self.ref_id = 0
        """reference clock identifier"""
        self.ref_timestamp = 0
        """reference timestamp"""
        self.orig_timestamp = 0
        self.orig_timestamp_high = 0
        self.orig_timestamp_low = 0
        """originate timestamp"""
        self.recv_timestamp = 0
        """receive timestamp"""
        self.tx_timestamp = tx_timestamp
        self.tx_timestamp_high = 0
        self.tx_timestamp_low = 0
        """tansmit timestamp"""
        
    def to_data(self):
        """Convert this NTPPacket to a buffer that can be sent over a socket.

            returns:
        buffer representing this packet

        Raises:
        NTPException -- in case of invalid field
        """
        try:
            packed = struct.pack(NTPPacket._PACKET_FORMAT,
                (self.leap << 6 | self.version << 3 | self.mode),
                self.stratum,
                self.poll,
                self.precision,
                _to_int(self.root_delay) << 16 | _to_frac(self.root_delay, 16),
                _to_int(self.root_dispersion) << 16 |
                _to_frac(self.root_dispersion, 16),
                self.ref_id,
                _to_int(self.ref_timestamp),
                _to_frac(self.ref_timestamp),
                #Change by lichen, avoid loss of precision
                self.orig_timestamp_high,
                self.orig_timestamp_low,
                _to_int(self.recv_timestamp),
                _to_frac(self.recv_timestamp),
                _to_int(self.tx_timestamp),
                _to_frac(self.tx_timestamp))
        except struct.error:
            raise NTPException("Invalid NTP packet fields.")
        return packed

    def from_data(self, data):
        """Populate this instance from a NTP packet payload received from
        the network.

        Parameters:
        data -- buffer payload

        Raises:
        NTPException -- in case of invalid packet format
        """
        try:
            unpacked = struct.unpack(NTPPacket._PACKET_FORMAT,
                    data[0:struct.calcsize(NTPPacket._PACKET_FORMAT)])
        except struct.error:
            raise NTPException("Invalid NTP packet.")

        self.leap = unpacked[0] >> 6 & 0x3
        self.version = unpacked[0] >> 3 & 0x7
        self.mode = unpacked[0] & 0x7
        self.stratum = unpacked[1]
        self.poll = unpacked[2]
        self.precision = unpacked[3]
        self.root_delay = float(unpacked[4])/2**16
        self.root_dispersion = float(unpacked[5])/2**16
        self.ref_id = unpacked[6]
        self.ref_timestamp = _to_time(unpacked[7], unpacked[8])
        self.orig_timestamp = _to_time(unpacked[9], unpacked[10])
        self.orig_timestamp_high = unpacked[9]
        self.orig_timestamp_low = unpacked[10]
        self.recv_timestamp = _to_time(unpacked[11], unpacked[12])
        self.tx_timestamp = _to_time(unpacked[13], unpacked[14])
        self.tx_timestamp_high = unpacked[13]
        self.tx_timestamp_low = unpacked[14]

    def GetTxTimeStamp(self):
        return (self.tx_timestamp_high,self.tx_timestamp_low)

    def SetOriginTimeStamp(self,high,low):
        self.orig_timestamp_high = high
        self.orig_timestamp_low = low

class RecvThread(threading.Thread):
    def __init__(self,socket):
        threading.Thread.__init__(self)
        self.socket = socket
    def run(self):
        global taskQueue,stopFlag
        while True:
            if stopFlag == True:
                print ("RecvThread Ended")
                break
            rlist,wlist,elist = select.select([self.socket],[],[],1);
            if len(rlist) != 0:
                print ("Received %d packets" % (len(rlist)))
                for tempSocket in rlist:
                    try:
                        data,addr = tempSocket.recvfrom(1024)
                        recvTimestamp = system_to_ntp_time(time.time())
                        taskQueue.put((data,addr,recvTimestamp))
                        print("218")
                    except OSError as err:
                        print (err)

class WorkThread(threading.Thread):
    def __init__(self,socket):
        threading.Thread.__init__(self)
        self.socket = socket
    def run(self):
        global taskQueue,stopFlag
        while True:
            if stopFlag == True:
                print ("WorkThread Ended")
                break
            try:
                data,addr,recvTimestamp = taskQueue.get(timeout=1)
                recvPacket = NTPPacket()
                recvPacket.from_data(data)
                timeStamp_high,timeStamp_low = recvPacket.GetTxTimeStamp()
                sendPacket = NTPPacket(version=3,mode=4)
                sendPacket.stratum = 2
                sendPacket.poll = 10
                '''
                sendPacket.precision = 0xfa
                sendPacket.root_delay = 0x0bfa
                sendPacket.root_dispersion = 0x0aa7
                sendPacket.ref_id = 0x808a8c2c
                '''
                sendPacket.ref_timestamp = recvTimestamp-5
                sendPacket.SetOriginTimeStamp(timeStamp_high,timeStamp_low)
                sendPacket.recv_timestamp = recvTimestamp
                sendPacket.tx_timestamp = system_to_ntp_time(time.time())#bunlar gercek time degil datanin islenme timestamplari
                socket.sendto(sendPacket.to_data(),addr)
                print ("Sent to %s:%d" % (addr[0],addr[1]))
            except queue.Empty:
                continue



# Create a client socket
timeout = 3
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
clientSocket.settimeout(timeout)
clientSocket.setblocking(0)
target_date = datetime.datetime(2023, 1, 1)
target_time = target_date.timestamp()

# Send data to the server
i=+1
sendPacket = NTPPacket(version=3,mode=4)# ICININ ONEMI YOK SERVER NTPPacket turunden data istiyor, icindeki bizim kullanmayacagimiz bazi bilgileri gonderecegi packete
#yaziyor, data alma ve verme timestamplari gibi degerler. saniyelik sabit shift edilmis hata olabilir ama server time.time() datasini packete yazip geri gonderiyor.


for i in range(5):
    try:
        clientSocket.sendto(sendPacket.to_data(), (serverIp, serverPort))
        ready = select.select([clientSocket], [], [], timeout)#timeoutlu data cekme, socketi nonblocking yapip select modulunu kullandik
        if ready[0]:
        # Receive response from the server
            data, serverAddress = clientSocket.recvfrom(1024)
            recvPacket = NTPPacket()
            recvPacket.from_data(data)
            received_time = time.ctime(recvPacket.tx_timestamp)#String format Ex: Mon May 15 10:57:42 2023
            if recvPacket.tx_timestamp>target_time:
                # Format the datetime object into a string accepted by timedatectl
                dt = datetime.datetime.strptime(received_time, "%a %b %d %H:%M:%S %Y")
                formatted_time = dt.strftime("%a %Y-%m-%d %H:%M:%S")
                print("Received response&passed sanity check:", formatted_time)
                if command_run:
                    subprocess.run(["timedatectl", "set-ntp", "false"])
                    subprocess.run(["timedatectl", "set-time", formatted_time])
                    subprocess.run(["timedatectl", "set-timezone", "Europe/Istanbul"])
                    subprocess.run(["timedatectl", "set-ntp", "true"])
                break
            else:
                print("Sanity check failed.")
        else:
            print("Timeout occurred. No response received.")

            
    except socket.error as e:
        # Handle any socket-related errors
        print("Socket error occurred:", e)
    
# Close the socket
clientSocket.close()


#SET TIME

