import urllib.parse
from typing import Optional

import requests


class EvidentlyOSSClient:
    """Client for Evidently OSS (Open Source) that works with or without authentication."""

    def __init__(self, url: str, token: Optional[str] = None):
        self._base_url = url
        self._token = token
        self._session = requests.Session()
        if token:
            self._session.headers.update({"evidently-secret": token})

    def request(
        self,
        path: str,
        method: str,
        headers: Optional[dict] = None,
        query_params: Optional[dict] = None,
        body: Optional[dict] = None,
    ) -> requests.Response:
        url = urllib.parse.urljoin(self._base_url, path)
        req_headers = dict(self._session.headers)
        if headers:
            req_headers.update(headers)
        req = requests.Request(method, url, params=query_params, headers=req_headers, json=body)
        resp = self.session().send(req.prepare())
        resp.raise_for_status()
        return resp

    def session(self) -> requests.Session:
        return self._session
