""" This module is used to capture the data out of the RHV4 instances
"""
from ovirtsdk.api import API
from ovirtsdk.xml import params
from ConfigParser import SafeConfigParser
import time, datetime
import argparse
import sys
import pickle
import urllib, json
import requests

debug = 0

class rhv4:
	"""The main class for RHV Module
	"""
	def __init__(self, config, debug):
		self.hostArr = {}					# The array will contain all the hosts that are up
		self.vmsArr = {}
		self.config = config
		self.api =  ""
		self.debug = debug
		self.baseUrl = "http://localhost/data/api/Icinga/"	# This is the base url to the data Module
		pass

	def _connect(self, system):	
		""" General function to retrive the info from the RHEV system
		"""
		try:
			if self.debug: print "Getting information from %s with url %s" % (system, self.config.get(system,'url'))
			# Initialize api_instance sith login creadentials
			self.api = API( url=self.config.get(system,'url'),
				username=self.config.get(system,'username'),
				password=self.config.get(system,'password'),
				ca_file=self.config.get(system,'ca_file') )
			if self.debug: print "-Connected successfully-"
		except Exception as ex:
                        print "WARNING - %s in config file" % str(ex)
                        sys.exit(1)

	def _addRESTlog(self,system,event):
		""" This function will send the request to the data module and add the entry in the logentries
	        """
		# Calculate EventType
		if(event.get_severity().upper() == "WARNING"):
			eventtype=1
		elif(event.get_severity().upper() == "ERROR"):
			eventtype=2
		else:
			eventtype=0      

		url = "%s/%s" % (self.baseUrl,"add")
		if self.debug: print "--Post REST api url is %s --" % url
		entrytime=event.get_time().strftime("%Y-%m-%d %H:%M:%S")
		if self.debug: print "------ JSON DATA send %s %s %s %s %s ------" %(event.get_id(),event.description,eventtype,system,entrytime)
		response = requests.post(url,
   	 		data=json.dumps({'id': event.get_id(), 'text': event.description, 'type': eventtype, 'host':system, 'entrytime': entrytime}))
		if self.debug: print "----- Reponse data from JSON request %s ----- " %  response.text

	""" This function will retrive the last log in the manager, puts it in data structure and process alerts
        """
	def getLogEntries(self,system):
                """ This function will process the information on the log Entries.

                :param system: The rhvm host

                """
		#Initialise the connection
                self._connect(system)
		try:
			#id=0
			if self.debug: print "--Trying to locate the pickle file--"
			pklfile="/var/tmp/%s.pkl" % system
			try:
				# has pickle file ??
				dataStream = open(pklfile,'rb')
				last = pickle.load(dataStream)
				dataStream.close()
				if self.debug: print "--Picle file %s is readable and can be used--" % pklfile
			
				# retrieve last id from Pickle file
				if(last['id']>0):
					if self.debug: print "---Pickle ID found in file = %s---" % last['id']
					
					# Check if this last ID still exsist, if not there might be log rotation
					event = self.api.events.get(id="%s" % last['id'])
					if not(event is None):
						if self.debug: print "---Last ID still available consider this as good %s (%s) %s---" % (event.get_id(),event.description,event.get_severity().upper())
						# id = last id form pickle file
						id=int(last['id'])
					else:
						if self.debug: print "---Last ID is not valid !!! We need to read the entire list and use the last ---"
						event=self._processAllLogs()
						id=event.get_id()

					# id is defined from here		
					while not(event is None):

						# get_event(id+1)
						id += 1
						if self.debug: print "---Test for event ID %s---" % id
						event = self.api.events.get(id="%s" % id)
						if not(event is None):
							# Thre is a new legentry
							if self.debug: print "---NEW log entry  %s (%s) %s---" % (event.get_id(),event.description,event.get_severity().upper())
							# We will only take into account above WARNNING
							if(event.get_severity().upper() == "WARNING" or (event.get_severity().upper() == "ERROR")):								
								self._addRESTlog(system,event)
								#logLine = "%s %s" % (logLine, event.description)
						else:
							id -= 1
							if self.debug: print "---NO new log, taking last valid id %s---" % id
							 
					# Compare the latest id with the one in the pickle file
					latest_pickle=int(last['id'])
					latest_id=id
					if(latest_pickle == latest_id):
						# Nothing to do here since no new entered 
						pass
					else:
						if self.debug: print "----Saving last log %s in Pickle----" % latest_id
						dataStream = open(pklfile,'wb')
						idStr = "%s" % latest_id
						pickle.dump({"id" : idStr}, dataStream)
						dataStream.close()
					
					# Handle info from the data to the monitor
					url = "http://localhost/data/api/Icinga/%s" % system
					# todo ERROR TRAPPING HERE	
					if self.debug: print "-----Testing for URL %s-----" % url
					try:
						response = urllib.urlopen(url)
						data = json.loads(response.read())
						if self.debug: print "-----URL can be loaded-----" 
						record = data[0]
						if self.debug: print "------ Dumping data %s ------" %  record
						if (record['exitCode'] == 1 ):
        						exit = "WARNING"
						elif(record['exitCode'] == 2 ):
       							exit = "CRITICAL"
						else:
       							exit = "OK last(%s)" % latest_pickle
						print "%s - %s " % (exit,record['data'].replace('\n', ' ').replace('\r', ''))
						# exit record['exitCode']
						sys.exit(record['exitCode'])
					except Exception as ex:
                                        	print "%s - %s %s" % ("UNKNOWN","CAN NOT CONNECT TO", url)
                                        	sys.exit(4)
				else:
					# loop over alle events and get last to find last id
					event=self._processAllLogs()
					idStr = "%s" % event.get_id()
					pickle.dump({"id" : idStr}, dataStream)
					dataStream.close()
					print "%s - %s" % ("UNKNOWN","Initializing the check environment")
					sys.exit(4)
				dataStream.close()
			except Exception as ex:
				if self.debug: print "Exception : %s " % str(ex)
				if self.debug: print "--Creating Picle file--"
				dataStream = open(pklfile,'wb')
				event = self._processAllLogs()
				pickle.dump({"id" : event.get_id()}, dataStream)
				dataStream.close()
				if self.debug: print "--Picle file created initializing on %s--" %  event.get_id()
				print "%s - %s" % ("UNKNOWN","Initializing the check environment")
                                sys.exit(4)
		except Exception as ex:
			print "Exception : %s " % str(ex)	

	def _processAllLogs(self):
		""" This function will loop over all the logs in order to retieve the last log entrie
        	"""
		eventList = self.api.events.list()
                eventList.reverse()
		for event in eventList:
			if self.debug: print "%s (%s) %s" % (event.get_id(),event.description,event.get_severity().upper())
		return event

	def checkNumVMS(self,system):
		""" This function will return vm data

                :param system: The rhvm host

                """
		self._connect(system)
		try:
			active = self.api.get_summary().vms.get_active()
			total = self.api.get_summary().vms.get_total()
			print "OK NumVMS Total=%s Active=%s |total=%s active=%s" % (total,active,total,active)
		except Exception as ex:
			print "WARNING - checkNumVMS Exception : %s " % str(ex)
			sys.exit(1)

	def checkNumHosts(self,system):
		""" This function will return host data

                :param system: The rhvm host

                """
		self._connect(system)
                try:
			if self.debug: print "--Retrieving the HOSTS and host state--"
			countArr = { 	"maintenance" : 0,
					"non_operational" : 0,
					"up" : 0 }
		  	hostList = self.api.hosts.list()
                        for host in hostList:
                        	if self.debug: print "%s (%s) is %s" % (host.get_name(),host.get_id(),host.status.state)
				try:
					countArr[host.status.state] += 1
				except:
					countArr[host.status.state] = 1
		except Exception as ex:
                        print "WARNING - checkHosts Exception : %s " % str(ex)
                        sys.exit(1)
		
		maintenace=""
		non_operational=""
		# We are only filtering out 
		if(countArr["maintenance"]>0):
			maintenace="%s host are in maintenance" % (countArr["maintenance"])
                       	#sys.exit(1)
		if(countArr["non_operational"]>0):
			non_operational="%s host are in non_operational" % (countArr["non_operational"])
		if(countArr["maintenance"]>0 or countArr["non_operational"]>0):
			print "WARNING - %s %s |up=%s maintenace=%s non_operational=%s " % ( maintenace, non_operational, countArr["up"], countArr["maintenance"], countArr["non_operational"])
		else:
			print "OK - All Hosts up |up=%s maintenace=%s non_operational=%s " % ( countArr["up"], countArr["maintenance"], countArr["non_operational"])

	def getInventory(self,system):
		""" This function will perform the inventory of a specific RHV host
		General environment parameters are put in the csv file 
                
		:param system: The rhvm host
		
		"""
		self._connect(system)
		clusterArr = {}
		dataArr = []
		try:
			if debug: print "--Retrieving the HOSTS and host state--"
                        hostList = self.api.hosts.list()
                        for host in hostList:
                                if debug: print "%s (%s) is %s" % (host.get_name(),host.get_id(),host.status.state)
                        	self.hostArr[host.get_id()]=host.get_name()

			if self.debug: print "--Retrieving the clusters--"
			clusterList = self.api.clusters.list()       
    			for cluster in clusterList:
				clusterArr[cluster.get_id()]=cluster.get_name() 
	
		except Exception as ex:
                        print "WARNING - saveInventory Exception : %s " % str(ex)
			sys.exit(99)
                try:
			if self.debug: print "--Retrieving the VMS--"
                        vmList = self.api.vms.list()
                        for vm in vmList:
				try: full_version = vm.guest_operating_system.kernel.version.full_version
				except: full_version = "NRV"

				disks = vm.disks.list()
				
				try: vda_size = disks[0].get_size()
				except: vda_size = "NRV"

				try: vdb_size = disks[1].get_size()
                                except: vdb_size = "NRV"
				
				if (vm.placement_policy.host is None):
					placement_policy = "NRV"
				else:
					placement_policy =  self.hostArr[vm.placement_policy.host.get_id()]
				if ( vm.status.state == 'up' ):
					running_on= self.hostArr[vm.host.get_id()]
				else:
					running_on="DOWN"
				
				if self.debug: print "name=%s,desciption=%s,state=%s,cores=%s,sockets=%s,memory=%s,memory_guaranteed=%s,high_availability=%s,kernel=%s,cluster=%s,running_on=%s,started_on=%s,vda_size=%s,vdb_size=%s" % (
					vm.get_name(),
					vm.description,
					vm.status.state,
					vm.cpu.topology.cores,
					vm.cpu.topology.sockets,
					vm.memory,
					vm.memory_policy.guaranteed,
					vm.high_availability.enabled,
					full_version,
					clusterArr[vm.cluster.get_id()],
					running_on,
					placement_policy,
					vda_size,
					vdb_size)
				data = {
					'name' : vm.get_name(),
                                        'description' : vm.description,
                                        'state' : vm.status.state,
                                        'cores' : vm.cpu.topology.cores,
                                        'sockets' : vm.cpu.topology.sockets,
                                        'memory' : vm.memory,
                                        'memory_policy' : vm.memory_policy.guaranteed,
                                        'high_availability' : vm.high_availability.enabled,
                                        'full_version' : full_version,
                                        'cluster' : clusterArr[vm.cluster.get_id()],
					'running_on' : running_on,
					'started_on' : placement_policy,
                                        'vda_size' : vda_size,
                                        'vdb_size' : vdb_size}
				dataArr.append(data)
			return dataArr
		except Exception as ex:
                        print "WARNING - saveInventory Exception : %s " % str(ex)
                        sys.exit(99)

	def migrateHost2defaultHost(self, system, move):
		""" This function will move vms to its default host.
			
		The function makes a loop over all running VMs. 
		If a VM is not running on his staring Host then this VM will be moved to its starting host.

		It is the intention to use this function only form the commandline application moveVm2Host.

		A delay is forseen between every REST call in order not to overload the RHV Manager.

		:param system: The rhvm host
		:param move: set to 1 will move the hosts
		
		"""

                try:
                        if debug: print "Getting information from %s with url %s" % (system, self.config.get(system,'url'))
                        # Initialize api_instance sith login creadentials
                        api = API( url=self.config.get(system,'url'),
                                username=self.config.get(system,'username'),
                                password=self.config.get(system,'password'),
                                ca_file=self.config.get(system,'ca_file') )

                        if debug: print "-Connected successfully-"
                        if debug: print "--Retrieving the HOSTS and host state--"

                        hostList = api.hosts.list()
                        for host in hostList:
                                if debug: print "%s (%s) is %s" % (host.get_name(),host.get_id(),host.status.state)
                                if  ( host.status.state == 'up' ):
                                        self.hostArr[host.get_id()]=host.get_name()

                        if debug: print "--Retrieving the VMS--"
                        vmList = api.vms.list()
                        for vm in vmList:
                                if ( vm.status.state == 'up' ):
                                        if debug: print "%s (%s) %s ON %s" % (vm.get_name(), vm.get_id(), vm.status.state, vm.host.get_id() )
                                        if (vm.placement_policy.host is None):
                                                #if debug: print "No host placement policy assigned"
                                                pass
                                        else:
                                                if debug: print "Host placement policy assigned to %s" % (vm.placement_policy.host.get_id())

                                                if (vm.placement_policy.host.get_id() == vm.host.get_id()):
                                                        if debug: print "No HOST migration needed"
                                                else:
                                                        line="Host %s (on %s) needs to move to %s" % (vm.get_name(),self.hostArr[vm.host.get_id()], self.hostArr[vm.placement_policy.host.get_id()])
                                                        sys.stdout.write(line)
                                                        sys.stdout.flush()
                                                        #move = 1
                                                        if move:
                                                                vm.migrate(
                                                                	action=params.Action(
                                                                		host=params.Host(id=vm.placement_policy.host.get_id())
                                                                	)
                                                                )

								# This is a sleep routine
                                                                for i in range(0,5):
                                                                        sys.stdout.write('.')
                                                                        sys.stdout.flush()
                                                                        time.sleep(2)
                                                                sys.stdout.write("\n")
                                                                sys.stdout.flush()
							else:
								sys.stdout.write("\n")
                                                                sys.stdout.flush()
                                else:
                                        if debug: print "%s (%s) DOWN migration policy %s" % (vm.get_name(), vm.get_id(), vm.placement_policy.affinity )
                        api.disconnect()
                except Exception as ex:
                        print "Exception : %s " % str(ex)
