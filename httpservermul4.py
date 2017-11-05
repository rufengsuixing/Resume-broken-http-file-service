from http.server import BaseHTTPRequestHandler
from http.server import SimpleHTTPRequestHandler
from http.server import HTTPServer
from socketserver import ThreadingMixIn
from shutil import copyfileobj
import os
import urllib
from http import HTTPStatus
hostIP = ''
portNum = 80

class ThreadingHttpServer( ThreadingMixIn, HTTPServer ):
    pass
    
class myhander(SimpleHTTPRequestHandler):
    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        fs = os.fstat(f.fileno())
        headers = dict(self.headers)
        if 'Range' in headers or 'range' in headers:
            self.send_response(206)
            start, end = self.parse_range_header(headers, fs[6])
            print(start,'\n',end)
            if start!=None and end!=None:
                f = open(path, 'rb')
                #if f: f = _file_iter_range(f, start, end-start)
                f.seek(start)
                try:
                    self.send_header("Content-Range","bytes %d-%d/%d" % (start, end-1,fs.st_size))
                    self.send_header("Content-Length", str(end-start))
                    self.send_header("Content-type", ctype)
                    self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
                    self.end_headers()
                    self.copyfile(f, self.wfile,end-start)
                finally:
                    f.close()
                return None
            else:
                self.send_error(416, "Requested Range Not Satisfiable")
                return None
        else:
            try:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-type", ctype)
                
                self.send_header("Content-Length", str(fs[6]))
                self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
                self.end_headers()
                return f
            except:
                f.close()
                raise
    def copyfile(self, source, outputfile,length=None):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        if length:
            while 1:
                if length<=16*1024:
                    buf = source.read(length)
                    outputfile.write(buf)
                    break
                buf = source.read(16*1024)
                outputfile.write(buf)
                length-=16*1024
        else:
            copyfileobj(source, outputfile)
    def parse_range_header(self,header, flen=0):
        ranges = header['Range']
        start, end = ranges.strip('bytes=').split('-')
        try:
            if not start:  # bytes=-100    -> last 100 bytes
                start, end = max(0, flen-int(end)), flen
            elif not end:  # bytes=100-    -> all but the first 99 bytes
               start, end = int(start), flen
            else:          # bytes=100-200 -> bytes 100-200 (inclusive)
                start, end = int(start), min(int(end)+1, flen)
            if 0 <= int(start) < int(end) <= int(flen):
                return start, end
        except ValueError:
            pass
        return None,None
    
Handler = myhander
myServer = ThreadingHttpServer( ( hostIP, portNum ), Handler )
myServer.serve_forever()
myServer.server_close()