#!/bin/python
import task as Task
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import humanize
import ConfigParser
import string
import api
import re

config = ConfigParser.ConfigParser()
config.read('workflow.cfg')

apiurl = config.get('abiquo', 'api_location')
apiusername = config.get('abiquo', 'api_username') 
apipassword = config.get('abiquo', 'api_password')

TAKSDELIM = ','
COMMASPACE = ', '

def notify_answered_tasks(task_ids, action):

	tasks = []
	for task_id in task_ids:
		tasks.append(Task.get(task_id))

	first_task = tasks[0]

	# Prepare the mail properties
	from_addr = config.get('mail', 'from')
	subject = config.get('mail', 'requester_subject')
	to_addr = [api.get_single_user_email(first_task["rel_user"])]
	template = config.get('mail', 'requester_template')

	# Get data from the user who generated the task
	userStr = api.get_name_user(first_task["rel_user"])

	# Prepare task details
	taskType = first_task['type']
	
	# Get data from the affected virtual machine
	vm = api.get_virtualmachine_details(first_task["rel_target"])	

	# Build the html for the virtual machine/s
	vmhtmlbody = ""
	for task in tasks:
		vmhtmlbody = vmhtmlbody + build_html_virtualmachine_template_answer(task, action)

	# Prepare the data for the template and load the template with the overrided values
	template_file = config.get('mail', 'requester_template')
	with file(template_file) as f:
		template = f.read()

	valueDict = {'taskType':taskType, 'vmRows':vmhtmlbody}
	htmlbody = string.Template(template).substitute(valueDict)

	send_email(from_addr, to_addr, subject, htmlbody)
	
def build_html_template(template_file, dictionary):
	# Get the template file and substitute values for the ones provided on dictionary
	with file(template_file) as f:
		template = f.read()
	return string.Template(template).substitute(dictionary)

def build_html_virtualmachine_template_answer(task, action):
	# Get the details of the virtual machine and create the dictionary
	vm = api.get_virtualmachine_details(task['rel_target'])
	if "vmHD" in vm:
		vmHd_GB = humanize.naturalsize(long(vm["vmHd"]), gnu=True)
	else:
		vmHd_GB = 0

	vm_valueDict = {'vmName':vm["vmName"], 'vmCpu':vm["vmCpu"], 'vmRam':vm["vmRam"], 'vmHd':vmHd_GB, 'action':action}
	
	# Build the html for the virtual machine
	return build_html_template(config.get('mail', 'requester_vm_template'), vm_valueDict)

def build_html_virtualmachine_template(task):
	vmType = ""
	# Prepare accept / decline links
	accept_lnk = "http://" + config.get('server', 'hostname') + ":" + config.get('server', 'port') + "/accept?task=" +  task['taskid']
	cancel_lnk = "http://" + config.get('server', 'hostname') + ":" + config.get('server', 'port') + "/decline?task=" +  task['taskid']
	amazon_lnk = "http://" + config.get('server', 'hostname') + ":" + config.get('server', 'port') + "/upload_amazon?task=" +  task['taskid']

	# Get the details of the virtual machine and create the dictionary
	vm = api.get_virtualmachine_details(task['rel_target'])

	# Get the disks of the virtual machine
	disks_ = api.get_virtualmachine_storage(task['rel_target'])
	disks = []
	for disk in disks_:
		if disk['sequence'] != "0":
			disks.append(disk)

	vmdiskshtmlbody = ""
	for disk in disks:
		diskhtmlbody = build_html_template(config.get('mail', 'admin_vm_storage_template'), disk)
		vmdiskshtmlbody = vmdiskshtmlbody + diskhtmlbody
	
	if vm['persistent']:
		txt_pers = " (Persistent VM)"
	if vm['amazon']:
		txt_pers = " (Amazon)"
	else:
		txt_pers = ""

	rows_for_action = len(disks) + 1
        if "vmHD" in vm:
                vmHd_GB = humanize.naturalsize(long(vm["vmHd"]), gnu=True)
        else:
                vmHd_GB = 0

	if task['type'] == "UNDEPLOY":
		vm_valueDict = {'vmName':vm["vmName"], 'vmCpu':vm["vmCpu"], 'vmRam':vm["vmRam"], 'vmHd':vmHd_GB, 'amazon_lnk':amazon_lnk,
		'accept_lnk':accept_lnk, 'cancel_lnk':cancel_lnk, 'disks':vmdiskshtmlbody, 'pers':txt_pers, 'actionrows':rows_for_action }
	
		# Build the html for the virtual machine
		return build_html_template(config.get('mail', 'admin_undeploy_vm_template'),vm_valueDict)
	else:
		vm_valueDict = {'vmName':vm["vmName"], 'vmCpu':vm["vmCpu"], 'vmRam':vm["vmRam"], 'vmHd':vmHd_GB,
		'accept_lnk':accept_lnk, 'cancel_lnk':cancel_lnk, 'disks':vmdiskshtmlbody, 'pers':txt_pers, 'actionrows':rows_for_action }
	
		# Build the html for the virtual machine
		return build_html_template(config.get('mail', 'admin_vm_template'),vm_valueDict)

def notify_new_task(tasks):	
	accept_all_lnk = "http://" + config.get('server', 'hostname') + ":" + config.get('server', 'port') + "/multiple?action=accept&tasks="
	cancel_all_lnk = "http://" + config.get('server', 'hostname') + ":" + config.get('server', 'port') + "/multiple?action=cancel&tasks="
	upload_all_lnk = "http://" + config.get('server', 'hostname') + ":" + config.get('server', 'port') + "/multiple?action=amazon&tasks="

	tasks_all = []

	first_task = tasks[0]
	
	# Prepare the mail properties
	from_addr = config.get('mail', 'from')
	subject = config.get('mail', 'admin_subject')
	emailsList = api.get_emails_from_role(first_task["rel_target"])

	# Prepare task details
	taskType = first_task['type']

	# Get data from the user who generated the task
	userStr = api.get_name_user(first_task["rel_user"])

	# Get the vapp, vdc and enterprise name where the vm/s are placed
	vdc = api.get_virtualdatacenter_name(re.sub(r'(.*)/virtualappliances/.*','\g<1>', first_task['rel_target']))
	dc = api.get_datacenter_name(re.sub(r'(.*)/virtualappliances/.*','\g<1>', first_task['rel_target']))
	vapp = api.get_virtualapp_name(re.sub(r'(.*)/virtualmachines/.*','\g<1>', first_task['rel_target']))
	enterprise = api.get_enterprise_name(re.sub(r'(.*)/users/.*','\g<1>', first_task['rel_user']))
	
	# Build the html for the virtual machine/s
	vmhtmlbody = ""
	for task in tasks:
		tasks_all.append(task['taskid'])
		vmhtmlbody = vmhtmlbody + build_html_virtualmachine_template(task)

	tasks_all_str = TAKSDELIM.join(tasks_all)
	accept_all_lnk = accept_all_lnk + tasks_all_str
	cancel_all_lnk = cancel_all_lnk + tasks_all_str
	upload_all_lnk = upload_all_lnk + tasks_all_str

	if taskType == "UNDEPLOY":
		# Prepare the complete template
		valueDict = {'userStr':userStr, 'taskType':taskType, 'vmRows':vmhtmlbody, 'accept_all_lnk':accept_all_lnk, 'upload_all_lnk':upload_all_lnk,
			'cancel_all_lnk':cancel_all_lnk, 'enterprise':enterprise, 'vapp':vapp, 'vdc':vdc, 'dc':dc }
		htmlbody = build_html_template(config.get('mail', 'admin_undeploy_template'),valueDict)
	else:
		# Prepare the complete template
		valueDict = {'userStr':userStr, 'taskType':taskType, 'vmRows':vmhtmlbody, 'accept_all_lnk':accept_all_lnk, 'cancel_all_lnk':cancel_all_lnk, 'enterprise':enterprise, 'vapp':vapp, 'vdc':vdc, 'dc':dc }
		htmlbody = build_html_template(config.get('mail', 'admin_template'),valueDict)

	# Send the new task email	
	if emailsList and len(emailsList) > 0:
		send_email(from_addr, emailsList, subject, htmlbody)

	return emailsList

def send_email(from_addr, emails, subject, htmlbody):

	# Exit if no email address to send
	if not subject:
		return

	# Create message container - the correct MIME type is multipart/alternative.
	msg = MIMEMultipart('alternative')
	msg['Subject'] = subject
	msg['From'] = from_addr
	msg['To'] = COMMASPACE.join(emails)
	
	text = "This client cannot load HTML emails"
	
	# Record the MIME types of both parts - text/plain and text/html.
	part1 = MIMEText(text, 'plain')
	part2 = MIMEText(htmlbody, 'html')
	
	# Attach parts into message container.
	# According to RFC 2046, the last part of a multipart message, in this case
	# the HTML message, is best and preferred.
	msg.attach(part1)
	msg.attach(part2)
	
	# Send the message via local SMTP server.
	s = smtplib.SMTP('localhost')
	# sendmail function takes 3 arguments: sender's address, recipient's address
	# and message to send - here it is sent as one string.
	s.sendmail(from_addr, emails, msg.as_string())
	s.quit()
