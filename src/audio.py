#!/usr/bin/env python3
import jack
import threading
import queue
import time

import socket
import struct
import sys
import hexdump

from common import DEFAULT_MULTICAST_ADDRESS, info, debug, error

DEFAULT_PORT_FOR_AUDIO = 33220

class JackCastAudioReceiver():
    def __init__(self, port = 33220, multicast_group = DEFAULT_MULTICAST_ADDRESS, iface=None, no_multicast=False):
        self.iface = iface  #TODO
        self.no_multicast = no_multicast #TODO
        self.port = port
        self.multicast_group = multicast_group
    
        server_address = ('', self.port)

        # Create the socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Bind to the server address
        self.sock.bind(server_address)

        group = socket.inet_aton(self.multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.client = jack.Client("jackcast-rcv")
        self.client.outports.register("output_1")
        self.client.outports.register("output_2")
        self.samples = []
        self.header_len = 32
        self.prev_time_here = 0
        self.prev_counter = 0

        @self.client.set_process_callback
        def callback(frames):
            if self.prev_counter == 0:
                debug("initializiing ...")
                self.latency = 1000*self.client.blocksize/self.client.samplerate
                while not self.queue.empty():
                    self.queue.get()
            time_here = time.time_ns()
            try:
                data = self.queue.get(block=False)
            except queue.Empty as exc:
                debug("no data ...")
                self.prev_counter = 1
                return
            header = data[:self.header_len]
            debug("callback...", frames, self.queue.qsize(), (time_here - self.prev_time_here)/1000000)
            (time_should, time_there, counter, payload_per_port_size, num_ports) = struct.unpack('qqqii', header)
            td1 = (time_there - time_here)/ 1000000
            td2 = (time_there - time_should)/ 1000000
            td3 = (time_here - time_should)/ 1000000
            lat_here = (time_here - self.prev_time_here)/1000000
            payload = data[self.header_len:]
            debug(f"d there here: {td1}, d there should {td2}, d here should {td3}, latency {self.latency}, latency {lat_here} payload {len(payload)}")
            for i in range(num_ports):
                start = payload_per_port_size * i
                end   = payload_per_port_size * (i + 1)
                #self.client.outports[i].get_buffer()[:payload_per_port_size] = payload[start:end]
                self.client.outports[i].get_buffer()[:payload_per_port_size] = payload[start:end]
            #@hexdump.hexdump(payload)
            self.prev_time_here = time_here
                

    def process(self):
        snd_rcv_time_diff = 0
        last_diffs = []
        debug(self)
        debug("process thread")
        prev_time_should = 0
        prev_counter = 0
        prev_time_here = 0
        debug("starting processing")
        while True:
            if prev_counter == 0:
                debug("initializiing ...")
                self.start_time = time.time_ns()
                self.latency = 1000*self.client.blocksize/self.client.samplerate
                while not self.queue.empty():
                    self.queue.get()
            qsize = self.queue.qsize()
            if qsize == 0:
                time.sleep(self.latency/1000)
            data = self.queue.get(block=True)
            time_here = time.time_ns()
            header = data[:self.header_len]
            (time_should, time_there, counter, payload_per_port_size, num_ports) = struct.unpack('qqqii', header)

            if counter != prev_counter +1:
                debug("counter error", counter, prev_counter)
            if time_should < prev_time_should:
                debug("time error")
     
            #print((time_here - prev_time_here) / 10000000)
            diff = time_here - time_should
            last_diffs.append(diff)
            if len(last_diffs) > 10000:
                last_diffs.pop(0)
            snd_rcv_time_diff_ms = sum(last_diffs)/len(last_diffs)/1000000

            diff_ms = diff/(1000000)
            delta_should_ms = (time_should - prev_time_should) / 1000000
            target_diff_ms = snd_rcv_time_diff_ms
            #time.sleep((target_diff - diff)/(1000 * 1000 * 1000))
            #if diff_ms > 3:
            #    print(diff_ms)
            diff_diff_ms = target_diff_ms - diff_ms
            if diff_diff_ms > 0:
                td1 = (time_there - time_here)/ 1000000
                td2 = (time_there - time_should)/ 1000000
                td3 = (time_here - time_should)/ 1000000
                lat_here = (prev_time_here - time_here)/1000000
                #print(f"sleep: {diff_diff_ms}, delta_should {delta_should_ms}, diff {diff_ms}, diff_avg {snd_rcv_time_diff}, qsize {qsize}, latency {self.latency} {counter} {prev_counter}")
                debug(f"sleep: {diff_diff_ms}, diff {diff_ms}ms, diff_avg {snd_rcv_time_diff_ms}, qsize {qsize}, d there here: {td1}, d there should {td2}, d here should {td3}, latency {self.latency}, {lat_here}")
                time.sleep((diff_diff_ms)/1000)
            else:
                debug(f"no sleep: {diff_diff_ms}, diff {diff_ms}ms, diff_avg {snd_rcv_time_diff_ms}, qsize {qsize}")
            payload = data[self.header_len:]
            if(payload_per_port_size) != int(len(payload)/num_ports):
                debug("payload problem!!!")
            len_out_buffer = len(self.client.outports[0].get_buffer())
            for i in range(num_ports):
                start = payload_per_port_size * i
                end   = payload_per_port_size * (i + 1)
                self.client.outports[i].get_buffer()[:payload_per_port_size] = payload[start:end]

            #print((time_here - prev_time_here)/1000000)
            prev_time_here = time_here
            prev_time_should = time_should
            prev_counter = counter



    def run(self):
        self.queue = queue.Queue()
        #threading.Thread(target=self.process).start()

        event = threading.Event()
        with self.client:
            while True:
                data, address = self.sock.recvfrom(10024)
                self.queue.put(data)


class JackCastAudioSender:
    def __init__(self, multicast_group=DEFAULT_MULTICAST_ADDRESS, destination=None, port=DEFAULT_PORT_FOR_AUDIO):
        self.multicast_group_pair = (multicast_group, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.2)
        ttl = struct.pack('b', 1)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        self.client = jack.Client("jackcast-snd")
        self.counter = 0
        self.last_sent_time = 0
        self.latency = 0
        self.times = []

        @self.client.set_process_callback
        def process(frames):
            if self.counter == 0:
                self.start_time = time.time_ns()
                self.latency = 1000 * self.client.blocksize / self.client.samplerate
            sent_time = time.time_ns()
            should_time = int(self.counter * self.latency * 1000000 + self.start_time)
            assert frames == self.client.blocksize
            #print("process")
            num_ports = 2
            out_buf = bytes()
            bs = self.client.blocksize
            for i in range(2):
                buf = self.client.inports[i].get_buffer()[:bs*4]
                out_buf += buf
            out_buf = struct.pack(f"qqqii", should_time, sent_time, self.counter, bs*4, num_ports) + out_buf
            #print(f"jbs: {bs*4}, lb: {len(out_buf)}")
            sent = self.sock.sendto(out_buf, self.multicast_group_pair)
            delta_ms = (sent_time - self.last_sent_time)/1000000
            #print(delta_ms, self.latency, self.client.blocksize, self.client.samplerate)
            if delta_ms > self.latency * 1.5 :
                debug(f"poz latency issue, got: {delta_ms}, expected: {self.latency}")
            if delta_ms <  self.latency * 0.5 :
                debug(f"neg latency issue, got: {delta_ms}, expected: {self.latency}")
            #print(delta_ms, (should_time - sent_time) / 1000000)
            self.last_sent_time = sent_time
            self.counter += 1

    def run(self):

        if self.client.status.server_started:
            debug("JACK server started")
        if self.client.status.name_not_unique:
            debug("unique name {0!r} assigned".format(self.client.name))

        event = threading.Event()
        self.client.inports.register("input_1")
        self.client.inports.register("input_2")
        with self.client:
            self.client.blocksize = 512
            debug(f"sr: {self.client.samplerate}, bs: {self.client.blocksize}")
            try:
                event.wait()
            except KeyboardInterrupt:
                debug("\nInterrupted by user")



