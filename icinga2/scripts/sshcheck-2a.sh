#!/bin/bash

host= #parameter "h"
check= #parameter "c"
warn= #parameter "w"
crit= #parameter "C"

while getopts ":h:c:C:w:" OPTION
do
	case $OPTION in
	h)
	host=$OPTARG
	;;
	c)
	check=$OPTARG
	;;
	w)
	warn=$OPTARG
	;;
	C)
	crit=$OPTARG
	;;
	esac
done

sudo ssh $host "/usr/lib64/nagios/plugins/$check -w $warn -c $crit";

exit $?
