#!/bin/bash
echo "/usr/lib64/nagios/plugins/check_mem -w 10 -c 5"
/usr/lib64/nagios/plugins/check_mem -w 11 -c 7
echo $?
