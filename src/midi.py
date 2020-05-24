""" for each input device event we create a multicast message """

import time
import rtmidi

import socket
import struct
import sys
import re

from collections import defaultdict

from common import DEFAULT_MULTICAST_ADDRESS, info, debug, error

DEFAULT_PORT_FOR_MIDI = 33221

API_MAP = {
        'alsa': rtmidi.API_LINUX_ALSA, 
        'osx_core': rtmidi.API_MACOSX_CORE, 
        'dummy': rtmidi.API_RTMIDI_DUMMY, 
        'jack': rtmidi.API_UNIX_JACK, 
        'unspecified': rtmidi.API_UNSPECIFIED, 
        'windows': rtmidi.API_WINDOWS_MM}

class JackCastMidiReceiver():
    def __init__(self, multicast_group=DEFAULT_MULTICAST_ADDRESS, port=DEFAULT_PORT_FOR_MIDI):
        self.multicast_group = multicast_group
        self.server_address = ('', port)

        # Create the socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Bind to the server address
        self.sock.bind(self.server_address)

        group = socket.inet_aton(self.multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.midi_outs = {}
        self.re_prg = re.compile(r'{"midi_message":\[(\d+),(\d+),(\d+)\],"deltatime":([^,]*),"src":"([^"]+)"}')

        self.midi_outs = defaultdict(dict)

    def msg_scanner(self, msg):
        debug(msg)
        res_groups = self.re_prg.match(msg).groups()
        return ([int(res_groups[0]), int(res_groups[1]), int(res_groups[2])], float(res_groups[3]), res_groups[4])

    def recv_midi(self):
        debug('\nwaiting to receive message')
        data, address = self.sock.recvfrom(1024)
        (midi_msg, deltatime, src) = self.msg_scanner(data.decode('ascii'))
        debug(midi_msg, deltatime, src)
        
        midi_outs_per_ip = self.midi_outs[address]
        if not src in  midi_outs_per_ip:
            midi_out = rtmidi.MidiOut(API_MAP['jack'])
            midi_out.open_virtual_port(f"mcast-{address}-{src}")
            midi_outs_per_ip[src] = midi_out
        else:
            midi_out = midi_outs_per_ip[src]

        midi_out.send_message(midi_msg)
    
    def run(self):
        while True:
            self.recv_midi()

class JackCastMidiSender:
    class MidiInputHandler(object):
        def __init__(self, midicast_sender, name):
            self._wallclock = time.time()
            self.midicast_sender = midicast_sender
            self.src_name = name

        def __call__(self, event, src):
            message, deltatime = event
            debug(message, deltatime)
            message=",".join(map(str, message))
            msg=f'{{"midi_message":[{str(message)}],"deltatime":{str(deltatime)},"src":"{self.src_name}"}}'
            self.midicast_sender.send_midi_message(msg)

    def __init__(self, multicast_group=None):
        self.multicast_group = ('224.0.0.251', 12345)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.2)
        ttl = struct.pack('b', 1)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    def send_midi_message(self, midi_message):
        # Send data to the multicast group
        debug(f'sending {midi_message}')
        sent = self.sock.sendto(bytes(midi_message, 'ascii'), self.multicast_group)

    def run(self):
        dummy_midi_in = rtmidi.MidiIn(API_MAP['jack'])
        midi_ins = []
        for port in range(dummy_midi_in.get_port_count()):
            name = dummy_midi_in.get_port_name(port)
            midi_in = rtmidi.MidiIn(API_MAP['jack'])
            midi_in.open_port(port)
            midi_in.set_callback(self.MidiInputHandler(self, name))
            midi_ins.append(midi_in)
            
        while True:
            time.sleep(10)
            debug("wakeup")


