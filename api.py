#!/bin/python
from pprint import pprint
import time
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
download_location = config.get('server', 'download_location')

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

def get_dc_name(rel_dc):
    re = requests.get(rel_dc, auth=(apiusername, apipassword), headers={'accept': 'application/vnd.abiquo.datacenter+xml'})
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
    vm_obj['vmState'] = vm.find('state').text
    
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

    useraccept = {'Accept': 'application/vnd.abiquo.userswithroles+xml'}
    # Get the enterprise of the affected VM
    r = requests.get(apiurl + "/" + rel_target, auth=(apiusername, apipassword))
    vm = xmlparser.fromstring(r.text)

    for child in vm.findall('link'):
        if child.attrib.get('rel') == "enterprise":
            ent_link = child.attrib.get('href')
    
    # Get enterprise users from VM's enterprise
    r = requests.get(ent_link + "/users", auth=(apiusername, apipassword), headers=useraccept)
    users = xmlparser.fromstring(r.text)

    for child in users.findall('userWithRole'):
        role = child.find('role').find('name').text
        if role == configuredrole and child.find('email').text:
            mails.append(child.find('email').text)

    # Concatenate all the mails and return them
    return mails

def get_user_creds(rel_user):
    u = requests.get(apiurl + "/" + rel_user, auth=(apiusername, apipassword))
    userxml = xmlparser.fromstring(u.text)
    for child in userxml.findall('link'):
        if child.attrib.get('rel') == "enterprise":
            ent_link = child.attrib.get('href')

    l = requests.get(ent_link + "/limits", auth=(apiusername, apipassword))
    limxml = xmlparser.fromstring(l.text)

    creds = {}
    for limit in limxml.findall('limit'):
        for child in limit.findall('link'):
            if child.attrib.get('rel') == "datacenter":
                dc_type = child.attrib.get('type')
                dcurl = child.attrib.get('href')
            elif child.attrib.get('rel') == "edit":
                limurl = child.attrib.get('href')

        if dc_type == "application/vnd.abiquo.publicdatacenter+xml":
            c = requests.get(limurl + "/credentials", auth=(apiusername, apipassword))
            credxml = xmlparser.fromstring(c.text)
            if credxml.findall('credentials') is not None:
                for credential in credxml.findall('credentials'):
                    crd = {}
                    crd['access'] = credential.find('access').text
                    crd['key'] = credential.find('key').text
                    creds[dcurl] = crd

    return creds

def instancevm(rel_vm, instance_name, wait):
    r = requests.get(apiurl + "/" + rel_vm, auth=(apiusername, apipassword) )
    vms = xmlparser.fromstring(r.text)
    instance_link = ""
    state_link = ""
    for child in vms.findall('link'):
        if child.attrib.get('rel') == "instance":
            instance_link = child.attrib.get('href')
        if child.attrib.get('rel') == "state":
            state_link = child.attrib.get('href')
    vm_state = vms.find('state').text

    # POWER OF the VM if it is ON
    if vm_state == "ON":
        ## POWER OFF
        poffvm = "<virtualmachinestate><state>OFF</state></virtualmachinestate>"
        headers = {"Content-Type": "application/vnd.abiquo.virtualmachinestate+xml; version=2.6;"}
        pr = requests.put(state_link, poffvm, auth=(apiusername, apipassword), headers=headers )
        req = xmlparser.fromstring(pr.text)
        link_status = ""
        for child in req.findall('link'):
            if child.attrib.get('rel') == "status":
                link_status = child.attrib.get('href')
        wait_task(link_status)
        vm_state = get_virtualmachine_details(rel_vm)['vmState']

    if vm_state == "OFF":
        headers = {
            "Accept": "application/vnd.abiquo.acceptedrequest+xml; version=2.6",
            "Content-Type": "application/vnd.abiquo.virtualmachineinstance+xml; version=2.6;"
        }
        instancepost = "<virtualmachineinstance><instanceName>" + instance_name + "</instanceName></virtualmachineinstance>"
        r = requests.post(instance_link, instancepost, auth=(apiusername, apipassword), headers=headers )
        req = xmlparser.fromstring(r.text)
        for child in req.findall('link'):
            if child.attrib.get('rel') == "status":
                link_status = child.attrib.get('href')
        result = wait_task(link_status)
        for child in result.findall('link'):
            if child.attrib.get('rel') == "result":
                new_instance = child.attrib.get('href')
        
        return new_instance
    else:
        return False

def wait_task(task_lnk):
    while True:
        r = requests.get(task_lnk, auth=(apiusername, apipassword))
        task = xmlparser.fromstring(r.text)
        task_state = task.find('state').text
        if task_state == "FINISHED_SUCCESSFULLY":
            return task
        elif task_state == "FINISHED_UNSUCCESSFULLY":
            return -1
        time.sleep(5)

def download_template(tmpl_link):
    t = requests.get(tmpl_link, auth=(apiusername, apipassword))
    tmplxml = xmlparser.fromstring(t.text)
    for child in tmplxml.findall('link'):
        if child.attrib.get('rel') == "diskfile":
            fileurl = child.attrib.get('href')
            break

    template_id = tmplxml.find('id').text
    local_filename = download_location + "/" + template_id
    
    diskdownload = requests.get(fileurl, auth=(apiusername, apipassword), stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in diskdownload.iter_content(chunk_size=1024): 
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
    return local_filename

def get_user_amazon_id(rel_user):
    # Get the enterprise of the affected VM
    r = requests.get(apiurl + "/" + rel_user, auth=(apiusername, apipassword))
    user = xmlparser.fromstring(r.text)

    for child in user.findall('link'):
        if child.attrib.get('rel') == "enterprise":
            ent_link = child.attrib.get('href')

    r = requests.get(ent_link, auth=(apiusername, apipassword))
    enterprise = xmlparser.fromstring(r.text)

    for child in enterprise.findall('link'):
        if child.attrib.get('rel') == "properties":
            prop_link = child.attrib.get('href')

    r = requests.get(prop_link, auth=(apiusername, apipassword))
    properties = xmlparser.fromstring(r.text)

    for child in properties.findall('properties'):
        for p in child.findall('entry'):
            if p.find('key').text == "amazon account id":
                return p.find('value').text
    return ""
