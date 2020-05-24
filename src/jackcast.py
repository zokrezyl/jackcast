#!/usr/bin/env python3

import argparse
import logging
import sys
import os
import re

from common import DEFAULT_MULTICAST_ADDRESS, DEFAULT_PORT_FOR_AUDIO, DEFAULT_PORT_FOR_MIDI


def lowercase(string):
    return str(string).lower()

def snakecase(string):
    string = re.sub(r"[\-\.\s]", '_', str(string))
    if not string:
        return string
    return lowercase(string[0]) + re.sub(r"[A-Z]", lambda matched: '_' + lowercase(matched.group(0)), string[1:])

def spinalcase(string):
    return re.sub(r"_", "-", snakecase(string))


class Command:
    _needs_subcmd = True
    usage = "<undefined>"
    description = "<undefined>"

    def __init__(self, subparsers):
        self.subparsers = subparsers
        self.command = spinalcase(self.__class__.__name__.split("Command")[1])
        self.parser = self.subparsers.add_parser(
            self.command,
            usage=self.usage,
            description=self.description)
        self.add_subparser()

    def add_subparser(self):
        raise Exception("this method should be defined in the subclass")



class CommandAudioSender(Command):
    usage=f"{sys.argv[0]} sender [OPTIONS]"
    description="Sends jack aaudio over network"

    def add_subparser(self):
        self.parser.add_argument('-u', '--unicast', 
                help="unicast destination IP address (overrides the default multicast)")
        self.parser.add_argument('-p', '--port', 
                help=f"UDP port to send to default (default: {DEFAULT_PORT_FOR_AUDIO})", 
                default=33220)
        self.parser.add_argument('-m', '--multicast', 
                help=f"destination multicast IP address (default: {DEFAULT_MULTICAST_ADDRESS})", 
                default=DEFAULT_MULTICAST_ADDRESS)

    def run(self, args):
        from audio import JackCastAudioSender
        JackCastAudioSender().run()



class CommandAudioReceiver(Command):
    usage=f"{sys.argv[0]} sender [OPTIONS]"
    description="Sends jack aaudio over network"

    def add_subparser(self):
        self.parser.add_argument('-u', '--unicast', 
                help="just listen on UDP port, no multicast", 
                action='store_true')
        self.parser.add_argument('-p', '--port', 
                help=f"UDP port to listen on (default: {DEFAULT_PORT_FOR_AUDIO})", 
                default=33220)
        self.parser.add_argument('-m', '--multicast', 
                help=f"listen on multicast IP address (default: {DEFAULT_MULTICAST_ADDRESS})", 
                default=DEFAULT_MULTICAST_ADDRESS)

    def run(self, args):
        from audio import JackCastAudioReceiver
        JackCastAudioReceiver().run()


class CommandMidiSender(Command):
    usage=f"{sys.argv[0]} sender [OPTIONS]"
    description="Sends jack aaudio over network"

    def add_subparser(self):
        self.parser.add_argument('-d', '--destination', 
                help="destination IP address")
        self.parser.add_argument('-p', '--port', 
                help="UDP port to send to (default: {DEFAULT_PORT_FOR_MIDI})", 
                default=DEFAULT_PORT_FOR_MIDI)
        self.parser.add_argument('-m', '--multicast', 
                help="destination multicast IP address (default: {DEFAULT_MULTICAST_ADDRESS})", 
                default=DEFAULT_MULTICAST_ADDRESS)

    def run(self, args):
        from midi import JackCastMidiSender
        JackCastMidiSender().run()

class CommandMidiReceiver(Command):
    usage=f"{sys.argv[0]} midi-sender [OPTIONS]"
    description="Sends jack aaudio over network"

    def add_subparser(self):
        self.parser.add_argument('-p', '--port', 
                help="UDP port to listen on (default: {DEFAULT_PORT_FOR_MIDI})", 
                default=DEFAULT_PORT_FOR_MIDI)
        self.parser.add_argument('-m', '--multicast', 
                help="listen on multicast IP address", 
                default=DEFAULT_MULTICAST_ADDRESS)

    def run(self, args):
        from midi import JackCastMidiReceiver
        JackCastMidiReceiver().run()

def run(raw_args=None):

    parser = argparse.ArgumentParser(
        usage=f"{sys.argv[0]} [OPTIONS] COMMAND",
        description="Audio and midi cast over Network",
        epilog="")
    parser.add_argument('--log-level',
                        choices=['debug', 'info', 'warn', 'error', 'fatal'],
                        default='info')
    parser.add_argument('-j', '--jack-client-lib-bin-path',
                        help="where to search for the jack client lib binaries")

    subparsers = parser.add_subparsers(dest='command')

    cmd_map = {}
    for cmd in [
            CommandAudioSender(subparsers),
            CommandAudioReceiver(subparsers),
            CommandMidiSender(subparsers),
            CommandMidiReceiver(subparsers)]:
        cmd_map[cmd.command] = cmd

    #args = parser.parse_args()
    if raw_args:
        args = parser.parse_known_args(raw_args)
    else:
        args = parser.parse_known_args()

    log_level = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARNING,
        'error': logging.ERROR,
        'fatal': logging.CRITICAL
    }[args[0].log_level]


    logger = logging.getLogger()
    logger.setLevel(log_level)
    for handler in logger.handlers:
        handler.setLevel(log_level)

    if args[0].command is None:
        parser.print_help()
        return 1

    if args[0].jack_client_lib_bin_path:
        print('urraa..')
        os.environ['PATH'] = f"{args[0].jack_client_lib_bin_path};{os.environ['PATH']}"

    cmd = cmd_map[args[0].command]
#    if cmd.needs_subcmd and args[0].sub_cmd is None:
#        cmd.parser.print_help()
#        return
#
    return cmd.run(args)

if __name__ == "__main__":
    run()
