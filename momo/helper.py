# -*-coding: utf-8 -*-
from __future__ import unicode_literals

"""
File:   client.py
Author: goodspeed
Email:  cacique1103@gmail.com
Github: https://github.com/zongxiao
Date:   2015-02-11
Description: Weixin helpers
"""

import sys
import time
import logging
import datetime

try:
    import cPickle as pickle
except ImportError:
    import pickle
from functools import wraps
from hashlib import sha1
from decimal import Decimal

from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from chatterbot.response_selection import get_random_response

import six

from momo.settings import Config

PY2 = sys.version_info[0] == 2

_always_safe = (b'abcdefghijklmnopqrstuvwxyz'
                b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-+')


error_dict = {
    'AppID 参数错误': {
        'errcode': 40013,
        'errmsg': 'invalid appid'
    }
}


if PY2:
    text_type = unicode
    iteritems = lambda d, *args, **kwargs: d.iteritems(*args, **kwargs)

    def to_native(x, charset=sys.getdefaultencoding(), errors='strict'):
        if x is None or isinstance(x, str):
            return x
        return x.encode(charset, errors)
else:
    text_type = str
    iteritems = lambda d, *args, **kwargs: iter(d.items(*args, **kwargs))

    def to_native(x, charset=sys.getdefaultencoding(), errors='strict'):
        if x is None or isinstance(x, str):
            return x
        return x.decode(charset, errors)


"""
The md5 and sha modules are deprecated since Python 2.5, replaced by the
hashlib module containing both hash algorithms. Here, we provide a common
interface to the md5 and sha constructors, preferring the hashlib module when
available.
"""

try:
    import hashlib
    md5_constructor = hashlib.md5
    md5_hmac = md5_constructor
    sha_constructor = hashlib.sha1
    sha_hmac = sha_constructor
except ImportError:
    import md5
    md5_constructor = md5.new
    md5_hmac = md5
    import sha
    sha_constructor = sha.new
    sha_hmac = sha


momo_chat = ChatBot(
    'Momo',
    storage_adapter='chatterbot.storage.MongoDatabaseAdapter',
    # response_selection_method=get_random_response,
    logic_adapters=[
        "chatterbot.logic.BestMatch",
        "chatterbot.logic.MathematicalEvaluation",
        # "chatterbot.logic.TimeLogicAdapter",
    ],
    input_adapter='chatterbot.input.VariableInputTypeAdapter',
    output_adapter='chatterbot.output.OutputAdapter',
    database_uri=Config.MONGO_MASTER_URL,
    database='chatterbot',
    read_only=True
)


def get_momo_answer(content):
    try:
        response = momo_chat.get_response(content)
    except:
        return content
    if isinstance(response, str):
        return response
    return response.text


def set_momo_answer(conversation):
    momo_chat.set_trainer(ListTrainer)
    momo_chat.train(conversation)


log_format = '>' * 10 + "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s"
logging.basicConfig(format=log_format)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def timeit(fn):

    @wraps(fn)
    def real_fn(*args, **kwargs):
        _start = time.time()
        result = fn(*args, **kwargs)
        _end = time.time()
        _last = _end - _start
        logger.debug('End timeit for %s in %s seconds.' %
                     (fn.__name__, _last))
        return result

    return real_fn


try:
    from line_profiler import LineProfiler
except:
    class LineProfiler():
        def __call__(self, func):
           return func

        def print_stats(self):
            pass


ln_profile = LineProfiler()


def lprofile(fn):
    '''
    用line_profiler输出代码行时间统计信息
    '''
    fn = ln_profile(fn)

    @wraps(fn)
    def _fn(*args, **kwargs):
        result = fn(*args, **kwargs)
        print('>' * 10)
        ln_profile.print_stats()
        return result
    return _fn


class Promise(object):
    """
    This is just a base class for the proxy class created in
    the closure of the lazy function. It can be used to recognize
    promises in code.
    """
    pass


class _UnicodeDecodeError(UnicodeDecodeError):
    def __init__(self, obj, *args):
        self.obj = obj
        UnicodeDecodeError.__init__(self, *args)

    def __str__(self):
        original = UnicodeDecodeError.__str__(self)
        return '%s. You passed in %r (%s)' % (original, self.obj,
                                              type(self.obj))


def smart_text(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a text object representing 's' -- unicode on Python 2 and str on
    Python 3. Treats bytestrings using the 'encoding' codec.
    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if isinstance(s, Promise):
        # The input is the result of a gettext_lazy() call.
        return s
    return force_text(s, encoding, strings_only, errors)


_PROTECTED_TYPES = six.integer_types + (type(None), float, Decimal,
                                        datetime.datetime, datetime.date,
                                        datetime.time)


def is_protected_type(obj):
    """Determine if the object instance is of a protected type.
    Objects of protected types are preserved as-is when passed to
    force_text(strings_only=True).
    """
    return isinstance(obj, _PROTECTED_TYPES)


def force_text(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_text, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.
    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first for performance reasons.
    if issubclass(type(s), six.text_type):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        if not issubclass(type(s), six.string_types):
            if six.PY3:
                if isinstance(s, bytes):
                    s = six.text_type(s, encoding, errors)
                else:
                    s = six.text_type(s)
            elif hasattr(s, '__unicode__'):
                s = six.text_type(s)
            else:
                s = six.text_type(bytes(s), encoding, errors)
        else:
            # Note: We use .decode() here, instead of six.text_type(s, encoding,
            # errors), so that if s is a SafeBytes, it ends up being a
            # SafeText at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError as e:
        if not isinstance(s, Exception):
            raise _UnicodeDecodeError(s, *e.args)
        else:
            # If we get to here, the caller has passed in an Exception
            # subclass populated with non-ASCII bytestring data without a
            # working unicode method. Try to handle this without raising a
            # further exception by individually forcing the exception args
            # to unicode.
            s = ' '.join(force_text(arg, encoding, strings_only, errors)
                         for arg in s)
    return s


def smart_bytes(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.
    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if isinstance(s, Promise):
        # The input is the result of a gettext_lazy() call.
        return s
    return force_bytes(s, encoding, strings_only, errors)


def force_bytes(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_bytes, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.
    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first for performance reasons.
    if isinstance(s, bytes):
        if encoding == 'utf-8':
            return s
        else:
            return s.decode('utf-8', errors).encode(encoding, errors)
    if strings_only and is_protected_type(s):
        return s
    if isinstance(s, Promise):
        return six.text_type(s).encode(encoding, errors)
    if not isinstance(s, six.string_types):
        try:
            if six.PY3:
                return six.text_type(s).encode(encoding)
            else:
                return bytes(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return b' '.join(force_bytes(arg, encoding,
                                             strings_only, errors)
                                 for arg in s)
            return six.text_type(s).encode(encoding, errors)
    else:
        return s.encode(encoding, errors)

if six.PY3:
    smart_str = smart_text
    force_str = force_text
else:
    smart_str = smart_bytes
    force_str = force_bytes
    # backwards compatibility for Python 2
    smart_unicode = smart_text
    force_unicode = force_text

smart_str.__doc__ = """
Apply smart_text in Python 3 and smart_bytes in Python 2.
This is suitable for writing to sys.stdout (for instance).
"""

force_str.__doc__ = """
Apply force_text in Python 3 and force_bytes in Python 2.
"""


def genarate_js_signature(params):
    keys = params.keys()
    keys.sort()
    params_str = b''
    for key in keys:
        params_str += b'%s=%s&' % (smart_str(key), smart_str(params[key]))
    params_str = params_str[:-1]
    return sha1(params_str).hexdigest()


def genarate_signature(params):
    sorted_params = sorted([v for k, v in params.items()])
    params_str = ''.join(sorted_params)
    return sha1(params_str).hexdigest()


def get_encoding(html=None, headers=None):
    try:
        import chardet
        if html:
            encoding = chardet.detect(html).get('encoding')
            return encoding
    except ImportError:
        pass
    if headers:
        content_type = headers.get('content-type')
        try:
            encoding = content_type.split(' ')[1].split('=')[1]
            return encoding
        except IndexError:
            pass


def iter_multi_items(mapping):
    """
    Iterates over the items of a mapping yielding keys and values
    without dropping any from more complex structures.
    """
    if isinstance(mapping, dict):
        for key, value in iteritems(mapping):
            if isinstance(value, (tuple, list)):
                for value in value:
                    yield key, value
            else:
                yield key, value
    else:
        for item in mapping:
            yield item


def url_quote(string, charset='utf-8', errors='strict', safe='/:', unsafe=''):
    """
    URL encode a single string with a given encoding.

    :param s: the string to quote.
    :param charset: the charset to be used.
    :param safe: an optional sequence of safe characters.
    :param unsafe: an optional sequence of unsafe characters.

    .. versionadded:: 0.9.2
    The `unsafe` parameter was added.
    """
    if not isinstance(string, (text_type, bytes, bytearray)):
        string = text_type(string)
    if isinstance(string, text_type):
        string = string.encode(charset, errors)
    if isinstance(safe, text_type):
        safe = safe.encode(charset, errors)
    if isinstance(unsafe, text_type):
        unsafe = unsafe.encode(charset, errors)
    safe = frozenset(bytearray(safe) + _always_safe) - frozenset(bytearray(unsafe))
    rv = bytearray()
    for char in bytearray(string):
        if char in safe:
            rv.append(char)
        else:
            rv.extend(('%%%02X' % char).encode('ascii'))
    return to_native(bytes(rv))


def url_quote_plus(string, charset='utf-8', errors='strict', safe=''):
    return url_quote(string, charset, errors, safe + ' ', '+').replace(' ', '+')


def _url_encode_impl(obj, charset, encode_keys, sort, key):
    iterable = iter_multi_items(obj)
    if sort:
        iterable = sorted(iterable, key=key)
    for key, value in iterable:
        if value is None:
            continue
        if not isinstance(key, bytes):
            key = text_type(key).encode(charset)
        if not isinstance(value, bytes):
            value = text_type(value).encode(charset)
        yield url_quote_plus(key) + '=' + url_quote_plus(value)


def url_encode(obj, charset='utf-8', encode_keys=False, sort=False, key=None,
               separator=b'&'):
    separator = to_native(separator, 'ascii')
    return separator.join(_url_encode_impl(obj, charset, encode_keys, sort, key))


def validate_xml(xml):
    """
    使用lxml.etree.parse 检测xml是否符合语法规范
    """
    from lxml import etree
    try:
        return etree.parse(xml)
    except etree.XMLSyntaxError:
        return False


def cache_for(duration):

    def deco(func):
        @wraps(func)
        def fn(*args, **kwargs):
            all_args = []
            all_args.append(args)
            key = pickle.dumps((all_args, kwargs))
            value, expire = func.__dict__.get(key, (None, None))
            now = int(time.time())
            if value is not None and expire > now:
                return value
            value = func(*args, **kwargs)
            func.__dict__[key] = (value, int(time.time()) + duration)
            return value
        return fn

    return deco


@cache_for(60 * 60)
def get_weixinmp_token(appid, app_secret, is_refresh=False):
    from weixin import WeixinMpAPI
    from weixin.oauth2 import (ConnectTimeoutError,
                               ConnectionError,
                               OAuth2AuthExchangeError)
    try:
        api = WeixinMpAPI(
            appid=appid, app_secret=app_secret,
            grant_type='client_credential')
        token = api.client_credential_for_access_token().get('access_token')
        return token, None
    except (OAuth2AuthExchangeError, ConnectTimeoutError,
            ConnectionError) as ex:
        return None, ex


@timeit
def get_weixinmp_media_id(access_token, filepath):
    import requests
    upload_url = 'https://api.weixin.qq.com/cgi-bin/media/upload'
    payload_img = {
        'access_token': access_token,
        'type': 'image'
    }
    data = {'media': open(filepath, 'rb')}
    req = requests.post(url=upload_url, params=payload_img, files=data)
    if req.status_code == 200:
        info = req.json()
        media_id = info.get('media_id', '')
        return media_id
    return ''
