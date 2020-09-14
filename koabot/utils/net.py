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
        post::bool
            whether or not the request is a POST request
    """

    auth = kwargs.get('auth')
    data = kwargs.get('data')
    headers = kwargs.get('headers')
    json = kwargs.get('json')
    err_msg = kwargs.get('err_msg')
    post = kwargs.get('post')

    async with aiohttp.ClientSession(auth=auth) as session:
        if post:
            async with session.post(url, data=data, headers=headers) as response:
                if response.status != 200:
                    print('> %s\nFailed connecting to %s\n[Network status %i]: %s "%s"' % (datetime.now(), url, response.status, response.reason, err_msg))
                    return False
                if json:
                    return await response.json(content_type=None)

                return await response.read()

        async with session.get(url, data=data, headers=headers) as response:
            if response.status != 200:
                # Timeout error
                # if response.status == 524
                print('> %s\nFailed connecting to %s\n[Network status %i]: %s "%s"' % (datetime.now(), url, response.status, response.reason, err_msg))
                return False
            if json:
                return await response.json(content_type=None)

            return await response.read()


async def fetch_image(url: str, **kwargs):
    """Download an image"""

    img_bytes = io.BytesIO(await http_request(url, **kwargs))
    return img_bytes


def get_url_filename(url: str):
    """Get the file name from an url"""
    return url.split('/')[-1]


def get_domain(url: str):
    """Get domain from an url"""
    return url.split('//')[-1].split('/')[0].split('?')[0]


def get_domains(lst: list):
    """Get domains from a list of urls
    https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url#answer-36609868
    """

    domains = []

    for url in lst:
        domain = get_domain(url)
        domains.append(domain)
    return domains
