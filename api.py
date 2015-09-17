#!/bin/python
from pprint import pprint
import ConfigParser
import requests
import xml.etree.ElementTree as xmlparser
import string
import humanize

config = ConfigParser.ConfigParser()
config.read('workflow.cfg')

apiurl = config.get('abiquo', 'api_location')
apiusername = config.get('abiquo', 'api_username')
apipassword = config.get('abiquo', 'api_password')

def get_virtualmachine_disks(rel_vm):
    headers = {'accept': 'application/vnd.abiquo.harddisks+xml'}
    r = requests.get(apiurl + "/" + rel_vm + "/storage/disks", auth=(apiusername, apipassword), headers=headers)
    vm_disks = []
    disks = xmlparser.fromstring(r.text)
    for disk in disks.findall('disk'):
        disk_ = {}
        #if disk.find('sequence').text != "0":
        disk_['sizeInMb'] = humanize.naturalsize(long(disk.find('sizeInMb').text) * 1024 * 1024, gnu=True)
        disk_['sequence'] = disk.find('sequence').text
        disk_['type'] = "Extra Disk"
        disk_['name'] = ""
        vm_disks.append(disk_)

    return vm_disks

def get_virtualmachine_volumes(rel_vm):
    headers = {'accept': 'application/vnd.abiquo.volumes+xml'}
    r = requests.get(apiurl + "/" + rel_vm + "/storage/volumes", auth=(apiusername, apipassword), headers=headers)
    vm_vols = []
    vols = xmlparser.fromstring(r.text)
    for vol in vols.findall('volume'):
        vol_ = {}
        #if vol.find('sequence').text != "0":
        vol_['sizeInMb'] = humanize.naturalsize(long(vol.find('sizeInMB').text) * 1024 * 1024, gnu=True)
        vol_['sequence'] = vol.find('sequence').text
        vol_['type'] = "Volume"
        vol_['name'] = "(" + vol.find('name').text + ")"
        vm_vols.append(vol_)

    return vm_vols

def get_virtualmachine_storage(rel_vm):
    vmdisks = get_virtualmachine_disks(rel_vm)
    vmvols = get_virtualmachine_volumes(rel_vm)

    return vmdisks + vmvols

def get_virtualdatacenter_name(rel_vdc):
    headers = {'accept': 'application/vnd.abiquo.virtualdatacenter+xml'}
    r = requests.get(apiurl + "/" + rel_vdc, auth=(apiusername, apipassword), headers=headers)
    virtualdatacenter = xmlparser.fromstring(r.text)
    return virtualdatacenter.find('name').text

def get_datacenter_name(rel_vdc):
    headers = {'accept': 'application/vnd.abiquo.virtualdatacenter+xml'}
    r = requests.get(apiurl + "/" + rel_vdc, auth=(apiusername, apipassword), headers=headers)
    virtualdatacenter = xmlparser.fromstring(r.text)

    vdclinks = virtualdatacenter.findall('link')

    for vdclink in vdclinks:
        if vdclink.get('rel') == "datacenter":
            headers = {'accept': 'application/vnd.abiquo.datacenter+xml'}
            re = requests.get(vdclink.get('href'), auth=(apiusername, apipassword), headers=headers)
            datacenter = xmlparser.fromstring(re.text)
            return datacenter.find('name').text

def get_virtualapp_name(rel_vapp):
    headers = {'accept': 'application/vnd.abiquo.virtualappliance+xml'}
    r = requests.get(apiurl + "/" + rel_vapp, auth=(apiusername, apipassword), headers=headers)
    virtualapp = xmlparser.fromstring(r.text)
    return virtualapp.find('name').text

def get_enterprise_name(rel_enterprise):
    headers = {'accept': 'application/vnd.abiquo.enterprise+xml'}
    r = requests.get(apiurl + "/" + rel_enterprise, auth=(apiusername, apipassword), headers=headers)
    enterprise = xmlparser.fromstring(r.text)
    return enterprise.find('name').text

def get_name_user(rel_user):
    headers = {'accept': 'application/vnd.abiquo.user+xml'}
    r = requests.get(apiurl + "/" + rel_user, auth=(apiusername, apipassword), headers=headers)
    user = xmlparser.fromstring(r.text)
    userStr = user.find('name').text + " " + user.find('surname').text + " (" + user.find('nick').text + ")"
    return userStr

def get_virtualmachine_details(rel_vm):
    vm_obj = {}
   
    vm_obj['amazon'] = False
    headers = {'accept': 'application/vnd.abiquo.virtualmachine+xml'}
    r = requests.get(apiurl + "/" + rel_vm, auth=(apiusername, apipassword), headers=headers)
    vm = xmlparser.fromstring(r.text)
    vm_obj['vmName'] = vm.find('name').text
    vm_obj['vmCpu'] = vm.find('cpu').text
    vm_obj['vmRam'] = vm.find('ram').text
    
    links = vm.findall("link")
    for link in links:
        if link.attrib["rel"] == "disk0":
            if 'volume' in link.attrib["type"]:
                vm_obj['persistent'] = True
            else:
                vm_obj['persistent'] = False

            headers = {'accept': link.attrib["type"]}
            req = requests.get(link.get("href") , auth=(apiusername, apipassword), headers=headers)
            root_disk = xmlparser.fromstring(req.text)
            vm_obj['vmHd'] = long(root_disk.find("sizeInMb").text) * 1024 * 1024
        elif link.attrib["rel"] == "virtualdatacenter" and link.attrib["title"] == 'AMAZON':
            vm_obj['persistent'] = False
            vm_obj['amazon'] = True

    return vm_obj

def get_user_email(rel_user):
    headers = {'accept': 'application/vnd.abiquo.user+xml'}
    r = requests.get(apiurl + "/" + rel_user, auth=(apiusername, apipassword), headers=headers)
    data_parser = xmlparser.fromstring(r.text)
    user = data_parser.find('user')
    email = data_parser.find('email').text
    return email

def get_single_user_email(rel_user):
    headers = {'accept': 'application/vnd.abiquo.user+xml'}
    r = requests.get(apiurl + "/" + rel_user, auth=(apiusername, apipassword), headers=headers)
    user = xmlparser.fromstring(r.text)
    email = user.find('email').text
    return email

def get_emails_from_role(rel_target):

    # Get the configured role to notify new events
    configuredrole = config.get('abiquo', 'api_approve_role')
    mails = []

    # Get the enterprise of the affected VM
    headers = {'accept': 'application/vnd.abiquo.virtualmachine+xml'}
    r = requests.get(apiurl + "/" + rel_target, auth=(apiusername, apipassword), headers=headers)
    vm = xmlparser.fromstring(r.text)

    for child in vm.findall('link'):
        if child.attrib.get('rel') == "enterprise":
            ent_link = child.attrib.get('href')
    
    # Get enterprise users from VM's enterprise
    headers = {'accept': 'application/vnd.abiquo.userswithroles+xml'}
    r = requests.get(ent_link + "/users", auth=(apiusername, apipassword), headers=headers)
    users = xmlparser.fromstring(r.text)

    for child in users.findall('userWithRole'):
        role = child.find('role').find('name').text
        if role == configuredrole and child.find('email').text:
            mails.append(child.find('email').text)

    # Concatenate all the mails and return them
    return mails
