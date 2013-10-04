import api

#api.deploy_amazon('297','32','<link title="t1.micro" rel="hardwareprofile" type=#"application/vnd.abiquo.hardwareprofile+xml" 
	# href="http://192.168.2.219:80/api/admin/datacenters/3/hardwareprofiles/6"/>',
	# '<link title="ami-a93133dd" 
	# rel="virtualmachinetemplate" type="application/vnd.abiquo.virtualmachinetemplate+xml" 
	# href="http://192.168.2.219:80/api/admin/enterprises/1/datacenterrepositories/3/virtualmachinetemplates/66"/>')

vapp_url = '/cloud/virtualdatacenters/297/virtualappliances/32'
ami_url = '/admin/enterprises/1/datacenterrepositories/3/virtualmachinetemplates/0'
ami_name = 'ami-02b55375'
profile_url = '/admin/datacenters/3/hardwareprofiles/6'

# api.create_amazon(vapp_url,profile_link,ami_link)

# print api.get_link_name(ami_url)

api.deploy_amazon(vapp_url,ami_url,ami_name,profile_url)