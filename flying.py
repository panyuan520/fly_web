#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import cgi
import traceback
try:
    import json
except:
    import simplejson as json
import threading
import functools
from xml.dom.minidom import parseString


'''
import sae.const
'database':{
          'db':sae.const.MYSQL_DB,
          'type':'mysql',
          'name':'name',
          'user':sae.const.MYSQL_USER,
          'passwd':sae.const.MYSQL_PASS,
          'host':sae.const.MYSQL_HOST,
          'port':int(sae.const.MYSQL_PORT),
          'charset':'utf8'
          },
'''
            
##config
config = {
            'app':'demo',
            'media':'public',
            'template':'templates',
            'template_module':'mako',
            'database':{
                      'db':'',
                      'type':'mysql',
                      'name':'name',
                      'user':'',
                      'passwd':'',
                      'host':'',
                      'port':'',
                      'charset':'utf8'
                      },
            'middleware':[],
            'storge':'threading',
            'charset':'utf-8',
            'base_path':os.path.abspath('.')
        }
        
                                  
##requst
class InputProcessed(object):
    def read(self, *args):
        raise EOFError('The wsgi.input stream has already been consumed')
    readline = readlines = __iter__ = read
    
class Requst(object):

    def __init__(self, environ):
        self.environ  = environ
        self.input    = environ['wsgi.input']
        self.method   = environ["REQUEST_METHOD"].upper()
        self.encoding = config['charset']
        
    def is_post_request(self):
        if self.method  != 'POST':
            return False
        content_type = self.environ.get("CONTENT_TYPE","application/x-www-form-urlencoded")
        return (content_type.startswith("application/x-www-form-urlencoded") or content_type.startswith("multipart/form-data"))
   
    def get_post_form(self):
        assert self.is_post_request()
        input = self.environ['wsgi.input']
        post_form = self.environ.get('wsgi.post_form')
        if (post_form is not None
            and post_form[0] is input):
            return post_form[2]
        self.environ.setdefault('QUERY_STRING', '')
        fs = cgi.FieldStorage(fp=input, environ=self.environ, keep_blank_values=1)
        new_input = InputProcessed()
        post_form = (new_input, input, fs)
        self.environ['wsgi.post_form'] = post_form
        self.environ['wsgi.input'] = new_input
        return fs
    
    def run(self):
        post, get, files, cookie = {}, {}, {}, {}
        if self.is_post_request():
            fs = self.get_post_form()
            for key in fs.keys():
                if key == 'file':
                    files.update({key:{"filename":fs[key].filename, "file": fs[key].file}})
                else:
                    post.update({key: fs[key].value})
            request.POST = post
            request.files = files
        querys = self.environ.get("QUERY_STRING").split("&") if self.environ.get("QUERY_STRING") else []
        for q in querys:
            if len(q)>0:
                b = q.split("=")
                get.update({b[0]:b[1]})
        request.GET = get
            
        cookies =  self.environ.get("HTTP_COOKIE").split("&") if self.environ.get("HTTP_COOKIE") else []
        for c in cookies:
            if len(c)>0:
                d = c.split("=")
                cookie.update({d[0]:d[1]})
        request.cookie = cookie
        request.path   = self.environ['PATH_INFO']
        request.method = self.method
        return request
  
##response
class Response(object):

    def __init__(self, start_response):
        self.request = request
        self.start_response = start_response
    
    def _header(self):
        header = [("Content-type","%s; charset=%s" % (request.content_type, config['charset']))]
        if hasattr(request, 'content_disposition'):
            header.append(("Content-disposition", "attachment;filename=" + request.content_disposition))
        return header
        
    def run(self):
        self.start_response(request.status, self._header())
        
_local = threading.local()

class Stack(dict):

    def __getattr__(self, key):
        if key in self: 
            return self[key]
    
    def __setattr__(self, key, value):
        if value != None: 
            self[key] = value
        
    def __delattr__(self, key):
        if key in self: 
            del self[key]
    
class Local_stack(object):

    def __init__(self, name):
        self._local = setattr(_local, name, Stack())
        
    def __getattr__(self, name):
        if hasattr(_local, name):
            return getattr(_local, name)
        
    def __setattr__(self, name, value):
        setattr(_local, name, value)
        
    def __delattr__(self, name):
        if hasattr(_local, name):
            delattr(_local, name)
      
request = Local_stack('request')


class Local_decorate(object):
    
    def __init__(self):
        self.name = 'Local_dcorate'
    
    def run(self, func):
        call = func.callback(*request.args) if len(request.args) > 0 else func.callback()
        if func.type == 'text/html':
            request.content_type = 'text/html'
        elif func.type == 'json':
            request.content_type = 'application/json'
            call = self._json(call)
        elif func.type == 'xml':
            request.content_type = 'text/xml'
            call = self._xml(call)
        self._befor_response()
        return call
        
    def _json(self, j):
        try:
            return json.dumps(j)
        except:
            traceback.print_exc()
        
    def _xml(self, x):
        try:
            parseString(x)
            return x
        except:
            traceback.print_exc()
    
    def _static(self):
        if request.path:
            file = os.path.abspath(os.path.join(os.path.abspath(config["base_path"]) + os.sep,request.path.strip("/\\")))
            if os.path.isfile(file):
                return open(file, 'rb')
            else:
                request.status = '404 Not Found'
        else:
            raise 'no request path, please check it request.path'
                 
    def _befor_response(self):
        Response(request.start_response).run()
          
decorate = Local_decorate()
    
##templete
class MakoTemplete(object):

    def __init__(self):
        from mako.template import Template
        from mako.lookup import TemplateLookup
        self.mylookup = TemplateLookup(directories=[config['template']], output_encoding=config['charset'],
                                          input_encoding=config['charset'], encoding_errors='replace', 
                                            default_filters=['decode.%s' % (config['charset'].replace('-', "_"))]
                          )
               
    def render_to_response(self, templatename, kwargs):
        mytemplate = self.mylookup.get_template(templatename)
        return mytemplate.render(**kwargs) if kwargs else mytemplate.render()

            
def render_to_response(templatename, kwargs = None):
    if config['template_module'] == 'mako':
        return MakoTemplete().render_to_response(templatename, kwargs)
   
##route
class Router(object):

    def __init__(self):
        self.routers = {}
        
    def _rule(self, path):
        for key, router in self.routers.iteritems():
            regex = re.search(router.path, path)
            if regex:
                request.args = regex.groups()
                request.status = '200 OK'
                return decorate.run(router)
            else:
                request.status = '404 Not Found'
             
    def push(self, path, callback, method, type):
        path = ''.join(['^', path.replace('<int>', '(\d+)').replace('<str>', '(\w+)').replace('<*>', '(\S)'), '$'])
        if not self.routers.get(path):
            _stack = Stack()
            _stack.path, _stack.callback, _stack.method, _stack.type = path, callback, method, type
            self.routers.update({path:_stack})
    
    def get(self):
        return self._rule(request.path)
        
    def all(self):
        return self.routers

router = Router()   
    
#######main###########
class Flying(object):

    def __init__(self):
        self.config = {}
        self.request = None
        self.response  = None
        
    def route(self, path, method = 'GET', type = 'text/html', callback=None, *args):
        if callable(path): path, callback = None, path
        def decorator(callback):
            router.push(path, callback, method, type)
            return callback
        return decorator(callback) if callback else decorator
        
    def run(self, *args, **kwargs):
        config = self.config = kwargs
        WSGIRefServer(*args, **kwargs).run()
        
    def wsgi(self, environ, start_response):
        Requst(environ).run()
        return router.get()
    
    def __call__(self, environ, start_response):
        request.environ = environ
        request.start_response = start_response
        return self.wsgi(environ, start_response)
        

def make_default_app_wrapper(name):
    @functools.wraps(getattr(Flying, name))
    def wrapper(*args, **kwargs):
        return getattr(Flying(), name)(*args, **kwargs)
    return wrapper

route  = make_default_app_wrapper('route')

@route('/public/*')
def public():
    return decorate._static()

##server
class WSGIRefServer(object):

    def __init__(self, host='127.0.0.1', port=8080, **option):
        self.option = option
        self.host = host
        self.port = int(port)

    def __repr__(self):
        args = ', '.join(['%s=%s'%(k,repr(v)) for k, v in self.option.items()])
        return "%s(%s)" % (self.__class__.__name__, args)
        
    def run(self, app): 
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        srv = make_server(self.host, self.port, app)
        srv.serve_forever()



