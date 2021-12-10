# a short script to produce a Session object that is authenticated
# into Forsyth County's ADFS and logged into itslearning
# - Karthik Hari

import requests

import os
import re
from urllib.parse import parse_qs


HEADERS = {'User-Agent': 'Mozilla/5.0'}
ITSL_BASE_URL = 'https://forsyth.itslearning.com'

USERNAME = os.environ['USERNAME']
PASSWORD = os.environ['PASSWORD']

AUTOLOGIN_URL = '/elogin/autologin.aspx'

def getFCSSLoginInfo(itslBaseURL: str, headers):
    # Forsyth County's ADFS doesn't have a correct SSL certificate so verify has to be off
    response = requests.get(
        itslBaseURL + AUTOLOGIN_URL,
        headers=headers,
        verify=False
    )

    if response.status_code != 200:
        raise 'ADFS response Code is not "200 OK"'

    matches = re.search(
        r'action="(https://.*/adfs/ls/)\?(SAMLRequest=.*)"', response.text, flags=re.MULTILINE)
    link = matches.group(1)
    params = parse_qs(matches.group(2))

    return link, params['SAMLRequest'][0], params['RelayState'][0], params['client-request-id'][0]


def login(session: requests.Session, itslBaseUrl: str, username: str, password: str):
    loginUrl, SAMLToken, stateToken, clientId = getFCSSLoginInfo(
        itslBaseUrl,
        session.headers
    )

    # Sign into Forsyth County's SSO
    res = session.post(
        loginUrl,
        params={
            'SAMLRequest': SAMLToken,
            'RelayState': stateToken,
            'client-request-id': clientId,
        },
        data={
            'UserName': username,
            'Password': password,
            'AuthMethod': 'FormsAuthentication'
        },
        verify=False,
    )

    if '<span id="errorText"' in str(res.content):
        error = re.search(
            r'<span id="errorText" for="" aria-live="assertive" role="alert">(.+?)</span>', str(res.content)).groups(1)[0]
        print('ADFS error:', error)
        return

    # Ask itslearning to automatically login
    res = session.get(
        itslBaseUrl + AUTOLOGIN_URL,
        allow_redirects=True,
        verify=False
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

        # print(formdata)
        # print(f'posting to {endpoint}')

        res = session.post(
            endpoint,
            data=formdata,
            allow_redirects=True
        )

    # print(res.status_code, res.url)
    # f = open("./content", 'wb')
    # f.write(res.content)
    return

# --- Run Stuff ---

session = requests.Session()
session.headers.update(HEADERS)
login(
    session,
    itslBaseUrl=ITSL_BASE_URL,
    username=USERNAME,
    password=PASSWORD,
)
