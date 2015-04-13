#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flying import *

app = Flying()


@route('/')
def index():
    return render_to_response('hello.html',{'hello':'欢迎'})

@route('/json', type = 'json')
def json():
    return dict(a = 123)

    
@route('/xml', type = 'xml')
def xml():
    return "<myxml>Some data<empty/> some more data</myxml>"
    
@route('/a/<int>/<str>/a')
def test2(id, page):
    return "%s_%s" % (id, page)
    
      
if  __name__  ==  "__main__":
    mWSGIRefServer = WSGIRefServer()
    mWSGIRefServer.run(app)


