"""Handle network requests"""
import io
from datetime import datetime

import aiohttp


async def http_request(url: str, **kwargs):
    """Make an http request
    Arguments:
        url::str
            The url to point to

    Keywords:
        auth::aiohttp.BasicAuth
            Authentication object to make the connection with
        data::json dump str
            Stringified json object
        headers::json object
            object containing headers
        json::bool
            true = must return json. false/unset = returns plain text
        err_msg::str
            message to display on failure
    """

    auth = kwargs.get('auth')
    data = kwargs.get('data')
    headers = kwargs.get('headers')
    json = kwargs.get('json')
    err_msg = kwargs.get('err_msg')

    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.get(url, data=data, headers=headers) as response:
            if response.status != 200:
                print('> %s\nFailed connecting to %s\n[Network status %i]: %s "%s"' % (datetime.now(), url, response.status, response.reason, err_msg))
                return False

            if json:
                return await response.json(content_type=None)

            return await response.read()


async def fetch_image(url: str, **kwargs):
    """Download an image"""

    img_bytes = io.BytesIO(await http_request(url, **kwargs))
    return img_bytes