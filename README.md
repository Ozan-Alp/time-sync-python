timesync using ntpserver
=========

A time-sync script to sync wrong time data of devices which does not have access to ntp server or RTC. Server and client devices must be on the same network.
Run ntpserver.py in the server device which has the correct time, change the serverIp value to server`s adress in the client.py and run it on the client device.
Client receives the timestamp from the server and sets time with timedatectl commands.

Tested on Linux

Based on ntplib(https://pypi.python.org/pypi/ntplib/) and limitfly, thanks for their work.


