#!/bin/python
import api
import sqlite3
import xml.etree.ElementTree as xmlparser
import notifier
import ConfigParser
import httplib, urllib
import requests, json

config = ConfigParser.ConfigParser()
config.read('workflow.cfg')

def initialize():

	# Create sqlite3 database file and create the table tasks
	db = sqlite3.connect('workflow.db')
	db.execute ("CREATE TABLE IF NOT EXISTS tasks (timestamp text, taskid text, userid int, user_has_creds int, type text, ownerid int, state text, rel_target text, rel_user text, rel_continue text, rel_cancel text, active int)")
	db.close()

def get(task_id):

	# Retrieve the task from database in a dictionary format
	con = sqlite3.connect('workflow.db')
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute('select * from tasks where taskid = "%s"' % task_id)
        task=cur.fetchone()
	con.close()
	return task

def insert(task):

	# Insert the task into table tasks on database
        con = sqlite3.connect('workflow.db')
        cur = con.cursor()
        cur.execute('insert into tasks values (?,?,?,?,?,?,?,?,?,?,?,1)', [task['timestamp'],task['taskid'],task['userid'],task['user_has_creds'],task['type'],task['ownerid'],task['state'],task['rel_target'],task['rel_user'],task['rel_continue'],task['rel_cancel']])
        con.commit()
        con.close()

def disable(task_id):
	
	# Mark the task as disabled setting taskid = 0
	con = sqlite3.connect('workflow.db')
        cur = con.cursor()
	cur.execute('update tasks set active = 0 where taskid = "%s"' % task_id)
        con.commit()
        con.close()

def parse_tasks_from_xml(data):

	tasks = []
	# Parse the xml to retrieve the necessary data to create the object task. This will be a dictionary.
	data_parser = xmlparser.fromstring(data)

	if not data_parser.findall('jobs'):
	
		# If the task it's a deploy / undeploy of a vapp or vm
		for task_object in data_parser.findall('task'):
			task = {}
	        	for child in task_object.findall('link'):
		                if child.attrib.get('rel') == "continue":
		                        rel_continue = child.attrib.get('href')
		                if child.attrib.get('rel') == "cancel":
		                        rel_cancel = child.attrib.get('href')
		                if child.attrib.get('rel') == "user":
		                        rel_user = child.attrib.get('href')
		                if child.attrib.get('rel') == "target":
		                        rel_target = child.attrib.get('href')
		        task['timestamp'] = task_object.find('timestamp').text
			task['taskid'] = task_object.find('taskId').text
			task['userid'] = task_object.find('userId').text
			task['type'] = task_object.find('type').text
			task['ownerid'] = task_object.find('ownerId').text
			task['state'] = task_object.find('state').text
			task['rel_target'] = rel_target
			task['rel_user'] = rel_user
			task['rel_continue'] = rel_continue
			task['rel_cancel'] = rel_cancel
			
			task['user_has_creds'] = True if api.get_user_creds(rel_user) else False
			
			tasks.append(task)

	else:
		# if the task it's a reconfigure
		task = {}
		task_object = data_parser
                for child in task_object.findall('link'):
	                if child.attrib.get('rel') == "continue":
        		        rel_continue = child.attrib.get('href')
                        if child.attrib.get('rel') == "cancel":
                                rel_cancel = child.attrib.get('href')
                        if child.attrib.get('rel') == "user":
                                rel_user = child.attrib.get('href')
                        if child.attrib.get('rel') == "target":
                                rel_target = child.attrib.get('href')
                task['timestamp'] = task_object.find('timestamp').text
                task['taskid'] = task_object.find('taskId').text
                task['userid'] = task_object.find('userId').text
                task['type'] = task_object.find('type').text
                task['ownerid'] = task_object.find('ownerId').text
                task['state'] = task_object.find('state').text
                task['rel_target'] = rel_target
                task['rel_user'] = rel_user
                task['rel_continue'] = rel_continue
                task['rel_cancel'] = rel_cancel

                task['user_has_creds'] = True if api.user_has_creds(rel_user) else False

                tasks.append(task)
	return tasks

def accept(task):
	
	# Prepare the URL accept link and send the post call to Abiquo.
	url = config.get('abiquo', 'api_location') + "/" + task['rel_continue']
	data = json.dumps({})
	try:
		r = requests.post(url, data, auth=(config.get('abiquo', 'api_username'),config.get('abiquo', 'api_password')))
	except:
		print "There was an error comunicating with Abiquo API."

def cancel(task):

	# Prepare the URL cancel link and send the post call to Abiquo.
	url = config.get('abiquo', 'api_location') + "/" + task['rel_cancel']
	data = json.dumps({})
	try:
		r = requests.post(url, data, auth=(config.get('abiquo', 'api_username'),config.get('abiquo', 'api_password')))
	except:
		print "There was an error comunicating with Abiquo API."
