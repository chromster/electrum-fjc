#!/usr/bin/env python
from __future__ import print_function

'''
Use KeepKey as a hardware key for opening EncFS filesystem!

Demo usage:

encfs --standard --extpass=./encfs_aes_getpass.py ~/.crypt ~/crypt
'''

import os
import sys
import json
import hashlib
import binascii

from keepkeylib.client import KeepKeyClient, KeepKeyClientDebug

# Python2 vs Python3
try:
    input = raw_input
except NameError:
    pass

def wait_for_devices():
    devices = HidTransport.enumerate()
    while not len(devices):
        sys.stderr.write("Please connect KeepKey to computer and press Enter...")
        input()
        devices = HidTransport.enumerate()

    return devices

def choose_device(devices):
    if not len(devices):
        raise Exception("No KeepKey connected!")

    if len(devices) == 1:
        try:
            return HidTransport(devices[0])
        except IOError:
            raise Exception("Device is currently in use")

    i = 0
    sys.stderr.write("----------------------------\n")
    sys.stderr.write("Available devices:\n")
    for d in devices:
        try:
            t = HidTransport(d)
        except IOError:
            sys.stderr.write("[-] <device is currently in use>\n")
            continue

        client = KeepKeyClient(t)

        if client.features.label:
            sys.stderr.write("[%d] %s\n" % (i, client.features.label))
        else:
            sys.stderr.write("[%d] <no label>\n" % i)
        t.close()
        i += 1

    sys.stderr.write("----------------------------\n")
    sys.stderr.write("Please choose device to use: ")

    try:
        device_id = int(input())
        return HidTransport(devices[device_id])
    except:
        raise Exception("Invalid choice, exiting...")

def main():
    devices = wait_for_devices()
    transport = choose_device(devices)
    client = KeepKeyClient(transport)

    rootdir = os.environ['encfs_root']  # Read "man encfs" for more
    passw_file = os.path.join(rootdir, 'password.dat')

    if not os.path.exists(passw_file):
        # New encfs drive, let's generate password

        sys.stderr.write('Please provide label for new drive: ')
        label = input()

        sys.stderr.write('Computer asked KeepKey for new strong password.\n')
        sys.stderr.write('Please confirm action on your device.\n')

        # 32 bytes, good for AES
        keepkey_entropy = client.get_entropy(32)
        urandom_entropy = os.urandom(32)
        passw = hashlib.sha256(keepkey_entropy + urandom_entropy).digest()

        if len(passw) != 32:
            raise Exception("32 bytes password expected")

        bip32_path = [10, 0]
        passw_encrypted = client.encrypt_keyvalue(bip32_path, label, passw, False, True)

        data = {'label': label,
                'bip32_path': bip32_path,
                'password_encrypted_hex': binascii.hexlify(passw_encrypted)}

        json.dump(data, open(passw_file, 'wb'))

    # Let's load password
    data = json.load(open(passw_file, 'r'))

    sys.stderr.write('Please confirm action on your device.\n')
    passw = client.decrypt_keyvalue(data['bip32_path'],
                                    data['label'],
                                    binascii.unhexlify(data['password_encrypted_hex']),
                                    False, True)

    print(passw)

if __name__ == '__main__':
    main()
