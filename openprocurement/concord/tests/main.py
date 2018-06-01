# -*- coding: utf-8 -*-

import unittest

from openprocurement.concord.tests import conflicts, test_daemon


def suite():
    suite = unittest.TestSuite()
    suite.addTest(conflicts.suite())
    suite.addTest(test_daemon.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
