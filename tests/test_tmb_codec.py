import io
import os
import unittest
import zipfile
from tmb_codec import encode, decode

class CodecTests(unittest.TestCase):
    def setUp(self):
        self.seed=(b'\x01'+os.urandom(16)+(100000).to_bytes(4,'big'),os.urandom(32))
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('TvPlayer.db',b'SQLite format 3\x00'+b'curation'*100)
        self.payload=b.getvalue()
    def test_roundtrip_and_fresh_iv(self):
        a,b=encode(self.payload,self.seed),encode(self.payload,self.seed)
        self.assertEqual(decode(a,self.seed),self.payload)
        self.assertEqual(decode(b,self.seed),self.payload)
        self.assertNotEqual(a[21:37],b[21:37])
    def test_corrupted_payload_is_rejected(self):
        blob=bytearray(encode(self.payload,self.seed));blob[100]^=1
        with self.assertRaises(ValueError):decode(bytes(blob),self.seed)
    def test_different_salt_is_rejected(self):
        blob=bytearray(encode(self.payload,self.seed));blob[4]^=1
        with self.assertRaises(ValueError):decode(bytes(blob),self.seed)
    def test_wrong_key_is_rejected(self):
        blob=encode(self.payload,self.seed)
        with self.assertRaises(ValueError):decode(blob,(self.seed[0],os.urandom(32)))
    def test_arbitrary_plaintext_is_not_packaged(self):
        with self.assertRaises(ValueError):encode(b'not a backup',self.seed)

if __name__=='__main__':unittest.main()
