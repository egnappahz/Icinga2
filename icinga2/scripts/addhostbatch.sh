#!/bin/bash
host=
ip=
dir=
type=
group=
#dir="/etc/icinga2/conf.d/$1" #rheva_hostgroup
#read -p "give the folder you want to put the hosts in: [rheva_hostgroup]: " dir
#type="$2" #hypervisor.tmpl

createmenudir ()
{
        printf "in what ${red}config directory${nc} would you like to store the ${blu}host${nc}?\n"
        select option; do
        dir=$option
        break;
        done
}

createmenutype ()
{
        printf "what ${red}template${nc} would you like for your host?\n"
        select option; do
	type=$option
        break;
        done
}
arraydir=($(find /etc/icinga2/conf.d/ -type d -name "*_hostgroup"))
createmenudir "${arraydir[@]}"

arraytype=($(ls /etc/icinga2/conf.d/templates | grep -v "args_"))
createmenutype "${arraytype[@]}"

read -p "Press return to review CSV BATCHFILE! SYNTAX: [FQDN HOSTNAME _IN CAPS!!_;IP ADDR]"
vim /etc/icinga2/scripts/batch

count=$(cat /etc/icinga2/scripts/batch | wc -l)

group="$(echo ${dir:20:-10})"
echo "group: $group, dir: $dir"
for ((i=1; i<=$count; i++))
do
	host="$(cat /etc/icinga2/scripts/batch | cut -d ';' -f1| awk 'FNR=='$i)"
	ip=$(cat /etc/icinga2/scripts/batch | cut -d ';' -f2 | awk 'FNR=='$i)
	printf "$(sed -e "s/\$host/$host/" -e "s/\$ip/$ip/" -e "s/\$group/$group/" /etc/icinga2/conf.d/templates/$type)" > $dir/$host.conf
	printf "${red}$host${nc} added to ${blu}$dir/$host.conf${nc}\n"
	echo "we are now making a trust so that the ssh checks can work"
	ssh-copy-id -oStrictHostKeyChecking=no $host
done

icinga2 daemon -C && systemctl reload icinga2 && echo icinga2\ reload\ OK
