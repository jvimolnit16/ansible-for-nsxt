#!/usr/bin/env python
#
# Copyright 2018 VMware, Inc.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json, os, re
from ansible.module_utils.urls import open_url, fetch_url
from ansible.module_utils.six.moves.urllib.error import HTTPError

def vmware_argument_spec():
    return dict(
        hostname=dict(type='str', required=True),
        username=dict(type='str', required=False),
        password=dict(type='str', required=False, no_log=True),
        port=dict(type='int', default=443),
        validate_certs=dict(type='bool', required=False, default=True),
    )

def request(url, data=None, headers=None, method='GET', use_proxy=True,
            force=False, last_mod_time=None, timeout=300, validate_certs=True,
            url_username=None, url_password=None, http_agent=None, force_basic_auth=True, ignore_errors=False):
    '''
    The main function which hits the request to the manager. Username and password are given the topmost priority.
    In case username and password are not provided if the environment variable is set.
    Authentication fails if the details are not correct.
    '''
    if url_username is None or url_password is None:
        force_basic_auth = False
        client_cert = get_certificate_file_path('NSX_MANAGER_CERT_PATH')
        if client_cert is None:
            raise Exception("It seems that either you have not passed your username password correctly or your path for NSX_MANAGER_CERT_PATH is not set correctly.")
    else:
        client_cert = None

    try:
        r = open_url(url=url, data=data, headers=headers, method=method, use_proxy=use_proxy,
                     force=force, last_mod_time=last_mod_time, timeout=timeout, validate_certs=validate_certs,
                     url_username=url_username, url_password=url_password, http_agent=http_agent,
                     client_cert=client_cert, force_basic_auth=force_basic_auth)
    except HTTPError as err:
        r = err.fp

    try:
        raw_data = r.read()
        if raw_data:
            data = json.loads(raw_data)
        else:
            raw_data = None
    except:
        if ignore_errors:
            pass
        else:
            raise Exception(raw_data)

    resp_code = r.getcode()

    if resp_code >= 400 and not ignore_errors:
        raise Exception(resp_code, data)
    if not (data is None) and data.__contains__('error_code'):
        raise Exception (data['error_code'], data)
    else:
        return resp_code, data

def get_certificate_string(crt_file):
    '''
    param: crt_file is the file containing the public key string
    result: returns the public key(client certificate) string to be passed to the payload
    how: String matching
    '''
    f = open(crt_file, 'r')
    file_content = f.read()
    file_content = file_content.split("\n")
    certificate_string = ""
    got_line_start = False
    for string in file_content:
        if string == "-----BEGIN CERTIFICATE-----":
            got_line_start = True
            certificate_string = certificate_string + string + "\n"
        elif string == "-----END CERTIFICATE-----":
            certificate_string = certificate_string + "\n" + string
            break
        elif got_line_start:
            certificate_string = certificate_string + string
        else:
            pass
    f.close()
    return certificate_string

def get_private_key_string(p12_file):
    '''
    param: p12_file is the file containing the private key string
    result: returns the private key string to be passed to the payload
    how: String matching
    '''
    f = open(p12_file, 'r')
    file_content = f.read()
    file_content = file_content.split("\n")
    certificate_string = ""
    got_start_line = False
    for string in file_content:
        if re.match("-+BEGIN[ \w]+PRIVATE[ ]+KEY-+", string):
            got_start_line = True
            certificate_string = certificate_string + string + "\n"
        elif re.match("-+END[ \w]+PRIVATE[ ]+KEY-+", string):
            certificate_string = certificate_string + "\n" + string
            break
        elif got_start_line:
            certificate_string = certificate_string + string
        else:
            pass
    f.close()
    return certificate_string

def get_certificate_file_path(environment_variable):
    return os.getenv(environment_variable)