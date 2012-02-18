#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyNSource
Version 1.4c
(c) Andy Bulka 2004-2006
abulka@netspace.net.au
http://www.atug.com/andypatterns/pynsource.htm

A python source code scanner that generates
 - UML pictures (as text)
 - Java code (which can be imported into UML modelling tools.)
 - UML diagrams in wxpython (see associated module pynsourcegui.py)



"""

import tokenize, token
import pprint
import os

from pynsource import config
from pynsource.keywords import pythonbuiltinfunctions, javakeywords, delphikeywords



class HandleCtypesFields():
    def __init__(self):
        self.attrslist = []
        HandleCtypesFields._Clearwaiting(self)
        print self.onlyParseForCtypesFields

    def On_newline(self):
        ''' ignore newlines  if [ is open ...'''
        print 'ctypes on_newline' 
        if not self.parsingctypes:
          HandleCtypesFields._Clearwaiting(self)

    def _Clearwaiting(self):
        print 'ctypes CLEAR' 
        self.parsingctypes = False
        self.waitingforequal = False
        self.waitingforopen = False
        self.waitingforfield = False
        self.waitingforfieldname = False
        self.waitingforfieldtypedelim = False
        self.waitingforfieldtype = False
        self.waitingforfieldend = False
        self.waitingfornextfield = False
        self.onlyParseForCtypesFields = False
        self.ctype_indent_level = 0

    def On_meat(self):
        ''' = [ ( x, x ) , * ] '''
        #print 'ctypes on meat ' , self.token, self.nexttoken

        if self.waitingforequal and self.token == '=' : 
            self.waitingforopen = True
            self.waitingforequal = False
            #print 'equal done'

        elif self.waitingforopen and self.token == '[': 
            self.waitingforopen = False
            self.waitingforfield = True
            self.parsingctypes = True
            #print 'open done'

        elif self.waitingforfield and self.token == '(' :
            self.waitingforfield = False
            self.waitingforfieldname = True
            #print 'open field done'

        elif self.waitingforfield and self.token not in ['(',']','def','class'] :
            # munch munch and ignore # comments
            pass

        elif self.waitingforfield and self.token == ']': 
            HandleCtypesFields._Clearwaiting(self)
            print 'STOP1'

        elif self.waitingforfieldname : #and self.nexttoken == ',':
            self.waitingforfieldname = False
            self.attrname = self.token
            self.attrtype = []
            self.waitingforfieldtypedelim = True
            #print 'get field name done'

        elif self.waitingforfieldtypedelim and self.token == ',' :
            self.waitingforfieldtypedelim = False
            self.waitingforfieldtype = True
            #print 'get field type delim  done'

        elif self.waitingforfieldtype : # do not expect next arg in tuple , ctypes can be 2 or 3 sized tuple
            self.attrtype.append(self.token)
            if self.token == '(':
              self.ctype_indent_level += 1
            elif (self.nexttoken == ')' and self.ctype_indent_level > 0):
              self.ctype_indent_level -= 1              
            elif (self.nexttoken == ')' and self.ctype_indent_level ==0) or self.nexttoken == ',' or self.nexttoken == '\n' :
              # close field
              self.waitingforfieldtype = False
              self.attrtype = ''.join(self.attrtype)
              self._Add_Ctypes_Attribute(self.attrname, self.attrtype)
              self.waitingforfieldend = True

        elif self.waitingforfieldend and self.token == ')':
            self.waitingforfieldend = False
            self.waitingfornextfield = True

        elif self.waitingfornextfield:
            if self.token == ']':
              self.waitingfornextfield = False
              HandleCtypesFields._Clearwaiting(self)
              print 'STOP2'
            elif self.token == ',':
              self.waitingfornextfield = False
              self.waitingforfield = True
            elif self.token in ['def', 'class']: # stop running errors
              HandleCtypesFields._Clearwaiting(self)
              print 'STOP3'

            else:
              pass # ok
        else :     # stop running errors
          print 'BAD TOKEN ', self.token, self.nexttoken
          HandleCtypesFields._Clearwaiting(self)
          print 'STOP ERROR'
          
              

    def _Add_Ctypes_Attribute(self, attrname, attrtype):
        #print self.classlist
        classentry = self.classlist[self.currclass]
        attrtype = ['static', attrtype]

        classentry.AddAttribute(attrname, attrtype)
        #print '       CTYPES ATTR  ', attrname, attrtype




if __name__ == '__main__':
    pass

