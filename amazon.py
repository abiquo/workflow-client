#!/bin/python

import ConfigParser
import subprocess

config = ConfigParser.ConfigParser()
config.read('workflow.cfg')

amazon_cert = config.get('amazon', 'amazon_cert')
amazon_priv = config.get('amazon', 'amazon_priv')


def create_bundle(amazon_account_id, image_path):
    return subprocess.call("ec2-bundle-image --cert %s --privatekey %s -u %s -r x86_64 --image %s" % (amazon_cert, amazon_priv, amazon_account_id, image_path), shell=True)

def upload_bundle(image_path, amazon_key,amazon_secret, amazon_region):
    return subprocess.call("ec2-upload-bundle -m /tmp/%s.manifest.xml -b abiquo-import -a %s -s %s  --retry" % (image_path, amazon_key, amazon_secret, amazon_region), shell=True)

def register_ami(image_path, amazon_key, amazon_secret, amazon_region):
    return subprocess.call("ec2-register abiquo-import/%s.manifest.xml -O %s -W %s --region %s --kernel aki-f2634886 --ramdisk ari-a06348d4" % (image_path, amazon_key, amazon_secret, amazon_region), shell=True)
