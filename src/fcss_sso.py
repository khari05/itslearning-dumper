# a short script to produce a Session object that is authenticated
# into Forsyth County's ADFS and logged into itslearning
# - Karthik Hari
import re
from urllib.parse import parse_qs
import requests


def getFCSSLoginInfo(itslLoginUrl: str, headers):
    # The  SSL certificate of Forsyth County's ADFS is issued for the wrong domain name so verify needs to be off.
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

    if '<span id="errorText"' in str(res.content):
        error = re.search(
            r'<span id="errorText" for="" aria-live="assertive" role="alert">(.+?)</span>', str(res.content)).groups(1)[0]
        print('ADFS error:', error)
        raise ('ADFS error:', error)

    # Ask itslearning to automatically login
    res = session.get(
        autoLoginUrl.format(itslBaseUrl),
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
