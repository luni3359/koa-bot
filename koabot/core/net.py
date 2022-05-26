"""Handle network requests"""
import io
from datetime import datetime

import aiohttp


class NetResponse():
    """Custom network response class"""

    def __init__(self, response: aiohttp.ClientResponse, **kwargs) -> None:
        self.client_response = response
        self.status: int = self.client_response.status
        self.response_body = kwargs.get('response_body', None)

        if kwargs.get('json'):
            self.json = self.response_body
        elif kwargs.get('image'):
            self.image = self.response_body
        else:
            self.plain_text = self.response_body


async def http_request(url: str, **kwargs) -> NetResponse:
    """Make an http request
    Arguments:
        url::str
            The url to point to

    Keywords:
        auth::aiohttp.BasicAuth
            Authentication object to make the connection with
        headers::json object
            object containing headers
        params::json dump str
            Stringified json object
        data::json dump str
            Stringified json object
        post::bool
            whether or not the request is a POST request
        jdata::dict
            a dict containing the json data to be sent
    """
    auth: aiohttp.BasicAuth = kwargs.get('auth')
    headers: dict = kwargs.get('headers')
    params: dict = kwargs.get('params', None)
    data: dict = kwargs.get('data', None)
    post: bool = kwargs.get('post', None)
    jdata: dict = kwargs.get('jdata', None)

    async with aiohttp.ClientSession(auth=auth) as session:
        if post:
            async with session.post(url, headers=headers, params=params, data=data, json=jdata) as response:
                return await handle_request(response, **kwargs)
        else:
            async with session.get(url, headers=headers, params=params, data=data, json=jdata) as response:
                return await handle_request(response, **kwargs)


async def handle_request(response: aiohttp.ClientResponse, **kwargs) -> NetResponse:
    """Handle the response made by either POST or GET requests
    Arguments:
        response::ClientResponse

    Keywords:
        json::bool
            True = must return json
            False/unset = returns plain text
        err_msg::str
            message to display on failure
    """
    json: bool = kwargs.get('json')
    err_msg: str = kwargs.get('err_msg')

    if response.status != 200:
        # Timeout error
        # if response.status == 524
        failure_msg = f"> {datetime.now()}\nFailed connecting to {response.real_url}\n"
        failure_msg += f"[Network status {response.status}]: {response.reason} \"{err_msg}\""
        print(failure_msg)
        return NetResponse(response)

    if json:
        response_body = await response.json(content_type=None)
    else:
        response_body = await response.read()

    return NetResponse(response, response_body=response_body, **kwargs)


async def fetch_image(url: str, /, **kwargs) -> io.BytesIO:
    """Download an image"""
    img_bytes = io.BytesIO((await http_request(url, image=True, **kwargs)).image)
    return img_bytes


def get_url_filename(url: str, /) -> str:
    """Get the file name from an url"""
    return url.split('/')[-1]


def get_url_fileext(url: str, /) -> str:
    """Get the file extension from an url"""
    return get_url_filename(url).split('.')[-1].split('?')[0]


def get_domain(url: str, /) -> str:
    """Get domain from an url"""
    return url.split('//')[-1].split('/')[0].split('?')[0]


def get_domains(urls: list[str], /) -> list[str]:
    """Get domains from a list of urls
    https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url#answer-36609868
    """
    return list(map(get_domain, urls))
