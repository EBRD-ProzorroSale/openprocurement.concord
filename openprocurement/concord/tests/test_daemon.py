import unittest
import mock
from datetime import datetime
from jsonpatch import make_patch
from openprocurement.concord.tests.data import test_tender_data
from openprocurement.concord.daemon import (
    get_now,
    get_revision_changes,
    update_journal_handler_params,
    conflicts_resolve,

    JournalHandler,
    LOGGER,
    TZ,
)


class DaemonTest(unittest.TestCase):
    def test_get_now(self):
        to_minute = lambda time: [
            time.year, time.month, time.day, time.hour, time.minute]
        self.assertEqual(to_minute(get_now()), to_minute(datetime.now(TZ)))

    def test_get_revision_changes(self):
        origin_data = {
            'id': 'test_id',
            'status': 'active'
        }
        revised_data = {
            'id': 'test_id',
            'status': 'cancelled'
        }

        patch = get_revision_changes(origin_data, revised_data)
        self.assertEqual(
           patch,
           [{u'path': u'/status', u'value': 'cancelled', u'op': u'replace'}]
        )
        patch = get_revision_changes(revised_data, origin_data)
        self.assertEqual(
            patch,
            [{u'path': u'/status', u'value': 'active', u'op': u'replace'}]
        )

    def test_update_journal_handler_params(self):
        if JournalHandler:
            LOGGER.handlers = [JournalHandler()]
            update_journal_handler_params({"spam": "spam"})
            handler = LOGGER.handlers[0]
            self.assertEqual(handler._extra["SPAM"], "spam")


    def test_revisions(self):
        db = mock.MagicMock()
        data = {
            "id": "tender_id",
            "doc": test_tender_data
        }
        data["doc"]["_rev"] = u'3-cbe27d63a1fc5ac5db4456df62a87ff4'
        data["doc"]["_id"] = "tender_id"
        data["doc"]["_conflicts"] = [u'3-7200a31509127c10410ea22dc8614783']

        for_rev = data["doc"].copy()
        for_rev["status"] = "draft"
        data["doc"]["revisions"] = [
            {
                'date': '1970-01-01',
                'rev': get_revision_changes(data["doc"], for_rev)
            }
        ]
        conflicts_resolve(db, data)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DaemonTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
