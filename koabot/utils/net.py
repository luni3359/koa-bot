"""Handle network requests"""
import io
from datetime import datetime
from typing import List

import aiohttp


class NetResponse():
    """Custom network response class"""

    def __init__(self, response: aiohttp.ClientResponse, **kwargs):
        self.client_response = response
        self.status: int = self.client_response.status
        self.response_body = kwargs.get('response_body', None)

        if kwargs.get('json'):
            self.json = self.response_body
        elif kwargs.get('image'):
            self.image = self.response_body
        else:
            self.plain_text = self.response_body


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
        post::bool
            whether or not the request is a POST request
    """
    auth: aiohttp.BasicAuth = kwargs.get('auth')
    headers = kwargs.get('headers')
    data = kwargs.get('data')
    post: bool = kwargs.get('post')

    async with aiohttp.ClientSession(auth=auth) as session:
        if post:
            async with session.post(url, data=data, headers=headers) as response:
                return await handle_request(response, **kwargs)
        else:
            async with session.get(url, data=data, headers=headers) as response:
                return await handle_request(response, **kwargs)


async def handle_request(response: aiohttp.ClientResponse, **kwargs) -> NetResponse:
    """Handle the response made by either POST or GET requests
    Arguments:
        response::ClientResponse

    Keywords:
        json::bool
            true = must return json. false/unset = returns plain text
        err_msg::str
            message to display on failure
    """
    json: bool = kwargs.get('json')
    err_msg: str = kwargs.get('err_msg')

    if response.status != 200:
        # Timeout error
        # if response.status == 524
        print(
            f'> {datetime.now()}\nFailed connecting to {response.real_url}\n[Network status {response.status}]: {response.reason} "{err_msg}"')
        return NetResponse(response)

    if json:
        response_body = await response.json(content_type=None)
    else:
        response_body = await response.read()

    return NetResponse(response, response_body=response_body, **kwargs)


async def fetch_image(url: str, **kwargs) -> io.BytesIO:
    """Download an image"""

    img_bytes = io.BytesIO((await http_request(url, image=True, **kwargs)).image)
    return img_bytes


def get_url_filename(url: str) -> str:
    """Get the file name from an url"""
    return url.split('/')[-1]


def get_url_fileext(url: str) -> str:
    """Get the file extension from an url"""
    return get_url_filename(url).split('.')[-1].split('?')[0]


def get_domain(url: str) -> str:
    """Get domain from an url"""
    return url.split('//')[-1].split('/')[0].split('?')[0]


def get_domains(lst: List[str]) -> List[str]:
    """Get domains from a list of urls
    https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url#answer-36609868
    """
    domains = []

    for url in lst:
        domain = get_domain(url)
        domains.append(domain)
    return domains
