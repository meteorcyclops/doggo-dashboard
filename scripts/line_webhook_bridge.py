#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

UPSTREAM = 'http://127.0.0.1:18789/line/webhook'
HOST = '0.0.0.0'
PORT = 18889


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _proxy(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length) if length else b''
        headers = {k: v for k, v in self.headers.items() if k.lower() not in {'host', 'connection', 'content-length'}}
        req = Request(UPSTREAM, data=body if self.command in {'POST', 'PUT', 'PATCH'} else None, headers=headers, method=self.command)
        try:
            with urlopen(req, timeout=20) as resp:
                data = resp.read()
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() in {'transfer-encoding', 'connection', 'content-encoding'}:
                        continue
                    self.send_header(k, v)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                if data:
                    self.wfile.write(data)
        except HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() in {'transfer-encoding', 'connection', 'content-encoding'}:
                    continue
                self.send_header(k, v)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            if data:
                self.wfile.write(data)
        except URLError as e:
            msg = f'Bad Gateway: {e}'.encode()
            self.send_response(502)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def do_GET(self):
        self._proxy()

    def do_POST(self):
        self._proxy()

    def do_HEAD(self):
        self._proxy()

    def log_message(self, format, *args):
        return


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == '__main__':
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()
