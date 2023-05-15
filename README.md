timesync using ntpserver
=========

A time-sync script to sync wrong time data of devices which does not have access to ntp server or RTC. Run ntpserver.py in server device, change the serverIp value in the client.py and run it on the client device.
Client receives the timestamp from the server and sets time with timedatectl commands.

Tested on Linux

Based on ntplib(https://pypi.python.org/pypi/ntplib/) and limitfly, thanks for their work.


