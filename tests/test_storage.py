import json
import os
import shutil
import tempfile
import unittest

import helpers  # noqa: F401  (adds src/ to the path)

from prestopet.storage import SavePolicy, Storage


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = Storage(os.path.join(self.dir, "save.json"))

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_nothing_saved(self):
        self.assertIsNone(self.store.load())
        self.assertFalse(self.store.exists())

    def test_save_and_load(self):
        self.assertTrue(self.store.save({"pet": {"a": 1}}))
        self.assertEqual(self.store.load(), {"pet": {"a": 1}})

    def test_previous_save_becomes_the_backup(self):
        self.store.save({"pet": {"n": 1}})
        self.store.save({"pet": {"n": 2}})
        with open(self.store.bak) as f:
            self.assertEqual(json.load(f), {"pet": {"n": 1}})

    def test_damaged_save_falls_back_on_the_backup(self):
        self.store.save({"pet": {"n": 1}})
        self.store.save({"pet": {"n": 2}})
        with open(self.store.path, "w") as f:
            f.write('{"pet": {"n"')
        self.assertEqual(self.store.load(), {"pet": {"n": 1}})

    def test_power_cut_between_the_renames(self):
        self.store.save({"pet": {"n": 1}})
        # The previous save was moved to the backup and the new one is still temporary.
        os.rename(self.store.path, self.store.bak)
        with open(self.store.tmp, "w") as f:
            json.dump({"pet": {"n": 2}}, f)
        self.assertEqual(self.store.load(), {"pet": {"n": 2}})

    def test_erase(self):
        self.store.save({"pet": {}})
        self.store.save({"pet": {}})
        self.store.erase()
        self.assertIsNone(self.store.load())
        self.assertEqual(os.listdir(self.dir), [])

    def test_unexpected_content_is_ignored(self):
        with open(self.store.path, "w") as f:
            f.write("[1, 2]")
        self.assertIsNone(self.store.load())


class SavePolicyTest(unittest.TestCase):
    def diff(self, a, b):
        return a - b

    def test_periodic(self):
        p = SavePolicy(0, self.diff, periodic_ms=600000)
        self.assertFalse(p.due(599999))
        self.assertTrue(p.due(600000))

    def test_actions_are_grouped(self):
        p = SavePolicy(0, self.diff, debounce_ms=15000)
        p.mark(1000)
        p.mark(5000)
        self.assertFalse(p.due(15999))
        self.assertTrue(p.due(16000))
        p.done(16000)
        self.assertFalse(p.due(20000))

    def test_urgent(self):
        p = SavePolicy(0, self.diff)
        p.mark(10, urgent=True)
        self.assertTrue(p.due(10))

    def test_writes_per_day_stay_low(self):
        p = SavePolicy(0, self.diff)
        writes = 0
        for t in range(0, 86400000, 1000):
            if t % 60000 == 0:      # a tap every minute, all day long
                p.mark(t)
            if p.due(t):
                p.done(t)
                writes += 1
        self.assertLessEqual(writes, 1440)
        q = SavePolicy(0, self.diff)
        idle = 0
        for t in range(0, 86400000, 1000):
            if q.due(t):
                q.done(t)
                idle += 1
        self.assertLessEqual(idle, 144)


if __name__ == "__main__":
    unittest.main()
