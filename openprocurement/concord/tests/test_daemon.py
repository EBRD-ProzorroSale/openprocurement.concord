import unittest
import mock
import couchdb
from datetime import datetime
from jsonpatch import make_patch
from openprocurement.concord.tests.data import test_tender_data
from openprocurement.concord.daemon import (
    get_now,
    get_revision_changes,
    update_journal_handler_params,
    conflicts_resolve,
    _apply_revisions,

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


    def test_apply_revisions(self):
        db = mock.MagicMock()
        data = {
            "id": "test_id",
            "doc": test_tender_data
        }
        data["doc"]["_rev"] = u'3-cbe27d63a1fc5ac5db4456df62a87ff4'
        data["doc"]["_id"] = "test_id"
        data["doc"]["id"] = "test_id"
        data["doc"]["_conflicts"] = [u'3-7200a31509127c10410ea22dc8614783']

        for_rev = data["doc"].copy()
        for_rev["status"] = "draft"
        data["doc"]["revisions"] = [
            {
                'date': '1970-01-01',
                'changes': get_revision_changes(data["doc"], for_rev)
            },
            {
                'date': '1970-01-02',
                'changes': [{
                    'path': '/procurementMethodType',
                    'value': 'belowthreshold',
                    'op': 'add',
                }]
            }
        ]
        db.get = mock.MagicMock(return_value=data["doc"])

        ctender = data['doc']
        trev = ctender['_rev']
        another_rev = "3-7200a31509127c10410ea22dc8614783"
        self.assertFalse(_apply_revisions(data, None, 0,
            {trev: ctender, another_rev: ctender}))

    @mock.patch("openprocurement.concord.daemon._apply_revisions")
    @mock.patch("openprocurement.concord.daemon.LOGGER")
    def test_conflicts_resolve(self, LOGGER, _apply_revisions):
        db = mock.MagicMock()
        data = {
            "id": "test_id",
            "doc": test_tender_data
        }
        data["doc"]["_rev"] = u'3-cbe27d63a1fc5ac5db4456df62a87ff4'
        data["doc"]["_id"] = "test_id"
        data["doc"]["id"] = "test_id"
        data["doc"]["_conflicts"] = [u'3-7200a31509127c10410ea22dc8614783']

        for_rev = data["doc"].copy()
        for_rev["status"] = "draft"
        data["doc"]["revisions"] = [
            {
                'date': '1970-01-01',
                'changes': get_revision_changes(data["doc"], for_rev)
            },
            {
                'date': '1970-01-02',
                'changes': [{
                    'path': '/procurementMethodType',
                    'value': 'belowthreshold',
                    'op': 'add',
                }]
            }
        ]

        _apply_revisions.return_value = False
        conflicts_resolve(db, data)
        LOGGER.info.assert_called_once_with(
            'Conflict detected',
            extra={
                'rev': u'3-cbe27d63a1fc5ac5db4456df62a87ff4',
                'tenderid': 'test_id',
                'MESSAGE_ID':
                'conflict_detected'
            }
        )
        _apply_revisions.return_value = True
        db.get = mock.MagicMock(return_value=data["doc"])
        db.save = mock.MagicMock(
            side_effect=couchdb.ServerError())
        conflicts_resolve(db, data)
        LOGGER.error.assert_called_with(
            'ServerError on saving resolution',
            extra={
                'rev': u'3-cbe27d63a1fc5ac5db4456df62a87ff4',
                'tenderid': 'test_id',
                'MESSAGE_ID': 'conflict_error_save'
            }
        )
        db.save = mock.MagicMock(return_value=(None, None))
        db.update = mock.MagicMock(side_effect=couchdb.ServerError())
        conflicts_resolve(db, data)
        LOGGER.error.assert_called_with(
            'ServerError on deleting conflicts',
            extra={
                'rev': None,
                'tenderid': None,
                'MESSAGE_ID': 'conflict_error_deleting'
            }
        )
        db.update = mock.MagicMock(return_value=[])
        conflicts_resolve(db, data)
        LOGGER.info.assert_called_with(
            'Deleting conflicts',
            extra={
                'rev': None,
                'tenderid': None,
                'MESSAGE_ID': 'conflict_deleting'
            }
        )


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DaemonTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
