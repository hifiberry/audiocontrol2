'''
Copyright (c) 2020 Modul 9/HiFiBerry

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import unittest

from ac2.simple_http import retrieve_url, post_data, is_cached, is_negative_cached, clear_cache

GOOGLE = "https://google.com"
NOT_EXISTING = "http://does-not-exist.nowhere.none"
BAD_CERT = "https://wrong.host.badssl.com"
POST = "https://webhook.site/d6c0f2b6-c361-4952-bab5-d95bba6a0fc3"

class Test(unittest.TestCase):


    def test_retrieve(self):
        res1 = retrieve_url(GOOGLE)
        self.assertIsNotNone(res1)
        self.assertTrue("html" in res1.text)
        res2 = retrieve_url(GOOGLE)
        self.assertEqual(res1, res2)
        res = retrieve_url(NOT_EXISTING)
        self.assertIsNone(res)
        
    def test_ssl(self):
        self.assertIsNotNone(retrieve_url(GOOGLE))
        self.assertIsNotNone(retrieve_url(BAD_CERT, verify=False))
        clear_cache()
        self.assertIsNone(retrieve_url(BAD_CERT))
        clear_cache()
        self.assertIsNone(retrieve_url(BAD_CERT, verify=True))
         
    def test_post(self):
        res = post_data(POST, {"test": "testdata"})
        self.assertIsNotNone(res)
        
    def test_cache(self):
        retrieve_url(GOOGLE)
        self.assertTrue(is_cached(GOOGLE))
        self.assertFalse(is_negative_cached(GOOGLE))
        retrieve_url(NOT_EXISTING)
        self.assertFalse(is_cached(NOT_EXISTING))
        self.assertTrue(is_negative_cached(NOT_EXISTING))
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()