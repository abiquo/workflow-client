#!/bin/python
import ConfigParser
import notifier
import task as Task
import api
import string
import xml.etree.ElementTree as xmlparser

config = ConfigParser.ConfigParser()
config.read('workflow.cfg')

def generate_html_reply(message, code):
  response_template = config.get('server', 'response_template')
  with file(response_template) as f:
    template = f.read()
  response_dictionary = { 'message':message }
  return { 'html': string.Template(template).substitute(response_dictionary), 'code': code }

def accept_task(task_id, multiple = False):

  # We retrieve the task from database. We only continue in case the task exists on DB and it's not obsolete.
  task=Task.get(task_id)
  if not task:
    return generate_html_reply("The requested task does not exist\n", "404")
  if task["active"] == 0:
    return generate_html_reply("This link is obsolete. The task have already been submitted.\n", "410")
  
  # Send the accept to Abiquo
  Task.accept(task)
    
  # Disable the task on database, so next calls to the link will find the task obsolete.
  Task.disable(task_id)

  if not multiple:   
    notifier.notify_answered_tasks([task['taskid']], True)
  
  return generate_html_reply("Task accepted. The task is now being processed\n", "200")

def decline_task(task_id, multiple = False):
    
  # We retrieve the task from database. We only continue in case the task exists on DB and it's not obsolete.
  task=Task.get(task_id)
  if not task:
    return generate_html_reply("The requested task does not exist\n", "404")

  if task["active"] == 0:
    return generate_html_reply("This link is obsolete. The task have already been submited\n", "410")

  # Send the accept to Abiquo
  Task.cancel(task)

  # Disable the task on database, so next calls to the link will find the task obsolete
  Task.disable(task_id)
  
  if not multiple:
     notifier.notify_answered_tasks([task['taskid']], False)
    
  return generate_html_reply("Task canceled. The task is now being canceled\n", "200")

def multiple_update(task_ids, action):
  all_tasks_id = task_ids.split(",")

  all_tasks_id_confirmed = []
  for task_to_confirm in all_tasks_id:
    task=Task.get(task_to_confirm)
    if task["active"] == 1:
      all_tasks_id_confirmed.append(task["taskid"])

  if not all_tasks_id_confirmed:
    return generate_html_reply("All task have already been decided", "410")

  for task_id in all_tasks_id_confirmed:
    if action == "cancel":
      decline_task(task_id, True)
    elif action == "accept":
      accept_task(task_id, True)
  
  notifier.notify_answered_tasks(all_tasks_id_confirmed, action)

  return generate_html_reply("The tasks " + task_ids + " are now being processed", "200")


def new_tasks(post_data):

  # Create the object task parsing the doc we received
  try:
    tasks = Task.parse_tasks_from_xml(post_data)
  except:
    tasks = Task.parse_tasks_from_json(post_data)

  for task in tasks:
    # Insert the task into database
    Task.insert(task) 

  # Notify the enterprise admin/s about the new task/s
  addresses = notifier.notify_new_task(tasks)
  if not addresses or len(addresses) == 0:
    # There is no address to send notifications, take default action.
    COMMA = ","
    task_ids = []
    for task in tasks:
      task_ids.append(task['taskid'])

    default_action = config.get('server', 'default_action')
    
    multiple_update(COMMA.join(task_ids), default_action.lower())
    
    print "Tasks " + COMMA.join(task_ids) + " cannot be notified. Applied default action " + default_action
