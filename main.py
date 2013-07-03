import api
import re

link = "/cloud/virtualdatacenters/3/virtualappliances/8/virtualmachines/58"
print api.get_virtualmachine_disks(link)
print ""
print api.get_virtualmachine_details(link)