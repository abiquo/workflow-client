#!/bin/python

import ConfigParser
import subprocess

config = ConfigParser.ConfigParser()
config.read('workflow.cfg')

amazon_cert = config.get('amazon', 'amazon_cert')
amazon_priv = config.get('amazon', 'amazon_priv')

def extract_partition(image_path):
    image_name = image_path.split('/')[-1]
    subprocess.call("qemu-img convert %s %s.raw" % (image_path, image_path), shell=True)
    proc = subprocess.Popen('fdisk -lu %s | grep ^%s' % (image_path, image_path), stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    output = out.split()
    subprocess.call("dd if=%s.raw of=%s-root bs=512 skip=%s" % (image_path, image_path, output[2]), shell=True)

def create_bundle(amazon_account_id, image_path):
    image_name = image_path.split('/')[-1]
    return subprocess.call("ec2-bundle-image --cert %s --privatekey %s -u %s -r x86_64 --image %s-root" % (amazon_cert, amazon_priv, amazon_account_id, image_path), shell=True)

def upload_bundle(image_path, amazon_key, amazon_secret, amazon_region):
    image_name = image_path.split('/')[-1]
    return subprocess.call("ec2-upload-bundle -m %s-root.manifest.xml -b %s -a %s -s %s --location US --retry" % (image_path, image_name.lower().split('_')[1], amazon_key, amazon_secret), shell=True)

def register_ami(image_path, amazon_key, amazon_secret, amazon_region):
    image_name = image_path.split('/')[-1]
    return subprocess.call("ec2-register %s/%s-root.manifest.xml -O %s -W %s --region %s" % (image_name.lower().split('_')[1], image_name, amazon_key, amazon_secret, amazon_region), shell=True)

def region_to_s3_location(amazon_region):
    #regions: us-east-1, us-west-1, us-west-2, eu-west-1, sa-east-1, ap-northeast-1, ap-southeast-1, ap-southeast-2
    #locations: EU,US,us-gov-west-1,us-west-1,us-west-2,ap-southeast-1,ap-southeast-2,ap-northeast-1,sa-east-1
    if amazon_region in ('us-east-1'):
        return "US"
    elif amazon_region in ('eu-west-1'):
        return "EU"
    else:
        return amazon_region

