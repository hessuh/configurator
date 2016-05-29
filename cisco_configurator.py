#!/usr/bin/env python3

from pprint import pprint
from time import sleep
import argparse
import getpass
import json
import os
import paramiko
import re
import subprocess
import sys


def verbose(func):
    def decorated_func(test):
        print("Setting verbosity for: ", func.__name__)
        func(test)
    return decorated_func


class SSHConnection():
    def __init__(self, hostname, username, password, port=22):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.client_pre = paramiko.SSHClient()
        self.client = None
        self.__openConnection()

    def __openConnection(self):
        try:
            self.client_pre.load_system_host_keys()
            self.client_pre.set_missing_host_key_policy(paramiko.WarningPolicy())

            if not self.username:
                self.username = os.getusername()

            self.client_pre.connect(self.hostname,
                                    port=self.port,
                                    username=self.username,
                                    password=self.password,
                                    allow_agent=False,
                                    look_for_keys=False
                                    )
            self.client = self.client_pre.invoke_shell()
            output = self.client.recv(65535)
            print(output)
        finally:
            print(" Connection to {host} successfully set up. ".
                  format(host=self.hostname).center(80, '*'))

    def __del__(self):
        try:
            self.client.close()
        except Exception as e:
            print("Caught exception: ", e)

    def ssh_communicate(self, command):
        # This is not to overwhelm the receiver with commands
        print("Executing command: ", command)
        try:
            self.client.send(command + "\n")
            sleep(.5)
            output = self.client.recv(65535).decode('ascii')
            total_output = output
            while "<--- More --->" in output:
                print("MORE FOUND")
                self.client.send(" ".encode('ascii'))
                sleep(.5)
                output = self.client.recv(65535).decode('ascii')
                total_output += output

        except Exception as e:
            print(e)
        finally:
            return total_output


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostfile', '-f',
                        default="hosts.json",
                        type=argparse.FileType('r'),
                        help='host configuration file')
    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='verbose flag')

    args = parser.parse_args()
    return args


def print_arguments(args):
    print("""
Given arguments:
    hostname: {host}
    port: {port}
    username: {username}
    password: hidden
    tunnel destination: {tunnel}
""".format(host=args.host,
           port=args.port,
           username=args.user,
           tunnel=args.tunnel))


class Device:
    def __init__(self, data):
        self.replace = {}
        for key in data['replace']:
            self.replace[key] = data['replace'][key]
        self.commands = []
        pattern = re.compile('|'.join(self.replace.keys()))
        for command in data['commands']:
            self.commands.append(
                pattern.sub(lambda x: self.replace[x.group()], command))


class Host:
    def __init__(self, data):
        self.hostname = data['hostname']
        self.username = data['username']
        self.password = data['password']
        self.port = data['port']
        self.device = Device(data['device'])


class Hosts:
    def __init__(self, data):
        self.hosts = []
        for host in data['hosts']:
            self.hosts.append(Host(data['hosts'][host]))


def main():
    args = arg_parser()
    data = json.load(args.hostfile)
    hosts = Hosts(data)
    for host in hosts.hosts:
        print("""
{host}
{port}
{name}
""".format(name=host.username,
           pwd=host.password,
           host=host.hostname,
           port=host.port))

        ssh_connection = SSHConnection(hostname=host.hostname,
                                       username=host.username,
                                       password=host.password,
                                       port=host.port)
        for command in host.device.commands:
            print(ssh_connection.ssh_communicate(command))
        print("Executed all commands successfully for the host {host}"
              .format(host=host.hostname).center(80, '*'))

if __name__ == '__main__':
    main()
