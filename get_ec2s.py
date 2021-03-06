import rsa
import boto3
import json
import base64
import sys
from multiprocessing import Pool

from itertools import chain

KEYS_MAPPING={"mat_test": "/Users/sdashkovsky/.ssh/mat_key.pem"}

def get_win_password(instance_id, key_path):
    if not key_path:
        return ""

    with open(key_path, 'r') as f:
        pk = rsa.PrivateKey.load_pkcs1(f.read())

    client = boto3.client("ec2")
    pwd = client.get_password_data(InstanceId=instance_id).get('PasswordData')
    try:
        password = rsa.decrypt(base64.b64decode(pwd), pk)
    except rsa.pkcs1.DecryptionError as e:
        # sys.stderr.write(f"Cannot decrypt password for instance {instance_id} - {pwd}")
        return str("")

    return str(password.decode())

def get_instance_entry(instance):
    try:
        instance_id = instance.get("InstanceId", "")
        platform = instance.get("Platform", "")

        public_ip_address = instance.get("PublicIpAddress", "")
        public_hostname = instance.get("PublicDnsName", "")

        private_ip_address = instance.get("PrivateIpAddress", "")
        private_hostname = instance.get("PrivateDnsName", "")

        tags = instance.get("Tags")
        key_name = instance.get("KeyName", "nokey")
        name = instance_id

        if tags is not None:
            for tag in tags:
                if tag.get("Key", "").lower() == "name":
                    tagValue = tag.get("Value", "")

                    if tagValue.lower() != "":
                        name = tagValue

                    break

        computer_name = private_ip_address

        if computer_name == "":
            computer_name = public_hostname

        if computer_name == "":
            computer_name = private_hostname

        if computer_name == "":
            computer_name = private_ip_address

        connection = {}

        is_windows = platform.lower() == "windows"

        if not is_windows:
            connection["Type"] = "TerminalConnection"
            connection["TerminalConnectionType"] = "SSH"
            connection["Username"] = "ec2-user"
            connection["KeyFilePath"] = KEYS_MAPPING.get(key_name, "")

        else:
            connection["Type"] = "RemoteDesktopConnection"
            connection["Username"] = "Administrator"
            connection["Password"] = get_win_password(instance_id, KEYS_MAPPING.get(key_name, ""))


        connection["ID"] = instance_id
        connection["Name"] = name
        connection["ComputerName"] = computer_name
        connection["CustomField1"] = instance_id

        return connection
    except Exception as e:
        return None



def get_instances():
    c = boto3.client("ec2")
    instances = c.describe_instances(Filters=[{"Name": "instance-state-code", "Values": ["16"]}],
                                     MaxResults=500)

    reservations = [ _ for _ in instances.get("Reservations", [])]
    instance_list = list( i for i_l in [r.get("Instances", []) for r in reservations] for i in i_l)
    p = Pool(30)
    connections = p.map(get_instance_entry, instance_list)



    store = {
        "Objects": [_ for _ in connections if _ is not None]
    }

    store_json = json.dumps(store)

    return store_json


print(get_instances())
