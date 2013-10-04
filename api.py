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

    r = requests.get(apiurl + "/" + rel_vm + "/storage/disks", auth=(apiusername, apipassword))
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
    r = requests.get(apiurl + "/" + rel_vm + "/storage/volumes", auth=(apiusername, apipassword))
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
    r = requests.get(apiurl + "/" + rel_vdc, auth=(apiusername, apipassword))
    virtualdatacenter = xmlparser.fromstring(r.text)
    return virtualdatacenter.find('name').text

def get_datacenter_name(rel_vdc):
    r = requests.get(apiurl + "/" + rel_vdc, auth=(apiusername, apipassword))
    virtualdatacenter = xmlparser.fromstring(r.text)

    vdclinks = virtualdatacenter.findall('link')

    for vdclink in vdclinks:
        if vdclink.get('rel') == "datacenter":
            re = requests.get(vdclink.get('href'), auth=(apiusername, apipassword), headers={'accept': 'application/vnd.abiquo.datacenter+xml'})
            datacenter = xmlparser.fromstring(re.text)
            return datacenter.find('name').text

def get_virtualapp_name(rel_vapp):
    r = requests.get(apiurl + "/" + rel_vapp, auth=(apiusername, apipassword))
    virtualapp = xmlparser.fromstring(r.text)
    return virtualapp.find('name').text

def get_enterprise_name(rel_enterprise):
    r = requests.get(apiurl + "/" + rel_enterprise, auth=(apiusername, apipassword))
    enterprise = xmlparser.fromstring(r.text)
    return enterprise.find('name').text

def get_name_user(rel_user):
    r = requests.get(apiurl + "/" + rel_user, auth=(apiusername, apipassword))
    user = xmlparser.fromstring(r.text)
    userStr = user.find('name').text + " " + user.find('surname').text + " (" + user.find('nick').text + ")"
    return userStr

def get_virtualmachine_details(rel_vm):
    vm_obj = {}
   
    vm_obj['amazon'] = False
    r = requests.get(apiurl + "/" + rel_vm, auth=(apiusername, apipassword))
    vm = xmlparser.fromstring(r.text)
    vm_obj['vmName'] = vm.find('name').text
    vm_obj['vmCpu'] = vm.find('cpu').text
    vm_obj['vmRam'] = vm.find('ram').text
    
    if vm.find('hdInBytes').text == "0":
        vm_obj['persistent'] = True
        
        links = vm.findall("link")
        for link in links:
            if link.attrib["rel"] == "disk0":
                req = requests.get(link.get("href") , auth=(apiusername, apipassword))
                root_disk = xmlparser.fromstring(req.text)
                vm_obj['vmHd'] = long(root_disk.find("sizeInMB").text) * 1024 * 1024
	    elif link.attrib["rel"] == "virtualdatacenter" and link.attrib["title"] == 'AMAZON':
		vm_obj['persistent'] = False
		vm_obj['amazon'] = True
    else:
        vm_obj['vmHd'] = vm.find('hdInBytes').text
        vm_obj['persistent'] = False

    return vm_obj

def get_user_email(rel_user):
    r = requests.get(apiurl + "/" + rel_user, auth=(apiusername, apipassword))
    data_parser = xmlparser.fromstring(r.text)
    user = data_parser.find('user')
    email = data_parser.find('email').text
    return email

def get_single_user_email(rel_user):
    r = requests.get(apiurl + "/" + rel_user, auth=(apiusername, apipassword))
    user = xmlparser.fromstring(r.text)
    email = user.find('email').text
    return email

def get_emails_from_role(rel_target):

    # Get the configured role to notify new events
    configuredrole = config.get('abiquo', 'api_approve_role')
    mails = []

    # Get the enterprise of the affected VM
    r = requests.get(apiurl + "/" + rel_target, auth=(apiusername, apipassword))
    vm = xmlparser.fromstring(r.text)

    for child in vm.findall('link'):
        if child.attrib.get('rel') == "enterprise":
            ent_link = child.attrib.get('href')
    
    # Get enterprise users from VM's enterprise
    r = requests.get(ent_link + "/users", auth=(apiusername, apipassword))
    users = xmlparser.fromstring(r.text)

    for child in users.findall('userWithRole'):
        role = child.find('role').find('name').text
        if role == configuredrole and child.find('email').text:
            mails.append(child.find('email').text)

    # Concatenate all the mails and return them
    return mails

def deploy_amazon(vapp_url,ami_url,ami_name,hardwareprofile_url):

    # Expects url from
    # vapp
    # ami
    # hardware probile
    hwprofile_name = get_link_name(hardwareprofile_url)

    data = xmlparser.Element("virtualMachine")
    xmlparser.SubElement(data, "link", { 'title':ami_name, 'rel':'virtualmachinetemplate', 'type':'application/vnd.abiquo.virtualmachinetemplate+xml', 'href':apiurl + ami_url })
    xmlparser.SubElement(data, "link", { 'title':hwprofile_name, 'rel':'hardwareprofile', 'type':'application/vnd.abiquo.hardwareprofile+xml', 'href':apiurl + hardwareprofile_url })
    xmlparser.SubElement(data, "name").text = ami_name
    xmlparser.SubElement(data, "nodeName").text = ami_name


    entity =  xmlparser.tostring(data, encoding='UTF-8')
    print xmlparser.dump(data)
    url = config.get('abiquo', 'api_location') + vapp_url + "/virtualmachines"

    headers = { 'Accept':'application/vnd.abiquo.virtualmachinewithnode+xml; version=2.6','Content-Type':'application/vnd.abiquo.virtualmachinewithnode+xml; version=2.6' }

    try:
        r = requests.post(url, entity, headers=headers, auth=(config.get('abiquo', 'api_username'),config.get('abiquo', 'api_password')))
        print "request"
        print r
    except Exception as e:
        print "There was an error comunicating with Abiquo API."
        print e
    return 0


def get_link_name(url):
    r = requests.get(apiurl + url, auth=(apiusername, apipassword))
    print r.text
    xml = xmlparser.fromstring(r.text)
    name = xml.find('name').text
    return name



    