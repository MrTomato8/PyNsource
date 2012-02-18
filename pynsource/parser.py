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
from pynsource import ctypesparse
from pynsource.keywords import pythonbuiltinfunctions, javakeywords, delphikeywords


class AndyBasicParseEngine(object):
    def __init__(self):
        self.meat = 0
        self.tokens = None
        self.isfreshline = 1
        self.indentlevel = 0

    def _ReadAllTokensFromFile(self, file):
        fp = open(file, 'r')
        try:
            self.tokens = [ x[0:2] for x in tokenize.generate_tokens(fp.readline) ]
        finally:
            fp.close()
        if config.DEBUG_DUMPTOKENS:
            pprint.pprint( self.tokens )

    def Parse(self, file):
        self._ReadAllTokensFromFile(file)
        self.meat = 0
        self._ParseLoop()

    def _ParseLoop(self):
        maxtokens = len(self.tokens)
        for i in range(0, maxtokens):

            tokentype, token = self.tokens[i]
            if tokentype == 5:
                self.indentlevel += 1
                continue
            elif tokentype == 6:
                self.indentlevel -= 1
                self.On_deindent()
                continue

            if tokentype == 0:  # End Marker.
                break

            assert token, ("Not expecting blank token, once have detected in & out dents. tokentype=%d, token=%s" %(tokentype, token))

            self.tokentype, self.token = tokentype, token
            if i+1 < maxtokens:
                self.nexttokentype, self.nexttoken = self.tokens[i+1]
            else:
                self.nexttokentype, self.nexttoken = (0,None)

            if self._Isblank():
                continue
            else:
                #print 'MEAT', self.token
                self._Gotmeat()

    def On_deindent(self):
        pass

    def On_newline(self):
        pass

    def On_meat(self):
        pass

    def _Gotmeat(self):
        self.meat = 1
        self.On_meat()
        self.isfreshline = 0  # must be here, at the end.

    def _Isblank(self):
        if self._Isnewline():
            return 1
        if self._Ispadding():
            return 1
        return 0

    def _Isnewline(self):
        if (self.token == '\n' or self.tokentype == token.N_TOKENS):
            if self.tokentype == token.N_TOKENS:
                assert '#' in self.token
            self.meat = 0
            self.isfreshline = 1
            self.On_newline()
            return 1
        else:
            return 0

    def _Ispadding(self):
        if not self.token.strip():
            self.meat = 0
            return 1
        else:
            return 0

class ClassEntry:
    def __init__(self):
        self.defs = []
        self.attrs = []
        self.classdependencytuples = []
        self.classesinheritsfrom = []
        self.ismodulenotrealclass = 0

    def FindAttribute(self, attrname):
        """
        Return
           boolean hit, index pos
        """
        for attrobj in self.attrs:
            if attrname == attrobj.attrname:
                return 1, attrobj
        return 0, None

    def AddAttribute(self, attrname, attrtype):
        """
        If the new info is different to the old, and there is more info
        in it, then replace the old entry.
        e.g. oldattrtype may be ['normal'
             and new may be     ['normal', 'many']
        """
        haveEncounteredAttrBefore, attrobj = self.FindAttribute(attrname)
        if not haveEncounteredAttrBefore:
            self.attrs.append(Attribute(attrname, attrtype))
        else:
            # See if there is more info to add re this attr.
            if len(attrobj.attrtype) < len(attrtype):
                attrobj.attrtype = attrtype   # Update it.

        # OLD CODE
        #if not self.FindAttribute(attrname):
        #    self.attrs.append(Attribute(attrname, attrtype))

class Attribute:
    def __init__(self, attrname, attrtype='normal'):
        self.attrname = attrname
        self.attrtype = attrtype

class HandleClasses(AndyBasicParseEngine):
    def __init__(self):
        AndyBasicParseEngine.__init__(self)
        self.currclasslist = []
        self._currclass = None
        self.nexttokenisclass = 0
        self.classlist = {}
        self.modulemethods = []
        self.optionModuleAsClass = 0
        self.inbetweenClassAndFirstDef = 0

    def On_deindent(self):
        if self.indentlevel <= self.currclassindentlevel:
##            print 'popping class', self.currclass, 'from', self.currclasslist
            self.PopCurrClass()
##        print
##        print 'deindent!!', self.indentlevel, 'class indentlevel =', self.currclassindentlevel

    def _DeriveNestedClassName(self, currclass):
        if not self.currclasslist:
            return currclass
        else:
            classname, indentlevel = self.currclasslist[-1]
            return classname + '_' + currclass   # Cannot use :: since java doesn't like this name, nor does the file system.

    def PushCurrClass(self, currclass):
        #print 'pushing currclass', currclass, 'self.currclasslist', self.currclasslist
        currclass = self._DeriveNestedClassName(currclass)
        self.currclasslist.append( (currclass, self.indentlevel) )
        #print 'result of pushing = ', self.currclasslist

    def PopCurrClass(self):
        #__import__("traceback").print_stack(limit=6)
        self.currclasslist.pop()

    def GetCurrClassIndentLevel(self):
        if not self.currclasslist:
            return None
        currclassandindentlevel = self.currclasslist[-1]
        return currclassandindentlevel[1]

    def GetCurrClass(self):
        if not self.currclasslist:
            return None
        currclassandindentlevel = self.currclasslist[-1]
        return currclassandindentlevel[0]
    currclass = property(GetCurrClass)

    currclassindentlevel = property(GetCurrClassIndentLevel)

    def _JustThenGotclass(self):
        self.PushCurrClass(self.token)
        self.nexttokenisclass = 0
        if self.currclass not in self.classlist:
            self.classlist[self.currclass] = ClassEntry()
        #print '*** class', self.currclass
        self.inbetweenClassAndFirstDef = 1
        

    def On_newline(self):
        pass

    def On_meat(self):
        if self.token == 'class':
##            print 'meat found class', self.token
            self.nexttokenisclass = 1
        elif self.nexttokenisclass:
##            print 'meat found class name ', self.token
            self._JustThenGotclass()

class HandleInheritedClasses(HandleClasses):
    def __init__(self):
        HandleClasses.__init__(self)
        self._ClearwaitingInheriteClasses()

    def _JustThenGotclass(self):
        HandleClasses._JustThenGotclass(self)
        self.currsuperclass = ''
        self.nexttokenisBracketOpenOrColon = 1

    def _ClearwaitingInheriteClasses(self):
        self.nexttokenisBracketOpenOrColon = 0
        self.nexttokenisSuperclass = 0
        self.nexttokenisComma = 0

    def On_newline(self):
        self._ClearwaitingInheriteClasses()

    def On_meat(self):
        HandleClasses.On_meat(self)
        if self.nexttokenisBracketOpenOrColon and self.token == '(':
            assert self.tokentype == token.OP  # unecessary, just practicing refering to tokens via names not numbers
            self.nexttokenisBracketOpen = 0
            self.nexttokenisSuperclass = 1

        elif self.nexttokenisBracketOpenOrColon and self.token == ':':
            self._ClearwaitingInheriteClasses()

        elif self.nexttokenisSuperclass and self.token == ')':
            self._ClearwaitingInheriteClasses()

        elif self.nexttokenisSuperclass:
            self.currsuperclass += self.token
            if self.token == '.' or self.nexttoken == '.':
                #print 'processing multi part superclass detected!', self.token, self.nexttoken
                self.nexttokenisSuperclass = 1
            else:
                self.nexttokenisSuperclass = 0
                self.nexttokenisComma = 1
                self.classlist[self.currclass].classesinheritsfrom.append(self.currsuperclass)

        elif self.nexttokenisComma and self.token == ',':
            self.nexttokenisSuperclass = 1
            self.nexttokenisComma = 0

class HandleDefs(HandleInheritedClasses):
    def __init__(self):
        HandleInheritedClasses.__init__(self)
        self.currdef = None
        self.nexttokenisdef = 0

    def _Gotdef(self):
        self.currdef = self.token
        self.nexttokenisdef = 0
        #print 'ADDING    def', self.currdef, 'to', self.currclass
##        if self.currclass and self.indentlevel == 1:
        if self.currclass:
            self.classlist[self.currclass].defs.append(self.currdef)
        elif self.optionModuleAsClass and self.indentlevel == 0:
            assert self.moduleasclass
            assert self.classlist[self.moduleasclass]
            self.classlist[self.moduleasclass].defs.append(self.currdef)
        else:
            self.modulemethods.append(self.currdef)
        self.inbetweenClassAndFirstDef = 0

    def On_meat(self):
        HandleInheritedClasses.On_meat(self)

##        if self.token == 'def' and self.indentlevel == 1:
        if self.token == 'def':
##            print 'DEF FOUND AT LEVEL', self.indentlevel
            self.nexttokenisdef = 1
        elif self.nexttokenisdef:
            self._Gotdef()
##        self.meat = 1

class HandleClassAttributes(HandleDefs):
    def __init__(self):
        HandleDefs.__init__(self)
        self.attrslist = []
        self._Clearwaiting()

    def On_newline(self):
        HandleInheritedClasses.On_newline(self)
        self._Clearwaiting()

    def _Clearwaiting(self):
        self.waitingfordot = 0
        self.waitingforsubsequentdot = 0
        self.waitingforvarname = 0
        self.waitingforequalsymbol = 0
        self.currvarname = None
        self.lastcurrvarname = None
        self.waitforappendopenbracket = 0
        self.nextvarnameisstatic = 0
        self.nextvarnameismany = 0

    def JustGotASelfAttr(self, selfattrname):
        pass

    def On_meat(self):
        HandleDefs.On_meat(self)

        if self.isfreshline and self.token == 'self' and self.nexttoken == '.':
            self.waitingfordot = 1

        elif self.waitingfordot and self.token == '.':
            self.waitingfordot = 0
            self.waitingforvarname = 1

        elif self.waitingforvarname:
            # We now have the possible class attribute name. :-)
            self.waitingforvarname = 0
            self.currvarname = self.token
            """
            At this point we have the x in the expression   self.x

            A. We could find   self.x =             in which case we have a valid class attribute.
            B. We could find   self.x.append(       in which case we have a valid class attribute list/vector.
            C. We could find   self.__class__.x =   in which case we have a valid STATIC class attribute.

            D. We could find   self.x.y =           in which case we skip.
            E. We could find   self.x.y.append(     in which case we skip.
            F. We could find   self.x.y.Blah(       in which case we skip.

            G. We could find   self.numberOfFlags = read16(fp)    - skip cos read16 is a module function.
            """
            if self.nexttoken == '=':
                self.waitingforequalsymbol = 1  # Case A
            elif self.nexttoken == '.':
                self.waitingforsubsequentdot = 1 # Cases B,C, D,E,F  pending

        elif self.waitingforsubsequentdot and self.token == '.':
            self.waitingfordot = 0
            self.waitingforsubsequentdot = 0
            self.waitingforequalsymbol = 0
            if self.nexttoken.lower() in ('append','add','insert'):  # Case B
                # keep the class attribute name we have, wait till bracket
                self.waitforappendopenbracket = 1
            elif self.currvarname in ('__class__',):  # Case C
                self.currvarname = None
                self.waitingforvarname = 1
                self.nextvarnameisstatic = 1
            else:
                # Skip cases D, E, F
                self._Clearwaiting()

        elif self.waitforappendopenbracket and self.token == '(':
            self.waitforappendopenbracket = 0
            self.nextvarnameismany = 1
            self._AddAttribute()
            self._Clearwaiting()

        elif self.waitingforequalsymbol and self.token == '=':
            self.waitingforequalsymbol = 0
            self._AddAttribute()
            self._Clearwaiting()

    def _AddAttribute(self):
        classentry = self.classlist[self.currclass]
        if self.nextvarnameisstatic:
            attrtype = ['static']
        else:
            attrtype = ['normal']

        if self.nextvarnameismany:
            attrtype.append('many')

        classentry.AddAttribute(self.currvarname, attrtype)
        #print '       ATTR  ', self.currvarname
        self.JustGotASelfAttr(self.currvarname)

class HandleComposites(HandleClassAttributes):
    def __init__(self):
        HandleClassAttributes.__init__(self)
        self._ClearwaitingOnComposites()
        self.dummy = ClassEntry()
        self.dummy2 = [()]

    def JustGotASelfAttr(self, selfattrname):
        assert selfattrname <> 'self'
        self.lastselfattrname = selfattrname
        self.waitingforclassname = 1
        self.waitingforOpenBracket = 0
        self.possibleclassname = None
        self.dontdoanythingnow = 1

    def _ClearwaitingOnComposites(self):
        self.lastselfattrname = None
        self.waitingforclassname = 0
        self.possibleclassname = None
        self.waitingforOpenBracket = 0
        self.dontdoanythingnow = 0

    def On_newline(self):
        HandleClassAttributes.On_newline(self)
        self._ClearwaitingOnComposites()

    def On_meat(self):
        self.dontdoanythingnow = 0
        HandleClassAttributes.On_meat(self)

        # At this point we may have had a "self.blah = " encountered, and blah is saved in self.lastselfattrname

        if self.dontdoanythingnow:
            pass

        elif self.waitingforclassname and self.token not in ( '(', '[' ) and \
          self.token not in pythonbuiltinfunctions and\
          self.tokentype not in (token.NUMBER, token.STRING) and\
          self.token not in self.modulemethods:
            self.possibleclassname = self.token
            self.waitingforclassname = 0
            self.waitingforOpenBracket = 1

        elif self.waitingforOpenBracket and self.token == '(':
            self.waitingforclassname = 0
            self.waitingforOpenBracket = 0

            dependency = (self.lastselfattrname, self.possibleclassname)
            self.classlist[self.currclass].classdependencytuples.append(dependency)
            #print '*** dependency - created instance of', self.possibleclassname, 'assigned to', self.lastselfattrname

        elif self.waitingforOpenBracket and self.token == ')':
            """
            New - we haven't got a class being created but instead have a variable.
            Note that the above code detects
              self.flag.append(Flag())   # notice instance creation inside append
            but the following code detects
              self.flag.append(flag)   # and assumes flag variable is an instance of Flag class
            """
            # we don't have class being created but have a variable name instead
            variablename = self.possibleclassname

            # try to find a class with the same name.
            correspondingClassName = variablename[0].upper() + variablename[1:] # HACK
            #print 'correspondingClassName', correspondingClassName

            dependency = (self.lastselfattrname, correspondingClassName)
            self.classlist[self.currclass].classdependencytuples.append(dependency)

        else:
            self._ClearwaitingOnComposites()


class HandleClassStaticAttrs(HandleComposites):
    def __init__(self):
        HandleComposites.__init__(self)
        self.__Clearwaiting()

    def __Clearwaiting(self):
        self.__waitingforequalsymbol = 0
        self.__staticattrname = ''

    def On_meat(self):
        HandleComposites.On_meat(self)

        if self.isfreshline and self.currclass and self.inbetweenClassAndFirstDef and self.tokentype == 1 and self.indentlevel != 0 and self.nexttoken == '=':
            self.__waitingforequalsymbol = 1
            self.__staticattrname = self.token

        elif self.__waitingforequalsymbol and self.token == '=':
            self.__waitingforequalsymbol = 0
            #print 'have static level attr', self.__staticattrname
            self.__AddAttrModuleLevel()
            self.__Clearwaiting()

        if self.__staticattrname == '_fields_':
            #print 'CTYPES _fields_, activating ctypes fields parsing.', self.token, self.nexttoken
            self.onlyParseForCtypesFields = True
            self.waitingforequal = True
            self.inbetweenClassAndFirstDef = False
            self.__Clearwaiting()


    def __AddAttrModuleLevel(self):
        # Should re-use the logic in HandleClassAttributes for both parsing
        # (getting more info on multiplicity but not static - cos static not relevant?) and
        # also should be able to resuse most of _AddAttr()
        #
        classentry = self.classlist[self.currclass]
        attrtype = ['static']

        classentry.AddAttribute(self.__staticattrname, attrtype)
        #print '       STATIC ATTR  ', self.__staticattrname
        # TODO change for ctypes-specific handling code
        # self.classentry.classesinheritsfrom
        #for parentclass in self.classentry.classesinheritsfrom



class HandleModuleLevelDefsAndAttrs(HandleClassStaticAttrs, ctypesparse.HandleCtypesFields):
    def __init__(self):
        HandleClassStaticAttrs.__init__(self)
        ctypesparse.HandleCtypesFields.__init__(self)
        self.moduleasclass = ''
        self.__Clearwaiting()

    def __Clearwaiting(self):
        self.waitingforequalsymbolformoduleattr = 0
        self.modulelevelattrname = ''

    def Parse(self, file):
        self.moduleasclass = 'Module_'+os.path.splitext(os.path.basename(file))[0]
        if self.optionModuleAsClass:
            self.classlist[self.moduleasclass] = ClassEntry()
            self.classlist[self.moduleasclass].ismodulenotrealclass = 1

        HandleComposites.Parse(self, file)

    def On_meat(self):

        if self.onlyParseForCtypesFields:
            ctypesparse.HandleCtypesFields.On_meat(self) # TODO       
            #print 'parser onlyParseForCtypesFields', self.onlyParseForCtypesFields
        else:
            HandleClassStaticAttrs.On_meat(self)
        
        if self.onlyParseForCtypesFields:
          return
          #pass
        
        elif self.isfreshline and self.tokentype == 1 and self.indentlevel == 0 and self.nexttoken == '=':
            self.waitingforequalsymbolformoduleattr = 1
            self.modulelevelattrname = self.token

        elif self.waitingforequalsymbolformoduleattr and self.token == '=':
            self.waitingforequalsymbolformoduleattr = 0
            #print 'have module level attr', self.modulelevelattrname
            self._AddAttrModuleLevel()
            self.__Clearwaiting()

    def On_newline(self):
        HandleClassStaticAttrs.On_newline(self)
        self.__Clearwaiting()

    def _AddAttrModuleLevel(self):
        if not self.optionModuleAsClass:
            return

        # Should re-use the logic in HandleClassAttributes for both parsing
        # (getting more info on multiplicity but not static - cos static not relevant?) and
        # also should be able to resuse most of _AddAttr()
        #
        classentry = self.classlist[self.moduleasclass]
        attrtype = ['normal']

##        if self.nextvarnameisstatic:
##            attrtype = ['static']
##        else:
##            attrtype = ['normal']
##
##        if self.nextvarnameismany:
##            attrtype.append('many')

        classentry.AddAttribute(self.modulelevelattrname, attrtype)
        #print '       ATTR  ', self.currvarname
        #self.JustGotASelfAttr(self.currvarname)





if __name__ == '__main__':
    pass

