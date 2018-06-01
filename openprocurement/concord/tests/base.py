# -*- coding: utf-8 -*-
import os
import unittest
import couchdb
import yaml
from couchdb.design import ViewDefinition
from datetime import timedelta
from openprocurement.concord.tests.data import test_tender_data, now


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
        "tests.yaml"), 'r') as file:
    CONFIG = yaml.load(file)

conflicts_view = ViewDefinition('conflicts', 'all', '''function(doc) {
    if (doc._conflicts) {
        emit(doc._rev, [doc._rev].concat(doc._conflicts));
    }
}''')

def add_index_options(doc):
    doc['options'] = {'local_seq': True}

class BaseTenderWebTest(unittest.TestCase):
    def setUp(self):
        self.couch_server = couchdb.Server(CONFIG["couch_url"])
        self.db1 = self.couch_server.create(CONFIG["db_name_1"])
        ViewDefinition.sync_many(self.db1, [conflicts_view], callback=add_index_options)
        self.db2 = self.couch_server.create(CONFIG["db_name_2"])
        ViewDefinition.sync_many(self.db2, [conflicts_view], callback=add_index_options)
        
        self.initial_data = test_tender_data
        self.tender_id = self.initial_data["id"]
        self.initial_bids = None
        self.initial_status = None
        self.initial_lots = None
        
    def tearDown(self):
        del self.couch_server[self.db1.name]
        del self.couch_server[self.db2.name]
