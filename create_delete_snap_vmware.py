#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
import getpass
import ssl
from ansible.module_utils.basic import AnsibleModule
from pyVim.connect import SmartConnect
from pyVmomi import vim
from ssl import CERT_NONE, PROTOCOL_TLSv1_2, SSLContext
s = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
s.verify_mode = ssl.CERT_NONE
def take_snapshot(hostname,vcenter,username,password,action):
    print("starting")
    break_out_flag = False
    for instance in vcenter:
        try:
           c =  SmartConnect(host=instance, user=username, pwd=password, sslContext=s)
           print("connected to vcenter")
        except Exception as e:
           print("failed")
           print(str(e))

        content = c.content
        container = content.viewManager.CreateContainerView(content.rootFolder,[vim.VirtualMachine],True)
        for vm in container.view:
            print("Searching for VM....")
            if hasattr(vm.guest, 'hostName') and vm.guest.hostName: 
#               if hostname in vm.guest.hostName:
               if hostname.lower() ==  str(vm.guest.hostName).lower().split(".")[0]:
                  if action == "delete":
                      print("VM found, now Removing backup for " + vm.guest.hostName)
                      vm.snapshot.rootSnapshotList[0].snapshot.RemoveSnapshot_Task(True)
                      output = "remove_succ"
                      break_out_flag = True
                      break
                  elif action == "create": 
                      print("VM found, now taking backup for " + vm.guest.hostName)
                      ds_vm = vm.datastore
                      obj_ds = content.viewManager.CreateContainerView(content.rootFolder,[vim.Datastore],True)
                      for data_store in obj_ds.view:
                          if data_store == ds_vm[0]:
                             free_space = int(data_store.summary.freeSpace/(1024*1024*1024))
                             total_ds_space = int(data_store.summary.capacity/(1024*1024*1024))
                             print("Free space in DS is {0} Gigs".format(free_space))
                      x = vm.storage.perDatastoreUsage[0].committed
                      size = int(x/(1024*1024*1024))
                      print("size of VM is {0} Gigs".format(size))
                      if ((free_space - size)/total_ds_space)*100 > 15:
                          print("trying to create snapshot")
                          vm.CreateSnapshot_Task(name='ansible_auto_snapshot',description='automated_snapshot',memory=False,quiesce=False)
                          print("snapshot is created successfully")
                          output = "successful"
                          break_out_flag = True
                          break
                      else:
                          print("Not enough free space in DS")
                          output = "failed"
                          break_out_flag = True
                          break
        if break_out_flag:
            break
    return output
def run_module():
    module_args = dict(
                     hostname=dict(type='str',required=True),
                     vcenter=dict(type='list',required=True),
                     username=dict(type='str',required=True),
                     password=dict(type='str',required=True),
                     action=dict(type='str',required=True))
    module = AnsibleModule(argument_spec=module_args,supports_check_mode=False)
    try:
       res = take_snapshot(module.params['hostname'],module.params['vcenter'],module.params['username'],module.params['password'],module.params['action'])
       if res == "successful":
          module.exit_json(msg="Finished searching and taken snapshot for VM",rc=0,changed=True)
       elif res == "remove_succ":
          module.exit_json(msg="Finished searching and Removed snapshot for VM",rc=0,changed=True) 
       elif res == "failed":
          module.fail_json(msg="Not Enough Free space in DataStore, please clear the space")
#       res = snapshot(module.params['hostname'])
    except Exception as e:
       module.fail_json(msg="Got an exception while attempting to query the vcenter")
#    module.exit_json(msg="Finished searching and taken snapshot for VM",rc=0,changed=True)

def main():
    run_module()

if __name__ == '__main__':
   main()
