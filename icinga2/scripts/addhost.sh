#!/bin/bash
red='\033[0;31m'
blu='\033[1;36m'
nc='\033[0m'
host=
ip=
dir=

createmenu ()
{
	printf "what ${red}template${nc} would you like for your host?\n"
        select option; do
	read -p "give the FQDN hostname (*.fqdn.be) of your type $option host: " host
	read -p "give the IP address of your type $option host: " ip
	break;
        done
	#we cannot export variables into the textfile anyway, the following sed command will not be ambigious!
	printf "$(sed -e "s/\$host/$host/" -e "s/\$ip/$ip/"  /etc/icinga2/conf.d/templates/$option)" > $dir/$host.conf
}

createmenu2 ()
{
	printf "in what ${red}config directory${nc} would you like to store the ${blu}host${nc}?\n"
        select option; do
	dir=$option
        break;
        done
}

array2=($(find /etc/icinga2/conf.d/ -type d -name "*_hostgroup"))
createmenu2 "${array2[@]}"

array=($(ls /etc/icinga2/conf.d/templates | grep -v "args_"))
createmenu "${array[@]}"

printf "${red}$host${nc} added to ${blu}$dir/$host.conf${nc}\n"
echo "we are now making a trust so that the ssh checks can work:"
ssh-copy-id -oStrictHostKeyChecking=no $host
