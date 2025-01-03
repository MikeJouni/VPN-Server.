import platform
import paramiko
import os
from platformdirs import user_data_dir
app_name = "CIS375VPN"
import time
import logging
from observer import Subject
logger = logging.getLogger(__name__)
logging.getLogger('paramiko').setLevel(logging.ERROR)

class VPN_Manager(Subject):
    '''
    Description: Manages the connection to the VPN, allowing for connecting, disconnecting, and monitoring of the VPN.
    '''
    def __init__(self):
        super().__init__([])
        self.is_ready = False
        self.is_connected = False
        self.profile_name = "CIS375VPN"
        self.username = "user"
        self.password = ""
        app_data_path = user_data_dir(app_name)
        path = os.path.join(app_data_path, 'vpn.pbk')
        self.pbk_path = path
        self.is_cert_installed = False
        
        if platform.system() == "Windows":
            from vpn.windows_vpn import Windows_VPN
            self.vpn = Windows_VPN()
        else:
            logger.critical(f"ERROR: Platform {platform.system()} not supported")
            quit()

    def get_vpn_keys(self, server_ip):
        '''
        Description: gets the VPN keys from the server given a server_ip

        param server_ip: IP address of server to connect to
        return: None
        '''
        app_data_path = user_data_dir(app_name)
        path = os.path.join(app_data_path, 'sshkey.pem')
        key = paramiko.RSAKey.from_private_key_file(path)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=server_ip, username="ubuntu", pkey=key)
        sftp = ssh.open_sftp()
        app_data_path = user_data_dir(app_name)
        path = os.path.join(app_data_path, 'cert.pem')
        sftp.get("/etc/swanctl/x509/cert.pem", path)
        path = os.path.join(app_data_path, 'vpnkey.secret')
        sftp.get("/home/ubuntu/vpnkey.secret", path)
        sftp.close()
        ssh.close()
        logger.info("Successfully retrieved server keys")
        return

    def monitor_connection(self):
        '''
        Description: periodically monitor the connection status of the VPN

        return: None
        '''
        while True:
            time.sleep(3)
            if not self.is_ready:
                continue
            try:
                result = self.vpn.status(self.profile_name)
                if result == 0:
                    self.is_connected = True
                else:
                    self.is_connected = False
                self.notify(None, self)
            except Exception as e:
                logger.error(f"Error monitoring vpn connection: {e}")

    def connect(self, server_address):
        '''
        Description: Connects to the VPN using the server_address

        param server_address: Address of server to connect to
        return: None
        '''
        self.get_vpn_keys(server_address)
        app_data_path = user_data_dir(app_name)
        path = os.path.join(app_data_path, 'cert.pem')
        if not self.is_cert_installed:
            self.vpn.install_cert(path)
            self.is_cert_installed = True
        time.sleep(0.3)
        self.vpn.create_profile(self.profile_name, server_address, self.pbk_path)
        app_data_path = user_data_dir(app_name)
        path = os.path.join(app_data_path, 'vpnkey.secret')
        file = open(path)
        password = file.readline().strip()
        ret = self.vpn.connect(self.profile_name, self.username, password, self.pbk_path)
        if ret != 0:
            raise Exception
        self.is_ready = True
        return
    
    def disconnect(self):
        '''
        Description: Disconnects from the VPN

        return: the status of the VPN disconnection(successful or unsuccessful)
        '''
        return self.vpn.disconnect(self.profile_name)
    
    def delete_profile(self):
        '''
        Description: delete the VPN profile from the system

        return None
        '''
        self.is_cert_installed = False
        self.vpn.delete_profile(self.profile_name)
        return
