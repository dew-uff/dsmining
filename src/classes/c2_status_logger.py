from __future__ import print_function

import csv
import os
import time
import src.config.consts as consts


class StatusLogger(object):

    def __init__(self, script="unknown"):
        self.script = script
        self._count = 0
        self._skipped = 0
        self._total = 0
        self.time = time.time()
        consts.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.file = consts.LOGS_DIR / "status.csv"
        self.freq = consts.STATUS_FREQUENCY.get(script, 5)
        self.pid = os.getpid()

    @property
    def count(self):
        return self._count

    @count.setter
    def count(self, value):
        self._count = value
        self._total = self._skipped + self._count

    @property
    def skipped(self):
        return self._skipped

    @skipped.setter
    def skipped(self, value):
        self._skipped = value
        self._total = self._skipped + self._count

    @property
    def total(self):
        return self._total

    def report(self):
        if self.total % self.freq == 0:
            with open(str(self.file), "a") as csvfile:
                writer = csv.writer(csvfile)
                now = time.time()
                writer.writerow([
                    consts.MACHINE, self.script,
                    self.total, self.count, self.skipped,
                    self.time, now, now - self.time, self.pid
                ])
