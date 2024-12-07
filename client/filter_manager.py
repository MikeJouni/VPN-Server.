import paramiko
import os
import logging
logger = logging.getLogger(__name__)

class Filter_Manager:
    def __init__(self, server_address="localhost"):
        self.block_list = [] #list of block lists = dicts containing name and enabled/disabled status
        self.server_host = server_address #server address passed as parameter when instance of filter manager created
        self.is_updated = False
        # initialize block lists
        self.get_block_lists()

    def get_block_lists(self):
        if os.path.exists('data/block/'): #check if path exists, if so, loop through directory and append all lists to block_list, disabled by default
            for list_name in os.listdir('data/block/'):
                # verify extension
                if list_name.endswith(".block"):
                    # add list
                    self.block_list.append({"name": list_name, "enabled": False})
                    logger.debug(f"Found Client block list {list_name}")
        else:
            logger.error("Block list path not found")

    def enable_list(self, list_name):
        for list in self.block_list: #iterate through block_list, if list_name is found, enable it, else, print error
            if list['name'] == list_name + ".block":
                list['enabled'] = True
                logger.info(f"Enabled block list: {list_name}")
                return
        logger.error(f"Block list {list_name} not found")

    def disable_list(self, list_name): #iterate through block_list, if list_name is found, disable it, else, print error
        for list in self.block_list:
            if list['name'] == list_name + ".block":
                list['enabled'] = False
                logger.info(f"Disabled block list: {list_name}")
                return
        logger.error(f"Block list {list_name} not found")

    def send_update(self):

        enabled_lists = [] #create list containing only enabled lists
        disabled_lists = [] #create list containing only disabled lists
        for list in self.block_list:
            if(list['enabled'] == True):
                enabled_lists.append(list)
            elif (list['enabled'] == False):
                disabled_lists.append(list)

        try:
            key = paramiko.RSAKey.from_private_key_file("data/sshkey.pem")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh.connect(hostname=self.server_host, username="ubuntu", pkey=key)
            sftp = ssh.open_sftp()
            try:
                sftp.stat('/home/ubuntu/dnsmasq/')
            except:
                sftp.mkdir('/home/ubuntu/dnsmasq/')

            for list in enabled_lists: #looping through enabled lists, copy the list and send to remote spot in server
                local_path = 'data/block/' + list['name']
                remote_path = '/home/ubuntu/dnsmasq/' + list['name']

                sftp.put(local_path, remote_path)

            for list in disabled_lists: #looping through disabled lists, copy an empty list, and send to the server
                local_path = 'data/block/empty.txt'
                remote_path = '/home/ubuntu/dnsmasq/' + list['name']

                sftp.put(local_path, remote_path)
            
            sftp.put('data/block/empty.txt', '/home/ubuntu/dnsmasq/flag')

            sftp.close()
            ssh.close()

            logger.info("Enabled block lists successfully sent to the server.")

        except Exception as e:
            logger.error(f"Error sending update: {e}")
    
    def get_server_lists(self):
        if not self.is_updated:
            # ensure server files are consistent with client
            self.send_update()
            self.is_updated = True
            return
        current_block_list = []
        key = paramiko.RSAKey.from_private_key_file("data/sshkey.pem")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(hostname=self.server_host, username="ubuntu", pkey=key)
        sftp = ssh.open_sftp()
        try:
            lists = sftp.listdir_attr('/home/ubuntu/dnsmasq/')
        except Exception as e:
            logger.error(f"Unable to get server block lists {e}")

        for list in lists:
            # skip non block files
            if not list.filename.endswith(".block"):
                logger.debug(f"Skipping file {list.filename}")
                continue
            if list.st_size == 0:
                current_block_list.append({"name": list.filename, "enabled": False})
                logger.debug(f"{list.filename}: Disabled")
            else:
                current_block_list.append({"name": list.filename, "enabled": True})
                logger.debug(f"{list.filename}: Enabled")
                
        self.block_list = current_block_list
        sftp.close()
        ssh.close()

