from __future__ import print_function
from src.config.states import NB_STOPPED, NB_LOADED, REP_STOPPED, REP_LOADED

import src.consts as consts


class SafeSession(object):

    def __init__(self, session, interrupted=NB_STOPPED):
        self.session = session
        self.future = []
        self.interrupted = interrupted

    def add(self, element):
        self.session.add(element)

    def dependent_add(self, parent, children, on):
        parent.state = self.interrupted
        self.session.add(parent)
        self.future.append([
            parent, children, on
        ])

    def commit(self):
        try:
            self.session.commit()
            if self.future:
                for parent, children, on in self.future:
                    if parent.state == self.interrupted:
                        if self.interrupted is NB_STOPPED:
                            parent.state = NB_LOADED
                        elif self.interrupted is REP_STOPPED:
                            parent.state = REP_LOADED
                    self.session.add(parent)
                    for child in children:
                        setattr(child, on, parent.id)
                        self.session.add(child)
                self.session.commit()
            return True, ""
        except Exception as err:
            if consts.VERBOSE > 4:
                import traceback
                traceback.print_exc()
            return False, err
        finally:
            self.future = []

    def __getattr__(self, attr):
        return getattr(self.session, attr)
