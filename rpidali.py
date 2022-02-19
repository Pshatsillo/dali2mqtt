import atexit
import logging
import os
import select
import struct
import threading

import dali.frame
import dali.gear.general as gear
from dali.command import Command
from dali.exceptions import CommunicationError

filename = "dali.txt"


class RpiDali:

    def __init__(self, callback=None):
        self.result = None
        self._callback = callback
        # fd = os.open(filename, os.O_RDWR)
        # self.f = open(fd, "wb+", buffering=0)

    def do_work(self):
        @atexit.register
        def goodbye():
            print("'CLEANLY' kill sub-thread with value: [THREAD: %s]" %
                  threading.currentThread().ident)

        self.result = self.f.readline()

    def after_timeout(self):
        raise SystemExit

    def send(self, command, timeout=None):
        # print("send")
        fd = os.open(filename, os.O_RDWR)
        self.f = open(fd, "wb+", buffering=0)
        assert isinstance(command, Command)
        message = struct.pack("B", 153) + command.frame.pack
        logging.info("command: {}{}".format(
            command, " (twice)" if command.sendtwice else ""))

        datas = str(message.hex())
        # try:
        #     self.f.write(bytes(datas, 'UTF-8'))
        # except Exception as err:
        #     logging.error(err)

        # try:
        #     pollerObject = select.poll()
        #     pollerObject.register(self.f, select.POLLIN)
        #     fdVsEvent = pollerObject.poll(100)
        #     for descriptor, Event in fdVsEvent:
        #         self.result = self.f.readline()
        # except Exception as err:
        #     print(err)

        self.result = self.f.readline()
        self.f.close()
        str_result = str(self.result)[2:8]
        try:
            result = bytes.fromhex(str_result)
        except Exception as err:
            result = b"\x99\x00\x00"
        response = self.unpack_response(command, result)
        if response:
            logging.info("  -> {0}".format(response))
        return response

    def unpack_response(self, command, result):
        """Unpack result from the given bytestream and creates the
        corresponding response object

        :param command: the command which waiting for it's response
        :param result: the result bytestream which came back
        :return: the result object
        """

        assert isinstance(command, Command)

        seq, addr, val = struct.unpack("BBB", result)
        response = None
        status = None
        if isinstance(command, gear.QueryControlGearPresent):
            status = val
        elif isinstance(command, gear.DAPC):
            status = 0
        else:
            status = 1

        if command.response:
            if status == 0:
                response = command.response(None)
            elif status == 1:
                response = command.response(dali.frame.BackwardFrame(val))
            elif status == 255:
                # This is "failure" - daliserver seems to be reporting
                # this for a garbled response when several ballasts
                # reply.  It should be interpreted as "Yes".
                response = command.response(dali.frame.BackwardFrameError(255))
            else:
                raise CommunicationError("status was %d" % status)
        else:
            print("No response")
        # if command.response:
        #     if status == 255:
        #         response = command.response(dali.frame.BackwardFrameError(255))
        #     else:
        #         response = command.response(dali.frame.BackwardFrame(status))

        return response
