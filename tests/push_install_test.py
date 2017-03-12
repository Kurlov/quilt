"""
Test push and install endpoints.
"""

import json
import urllib

import requests

from quilt_server import app
from quilt_server.core import (
    decode_node,
    encode_node,
    hash_contents,
    GroupNode,
    TableNode,
    FileNode,
)

from .utils import QuiltTestCase


class PushInstallTestCase(QuiltTestCase):
    """
    Test push and install endpoints.
    """

    HASH1 = 'd146942c9a051553f77d1e00672f2829565c590be972a1330de726a8db223589'
    HASH2 = '4cf37d7f670709346438cf2f2598db630eb34520947308aed55ad5e53f0c1518'
    HASH3 = '46449f44f36ec78364ae846fa47df57870e49d3c6cee59b3682aaf289e6d7586'

    CONTENTS = GroupNode(dict(
        foo=TableNode(
            hashes=[HASH1, HASH2]
        ),
        group1=GroupNode(dict(
            empty=TableNode(
                hashes=[]
            ),
            group2=GroupNode(dict(
                bar=TableNode(
                    hashes=[HASH1]
                )
            ))
        )),
        file=FileNode(
            hashes=[HASH3]
        )
    ))

    CONTENTS_WITH_METADATA = GroupNode(dict(
        foo=TableNode(
            hashes=[HASH1, HASH2],
            metadata=dict(
                important=True
            )
        ),
        group1=GroupNode(dict(
            empty=TableNode(
                hashes=[],
                metadata=dict(
                    whatever="123"
                )
            ),
            group2=GroupNode(dict(
                bar=TableNode([HASH1])
            ))
        )),
        file=FileNode(
            hashes=[HASH3],
            metadata=dict()
        )
    ))

    CONTENTS_HASH = 'cf8743510800aaf6f284568b19c3da5f2b7f3e517889c916f4e274bffeb7c035'

    def testContentsHash(self):
        assert hash_contents(self.CONTENTS) == self.CONTENTS_HASH
        assert hash_contents(self.CONTENTS_WITH_METADATA) == self.CONTENTS_HASH

    def testSuccessfulPushInstall(self):
        """
        Push a package, then install it.
        """
        # Push a package.
        resp = self.app.put(
            '/api/package/test_user/foo/%s' % self.CONTENTS_HASH,
            data=json.dumps(dict(
                description="",
                contents=self.CONTENTS
            ), default=encode_node),
            content_type='application/json',
            headers={
                'Authorization': 'test_user'
            }
        )

        assert resp.status_code == requests.codes.ok

        data = json.loads(resp.data.decode('utf8'))
        urls = data['upload_urls']
        assert len(urls) == 3

        url1 = urllib.parse.urlparse(urls[self.HASH1])
        url2 = urllib.parse.urlparse(urls[self.HASH2])
        url3 = urllib.parse.urlparse(urls[self.HASH3])
        assert url1.path == '/%s/test_user/foo/%s' % (app.config['PACKAGE_BUCKET_NAME'], self.HASH1)
        assert url2.path == '/%s/test_user/foo/%s' % (app.config['PACKAGE_BUCKET_NAME'], self.HASH2)
        assert url3.path == '/%s/test_user/foo/%s' % (app.config['PACKAGE_BUCKET_NAME'], self.HASH3)

        # List user's packages.
        resp = self.app.get(
            '/api/package/test_user/',
            headers={
                'Authorization': 'test_user'
            }
        )

        assert resp.status_code == requests.codes.ok

        data = json.loads(resp.data.decode('utf8'))
        assert data['packages'] == ['foo']

        # List package instances.
        resp = self.app.get(
            '/api/package/test_user/foo/',
            headers={
                'Authorization': 'test_user'
            }
        )

        assert resp.status_code == requests.codes.ok

        data = json.loads(resp.data.decode('utf8'))
        assert data['hashes'] == [self.CONTENTS_HASH]

        # Install the package.
        resp = self.app.get(
            '/api/package/test_user/foo/%s' % self.CONTENTS_HASH,
            headers={
                'Authorization': 'test_user'
            }
        )

        assert resp.status_code == requests.codes.ok

        data = json.loads(resp.data.decode('utf8'), object_hook=decode_node)
        contents = data['contents']
        assert contents == self.CONTENTS
        assert data['created_by'] == data['updated_by'] == 'test_user'
        assert data['created_at'] == data['updated_at']
        urls = data['urls']
        assert len(urls) == 3

        url1 = urllib.parse.urlparse(urls[self.HASH1])
        url2 = urllib.parse.urlparse(urls[self.HASH2])
        url3 = urllib.parse.urlparse(urls[self.HASH3])
        assert url1.path == '/%s/test_user/foo/%s' % (app.config['PACKAGE_BUCKET_NAME'], self.HASH1)
        assert url2.path == '/%s/test_user/foo/%s' % (app.config['PACKAGE_BUCKET_NAME'], self.HASH2)
        assert url3.path == '/%s/test_user/foo/%s' % (app.config['PACKAGE_BUCKET_NAME'], self.HASH3)

    def testPushNewMetadata(self):
        # Push the original contents.
        resp = self.app.put(
            '/api/package/test_user/foo/%s' % self.CONTENTS_HASH,
            data=json.dumps(dict(
                description="",
                contents=self.CONTENTS
            ), default=encode_node),
            content_type='application/json',
            headers={
                'Authorization': 'test_user'
            }
        )
        assert resp.status_code == requests.codes.ok

        # Push the metadata.
        resp = self.app.put(
            '/api/package/test_user/foo/%s' % self.CONTENTS_HASH,
            data=json.dumps(dict(
                description="",
                contents=self.CONTENTS_WITH_METADATA
            ), default=encode_node),
            content_type='application/json',
            headers={
                'Authorization': 'test_user'
            }
        )
        assert resp.status_code == requests.codes.ok

        # Verify that the metadata got saved.
        resp = self.app.get(
            '/api/package/test_user/foo/%s' % self.CONTENTS_HASH,
            headers={
                'Authorization': 'test_user'
            }
        )
        assert resp.status_code == requests.codes.ok

        data = json.loads(resp.data.decode('utf8'), object_hook=decode_node)
        assert data['contents'] == self.CONTENTS_WITH_METADATA

    def testNotLoggedIn(self):
        resp = self.app.put(
            '/api/package/test_user/foo/%s' % self.CONTENTS_HASH,
            data=json.dumps(dict(
                description="",
                contents=self.CONTENTS
            ), default=encode_node),
            content_type='application/json'
        )
        assert resp.status_code == requests.codes.unauthorized

        data = json.loads(resp.data.decode('utf8'))
        assert 'message' in data

        resp = self.app.get(
            '/api/package/test_user/foo/%s' % self.CONTENTS_HASH,
        )
        assert resp.status_code == requests.codes.not_found

        data = json.loads(resp.data.decode('utf8'))
        assert 'message' in data

    def testCreateWrongUser(self):
        resp = self.app.put(
            '/api/package/test_user/foo/%s' % self.CONTENTS_HASH,
            data=json.dumps(dict(
                description="",
                contents=self.CONTENTS
            ), default=encode_node),
            content_type='application/json',
            headers={
                'Authorization': 'blah'
            }
        )
        assert resp.status_code == requests.codes.forbidden

        data = json.loads(resp.data.decode('utf8'))
        assert 'message' in data

    def testInvalidRequest(self):
        resp = self.app.put(
            '/api/package/test_user/foo/%s' % self.CONTENTS_HASH,
            data='hello',
            headers={
                'Authorization': 'test_user'
            }
        )
        assert resp.status_code == requests.codes.bad_request

        data = json.loads(resp.data.decode('utf8'))
        assert 'message' in data

        resp = self.app.put(
            '/api/package/test_user/foo/%s' % self.CONTENTS_HASH,
            data=json.dumps(dict(
            )),
            content_type='application/json',
            headers={
                'Authorization': 'test_user'
            }
        )
        assert resp.status_code == requests.codes.bad_request

        data = json.loads(resp.data.decode('utf8'))
        assert 'message' in data

    def testInvalidHash(self):
        resp = self.app.put(
            '/api/package/test_user/foo/%s' % self.HASH1,
            data=json.dumps(dict(
                description="",
                contents=self.CONTENTS
            ), default=encode_node),
            content_type='application/json',
            headers={
                'Authorization': 'test_user'
            }
        )
        assert resp.status_code == requests.codes.bad_request

        data = json.loads(resp.data.decode('utf8'))
        assert 'message' in data

    def testCase(self):
        # Can't create a package if the username has the wrong case.
        resp = self.app.put(
            '/api/package/Test_User/foo/%s' % self.CONTENTS_HASH,
            data=json.dumps(dict(
                description="",
                contents=self.CONTENTS
            ), default=encode_node),
            content_type='application/json',
            headers={
                'Authorization': 'test_user'
            }
        )
        assert resp.status_code == requests.codes.forbidden

        # Successfully create a package.
        resp = self.app.put(
            '/api/package/test_user/foo/%s' % self.CONTENTS_HASH,
            data=json.dumps(dict(
                description="",
                contents=self.CONTENTS
            ), default=encode_node),
            content_type='application/json',
            headers={
                'Authorization': 'test_user'
            }
        )
        assert resp.status_code == requests.codes.ok

        # Can't update with the wrong username case.
        resp = self.app.put(
            '/api/package/Test_User/foo/%s' % self.CONTENTS_HASH,
            data=json.dumps(dict(
                description="",
                contents=self.CONTENTS
            ), default=encode_node),
            content_type='application/json',
            headers={
                'Authorization': 'test_user'
            }
        )
        assert resp.status_code == requests.codes.forbidden

        # Can't update with the wrong package name case.
        resp = self.app.put(
            '/api/package/test_user/Foo/%s' % self.CONTENTS_HASH,
            data=json.dumps(dict(
                description="",
                contents=self.CONTENTS
            ), default=encode_node),
            content_type='application/json',
            headers={
                'Authorization': 'test_user'
            }
        )
        assert resp.status_code == requests.codes.forbidden

        # Can't install with the wrong case.
        # TODO: Special error for this one.
        resp = self.app.get(
            '/api/package/test_user/Foo/%s' % self.CONTENTS_HASH,
            headers={
                'Authorization': 'test_user'
            }
        )
        assert resp.status_code == requests.codes.not_found
