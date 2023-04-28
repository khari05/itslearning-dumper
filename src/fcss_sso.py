# a short script to produce a Session object that is authenticated
# into Forsyth County's ADFS and logged into itslearning
#
#  Copyright (c) 2023 Karthik Hari (github.com/khari05)
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import re
from urllib.parse import parse_qs
import requests

def getFCSSLoginInfo(itslLoginUrl: str, headers):
    # ! The  SSL certificate of Forsyth County's ADFS is issued for the wrong domain name so verify needs to be off.
    response = requests.get(
        itslLoginUrl,
        headers=headers,
        verify=False
    )

    if response.status_code != 200:
        raise Exception('ADFS response Code is not "200 OK"')

    matches = re.search(
        r'action="(https://.*/adfs/ls/)\?(SAMLRequest=.*)"', response.text, flags=re.MULTILINE)
    link = matches.group(1)
    params = parse_qs(matches.group(2))

    return link, params['SAMLRequest'][0], params['RelayState'][0], params['client-request-id'][0]


def adfsLogin(session: requests.Session, itslBaseUrl: str, username: str, password: str, autoLoginUrl: str):
    loginUrl, SAMLToken, stateToken, clientId = getFCSSLoginInfo(
        autoLoginUrl.format(itslBaseUrl),
        session.headers
    )

    # Sign into Forsyth County's SSO
    res = session.post(
        loginUrl,
        params={
            'SAMLRequest': SAMLToken,
            'RelayState': stateToken,
            'client-request-id': clientId
        },
        data={
            'UserName': username,
            'Password': password,
            'AuthMethod': 'FormsAuthentication'
        },
        verify=False,
    )

    # TODO: Use an account with 2FA to allow logging into accounts that require 2-factor auth

    if '<span id="errorText"' in str(res.content):
        error = re.search(
            r'<span id="errorText" for="" aria-live="assertive" role="alert">(.+?)</span>', str(res.content)).groups(1)[0]
        print('ADFS error:', error)
        raise ('ADFS error:', error)

    # Ask itslearning to automatically login
    res = session.get(
        autoLoginUrl.format(itslBaseUrl),
        allow_redirects=True,
        verify=False # ! redirects to ADFS then back to itsl to sign in
    )

    # Allow itslearning to send itself data
    while '<p>Script is disabled. Click Submit to continue.</p>' in str(res.content) or 'onload=\\\'document.forms["form"].submit()\\\'' in str(res.content):
        resText = res.content.decode('UTF-8').replace('\'', '"')
        matches = re.findall(
            r'type="hidden" name="(.+?)" value="(.+?)"', resText)
        formdata = {}
        for m in matches:
            formdata[m[0]] = m[1]
        endpoint = re.search(r'action="(.+?)"', resText).group(1)

        res = session.post(
            endpoint,
            data=formdata,
            allow_redirects=True,
            verify=True # WITHIN ITSL, set our session to verify certificates again
        )
