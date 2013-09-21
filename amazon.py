#!/bin/python

import ConfigParser
import subprocess

config = ConfigParser.ConfigParser()
config.read('workflow.cfg')

amazon_cert = config.get('amazon', 'amazon_cert')
amazon_priv = config.get('amazon', 'amazon_priv')
download_location = config.get('server', 'download_location')

def extract_partition(image_name):
    image_path = download_location + image_name
    args = ['fdisk', '-lu', '/tmp/ABQ_55019395-f8f3-4425-9eda-2e2bc4fa82f5-workflow-instance']
    proc = subprocess.Popen('fdisk -lu /tmp/ABQ_55019395-f8f3-4425-9eda-2e2bc4fa82f5-workflow-instance | grep ^/tmp/ABQ_55019395-f8f3-4425-9eda-2e2bc4fa82f5-workflow-instance', stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    print "program output:", out.split()
    output = out.split()
    subprocess.call("dd if=/tmp/ABQ_55019395-f8f3-4425-9eda-2e2bc4fa82f5-workflow-instance of=/tmp/ABQ_55019395-f8f3-4425-9eda-2e2bc4fa82f5-workflow-instance-root bs=512 skip=%s" % (output[2]), shell=True)

def create_bundle(amazon_account_id, image_name):
    image_path = download_location + image_name
    return subprocess.call("ec2-bundle-image --cert %s --privatekey %s -u %s -r x86_64 --image %s" % (amazon_cert, amazon_priv, amazon_account_id, image_path), shell=True)

def upload_bundle(image_name, amazon_key,amazon_secret, amazon_region):
    image_path = download_location + image_name
    return subprocess.call("ec2-upload-bundle -m /tmp/%s.manifest.xml -b abiquo-import -a %s -s %s  --retry" % (image_path, amazon_key, amazon_secret, amazon_region), shell=True)

def register_ami(image_name, amazon_key, amazon_secret, amazon_region):
    image_path = download_location + image_name
    return subprocess.call("ec2-register abiquo-import/%s.manifest.xml -O %s -W %s --region %s --kernel aki-f2634886 --ramdisk ari-a06348d4" % (image_path, amazon_key, amazon_secret, amazon_region), shell=True)
