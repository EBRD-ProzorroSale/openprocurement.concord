# -*- coding: utf-8 -*-
import unittest
import random
from openprocurement.concord.tests.data import test_organization
from openprocurement.concord.tests.base import BaseTenderWebTest
from openprocurement.concord.daemon import (
    conflicts_resolve as resolve,
    get_revision_changes,
    LOGGER
)


def conflicts_resolve(db):
    """ Branch apply algorithm """
    for c in db.view('conflicts/all', include_docs=True, conflicts=True):
        resolve(db, c)


class TenderConflictsTest(BaseTenderWebTest):

    def patch_tender(self, i, j, dbs):
        for i in range(i, j):
            a = dbs(i)
            c = random.choice(['USD', 'UAH', 'RUB'])
            tender = a.get(self.tender_id)
            tender['title'] = 'title changed #{}'.format(i)
            tender['description'] = 'description changed #{}'.format(i)
            tender['value'] = {
                'amount': i*1000 + 500,
                'currency': c
            }
            tender['minimalStep'] = {
                'currency': c
            }
            a.save(tender)

    def test_conflict_draft(self):
        if not self.tender_id in self.db1:    
            data = self.initial_data.copy()
            data['_id'] = data['id']
            data['status'] = 'draft'
            self.db1.save(data)
            
        tender1 = self.db1[self.tender_id].copy()
        self.assertEqual(tender1['status'], 'draft')
        self.couch_server.replicate(self.db1.name, self.db2.name)
        self.couch_server.replicate(self.db2.name, self.db1.name)
        
        tender1['status'] = 'active.enquiries'
        tender2 = self.db2[self.tender_id].copy()
        self.db1.save(tender1)
        self.db2.save(tender2)
        self.couch_server.replicate(self.db1.name, self.db2.name)
        self.couch_server.replicate(self.db2.name, self.db1.name)
        self.assertEqual(
            self.db1.get(self.tender_id)["_rev"],
            self.db2.get(self.tender_id)["_rev"]
        )
        self.assertGreater(len(self.db1.view('conflicts/all')), 0)
        
        tender1 = self.db1.get(self.tender_id, conflicts=True)
        self.assertEqual(len(tender1["_conflicts"]), 1)
        conflicts_resolve(self.db1)
        tender1 = self.db1.get(self.tender_id, conflicts=True)
        self.assertNotIn('_conflicts', tender1)
        self.assertEqual(len(self.db1.view('conflicts/all')), 0)

        self.couch_server.replicate(self.db1.name, self.db2.name)
        self.couch_server.replicate(self.db2.name, self.db1.name)
        self.assertEqual(len(self.db1.view('conflicts/all')), 0)

    def test_conflict_simple(self):
        if not self.tender_id in self.db1:
            data = self.initial_data
            data["_id"] = data["id"]
            self.db1.save(data)

        self.couch_server.replicate(self.db1.name, self.db2.name)
        self.couch_server.replicate(self.db2.name, self.db1.name)
        tender1 = self.db1.get(self.tender_id)
        tender2 = self.db2.get(self.tender_id)
        self.assertEqual(tender1, tender2)
        self.patch_tender(0, 10, lambda i: [self.db1, self.db2][i % 2])
        self.couch_server.replicate(self.db1.name, self.db2.name)
        self.couch_server.replicate(self.db2.name, self.db1.name)
        self.assertGreater(len(self.db1.view('conflicts/all')), 0)
        conflicts_resolve(self.db1)
        self.assertEqual(len(self.db1.view('conflicts/all')), 0)
        self.assertGreater(len(self.db2.view('conflicts/all')), 0)
        conflicts_resolve(self.db2)
        self.assertEqual(len(self.db2.view('conflicts/all')), 0)
        self.couch_server.replicate(self.db1.name, self.db2.name)
        self.couch_server.replicate(self.db2.name, self.db1.name)
        self.assertEqual(len(self.db1.view('conflicts/all')), 0)

    def test_conflict_complex(self):
        if not self.tender_id in self.db1:
            data = self.initial_data
            data["_id"] = data["id"]
            self.db1.save(data)

        self.couch_server.replicate(self.db1.name, self.db2.name)
        self.couch_server.replicate(self.db2.name, self.db1.name)
        self.patch_tender(0, 5, lambda i: [self.db1, self.db2][i % 2])
        self.couch_server.replicate(self.db1.name, self.db2.name)
        self.couch_server.replicate(self.db2.name, self.db1.name)
        self.assertGreater(len(self.db1.view('conflicts/all')), 0)
        conflicts_resolve(self.db1)
        self.assertEqual(len(self.db1.view('conflicts/all')), 0)
        self.assertGreater(len(self.db2.view('conflicts/all')), 0)
        self.patch_tender(5, 10, lambda i: [self.db1, self.db2][i % 2])
        self.couch_server.replicate(self.db1.name, self.db2.name)
        self.couch_server.replicate(self.db2.name, self.db1.name)
        self.assertGreater(len(self.db2.view('conflicts/all')), 0)
        conflicts_resolve(self.db2)
        self.assertEqual(len(self.db2.view('conflicts/all')), 0)
        self.couch_server.replicate(self.db1.name, self.db2.name)
        self.couch_server.replicate(self.db2.name, self.db1.name)
        self.assertEqual(len(self.db1.view('conflicts/all')), 0)

        self.patch_tender(10, 11, lambda i: self.db1)
        self.assertNotEqual(
            self.db1.get(self.tender_id)["_rev"],
            self.db2.get(self.tender_id)["_rev"]
        )
        self.couch_server.replicate(self.db1.name, self.db2.name)
        self.couch_server.replicate(self.db2.name, self.db1.name)
        self.assertEqual(len(self.db1.view('conflicts/all')), 0)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderConflictsTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
