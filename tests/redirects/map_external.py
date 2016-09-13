# -*- coding: utf-8 -*-

from __future__ import absolute_import

import requests

from .base import flatten, url_test

URLS = flatten((
    url_test('https://www.mozilla.com/', 'https://www.mozilla.org/firefox/'),
    url_test('https://aurora.mozilla.org/', 'https://www.mozilla.org/firefox/aurora/', status_code=requests.codes.found),
    # Bug 1299947 once new /channel pages are live we can update this redirect test.
    # url_test('https://beta.mozilla.org/', 'https://www.mozilla.org/en-US/firefox/channel/#beta'),
))
