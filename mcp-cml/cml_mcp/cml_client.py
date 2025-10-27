# Copyright (c) 2025  Cisco Systems, Inc.
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import logging
from typing import Any
import os
import httpx
import virl2_client
import ssl

API_TIMEOUT = 10  # seconds
ssl_context = ssl.create_default_context()

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class CMLClient(object):
    """
    Async client for interacting with the CML API.
    Handles authentication and provides methods to fetch system and lab information.
    """

    def __init__(self, host: str, username: str, password: str):
        self.base_url = host.rstrip("/")
        self.api_base = f"{self.base_url}/api/v0"
        self.client = httpx.AsyncClient(verify=ssl_context, timeout=API_TIMEOUT)
        self.vclient = virl2_client.ClientLibrary(host, username, password, ssl_verify=ssl_context)
        self.token = None
        self.admin = None
        self.username = username
        self.password = password

    async def login(self) -> None:
            url = f"{self.base_url}/api/v0/authenticate"
            resp = await self.client.post(
                url,
                json={"username": self.username, "password": self.password},
            )
            resp.raise_for_status()
            token = resp.json()
            if isinstance(token, dict):
                token = token.get("token") or next(iter(token.values()))
            self.token = token.strip('"')
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            logger.info("Authenticated with CML API")


    async def check_authentication(self) -> None:
        # If we don't have a token yet, do a clean login
        if not self.token:
            self.client.headers.pop("Authorization", None)
            await self.login()
            return

        url = f"{self.base_url}/api/v0/authok"
        try:
            resp = await self.client.get(url, headers={"Authorization": f"Bearer {self.token}"})
            resp.raise_for_status()
            return  # Token still valid
        except httpx.HTTPStatusError as e:
            # Treat 400 and 401 both as "bad token"
            if e.response.status_code in (400, 401):
                logger.debug("Token invalid or expired, forcing reauthentication...")
                self.token = None
                self.client.headers.pop("Authorization", None)
                await self.login()
            else:
                logger.error(f"Auth check failed with {e.response.status_code}: {e}", exc_info=True)
                raise
        except httpx.RequestError as e:
            logger.error(f"Auth check TLS/request error: {e}", exc_info=True)
            raise




    async def is_admin(self) -> bool:
        """
        Check if the current user is an admin.
        Returns True if the user is an admin, False otherwise.
        """
        if self.admin is not None:
            return self.admin

        await self.check_authentication()
        try:
            resp = await self.client.get(f"{self.base_url}/api/v0/users/{self.username}/id")
            resp.raise_for_status()
            user_id = resp.json()
            resp = await self.client.get(f"{self.base_url}/api/v0/users/{user_id}")
            resp.raise_for_status()
            self.admin = resp.json().get("admin", False)
            return self.admin
        except Exception as e:
            logger.error(f"Error checking admin status: {e}", exc_info=True)
            return False

    async def get(self, endpoint: str, params: dict | None = None) -> Any:
        """
        Make a GET request to the CML API.
        Ensures that calls to /nodes include ?operational=true for CML 2.8 compatibility.
        """
        await self.check_authentication()

        # In CML 2.8, you only get the "operational" block if you ask for it
        if endpoint.startswith("/nodes") or "/nodes" in endpoint:
            params = params or {}
            params.setdefault("operational", "true")

        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Error making GET request to {url}: {e}", exc_info=True)
            raise e


    async def post(self, endpoint: str, data: dict | None = None, params: dict | None = None) -> Any | None:
        """
        Make a POST request to the CML API.
        """
        await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.post(url, json=data, params=params)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Error making POST request to {url}: {e}", exc_info=True)
            raise e

    async def put(self, endpoint: str, data: dict | None = None) -> Any | None:
        """
        Make a PUT request to the CML API.
        """
        await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.put(url, json=data)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Error making PUT request to {url}: {e}", exc_info=True)
            raise e

    async def delete(self, endpoint: str) -> dict | None:
        """
        Make a DELETE request to the CML API.
        """
        await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.delete(url)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Error making DELETE request to {url}: {e}", exc_info=True)
            raise e

    async def patch(self, endpoint: str, data: dict | None = None) -> Any | None:
        """
        Make a PATCH request to the CML API.
        """
        await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.patch(url, json=data)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Error making PATCH request to {url}: {e}", exc_info=True)
            raise e

    async def close(self) -> None:
        await self.client.aclose()
