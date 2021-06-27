


RUN SCRIPT AT STARTUP AND HAVE STDOUT AS FILE:
===============================================
sudo mkdir /var/log/mylogs

cp services/* /lib/systemd/system/


sudo systemctl start  mypython.webapp.service mypython.tank_sensor.service  mypython.scheduler.service mypython.lcd_controller.service

sudo nano /lib/systemd/system/mypython.lcd_controller.service
sudo nano lrmypython.pump_scheduler.service
sudo nano /lib/systemd/system/mypython.tank_level.service
sudo chmod 644 /lib/systemd/system/mypython*.service

sudo systemctl daemon-reload
sudo systemctl enable  mypython.tank_sensor.service
sudo systemctl start  mypython.tank_sensor.service
sudo systemctl enable  mypython.tank_sensor.service

alias status_tank="sudo systemctl status mypython.tank_level.service"
alias stop_tank="sudo systemctl stop mypython.tank_level.service"
alias start_tank"sudo systemctl start mypython.tank_level.service"
alias status_pump="sudo systemctl status mypython.pump_scheduler.service"
alias stop_pump="sudo systemctl stop mypython.pump_scheduler.service"
alias start_pump"sudo systemctl start mypython.pump_scheduler.service"


LOG FILE ROTATION:
==================
sudo mkdir /var/log/mylogs   <== all logs will be in go here

sudo nano /etc/logrotate.d/mylogs
more /etc/logrotate.d/mylogs
/var/log/mylogs/* {
   weekly
   rotate 2
   size 10M
   compress
   delaycompress
}
To see what this willdo, run it in debug mode:
logrotate -d /etc/logrotate.d/mylogs






more /etc/systemd/journald.conf
...
[Journal]
SystemMaxUse=20M


all scripts config file are in  /home/pi/config
==> use lock system on all files
