#!/usr/bin/env python
# -*- coding: utf-8 -*-


import tokenize, token
import pprint
import os

from pynsource import parser
from pynsource.keywords import pythonbuiltinfunctions, javakeywords, delphikeywords


class PySourceAsText(parser.HandleModuleLevelDefsAndAttrs):
    def __init__(self):
        parser.HandleModuleLevelDefsAndAttrs.__init__(self)
        self.listcompositesatend = 0
        self.embedcompositeswithattributelist = 1
        self.result = ''
        self.aclass = None
        self.classentry = None
        self.staticmessage = ""
        self.manymessage = ""
        self.verbose = 0

    def GetCompositeClassesForAttr(self, classname, classentry):
        resultlist = []
        for dependencytuple in classentry.classdependencytuples:
            if dependencytuple[0] == classname:
                resultlist.append(dependencytuple[1])
        return resultlist

    def _GetCompositeCreatedClassesFor(self, classname):
        return self.GetCompositeClassesForAttr(classname, self.classentry)

    def _DumpAttribute(self, attrobj):
        compositescreated = self._GetCompositeCreatedClassesFor(attrobj.attrname)
        if compositescreated and self.embedcompositeswithattributelist:
            self.result +=  "%s %s <@>----> %s" % (attrobj.attrname, self.staticmessage, str(compositescreated))
        else:
            self.result +=  "%s %s" % (attrobj.attrname, self.staticmessage)
        self.result += self.manymessage
        self.result += '\n'

    def _DumpCompositeExtraFooter(self):
        if self.classentry.classdependencytuples and self.listcompositesatend:
            for dependencytuple in self.classentry.classdependencytuples:
                self.result +=  "%s <*>---> %s\n" % dependencytuple
            self.result +=  '-'*20   +'\n'

    def _DumpClassNameAndGeneralisations(self):
        self._Line()
        if self.classentry.ismodulenotrealclass:
            self.result +=  '%s  (file)\n' % (self.aclass,)
        else:
            self.result +=  '%s  --------|> %s\n' % (self.aclass, self.classentry.classesinheritsfrom)
        self._Line()

    def _DumpAttributes(self):
        for attrobj in self.classentry.attrs:
            self.staticmessage = ""
            self.manymessage = ""
            if 'static' in attrobj.attrtype:
                self.staticmessage = " static"
            if 'many' in attrobj.attrtype:
                self.manymessage = " 1..*"
            self._DumpAttribute(attrobj)

    def _DumpMethods(self):
        for adef in self.classentry.defs:
            self.result +=  adef +'\n'

    def _Line(self):
        self.result +=  '-'*20   +'\n'

    def _DumpClassHeader(self):
        self.result += '\n'

    def _DumpClassFooter(self):
        self.result += '\n'
        self.result += '\n'

    def _DumpModuleMethods(self):
        if self.modulemethods:
            self.result += '  ModuleMethods = %s\n' % `self.modulemethods`
##        self.result += '\n'

    def __str__(self):
        self.result = ''
        self._DumpClassHeader()
        self._DumpModuleMethods()

        optionAlphabetic = 0
        classnames = self.classlist.keys()
        if optionAlphabetic:
            classnames.sort()
        else:
            def cmpfunc(a,b):
                if a.find('Module_') <> -1:
                    return -1
                else:
                    if a < b:
                        return -1
                    elif a == b:
                        return 0
                    else:
                        return 1
            classnames.sort(cmpfunc)
        for self.aclass in classnames:
            self.classentry = self.classlist[self.aclass]


##        for self.aclass, self.classentry in self.classlist.items():
            self._DumpClassNameAndGeneralisations()
            self._DumpAttributes()
            self._Line()
            self._DumpMethods()
            self._Line()
            self._DumpCompositeExtraFooter()
            self._DumpClassFooter()
        return self.result


class PySourceAsJava(PySourceAsText):
    def __init__(self, outdir=None):
        PySourceAsText.__init__(self)
        self.outdir = outdir
        self.fp = None

    def _DumpClassFooter(self):
        self.result +=  "}\n"

        if self.fp:
            self.fp.write(self.result)
            self.fp.close()
            self.fp = None
            self.result = ''

    def _DumpModuleMethods(self):
        self.result += '/*\n'
        PySourceAsText._DumpModuleMethods(self)
        self.result += '*/\n'

    def _OpenNextFile(self):
        filepath = "%s\\%s.java" % (self.outdir, self.aclass)
        self.fp = open(filepath, 'w')


    def _NiceNameToPreventCompilerErrors(self, attrname):
        """
        Prevent compiler errors on the java side by checking and modifying attribute name
        """
        # only emit the rhs of a multi part name e.g. undo.UndoItem will appear only as UndoItem
        if attrname.find('.') <> -1:
            attrname = attrname.split('.')[-1] # take the last
        # Prevent compiler errors on the java side by avoiding the generating of java keywords as attribute names
        if attrname in javakeywords:
            attrname = '_' + attrname
        return attrname

    def _DumpAttribute(self, attrobj):
        compositescreated = self._GetCompositeCreatedClassesFor(attrobj.attrname)
        if compositescreated:
            compositecreated = compositescreated[0]
        else:
            compositecreated = None

        # Extra processing on the attribute name, to avoid java compiler errors
        attrname = self._NiceNameToPreventCompilerErrors(attrobj.attrname)

        if compositecreated and self.embedcompositeswithattributelist:
            self.result +=  "    public %s %s %s = new %s();\n" % (self.staticmessage, compositecreated, attrname, compositecreated)
        else:
##            self.result +=  "    public %s void %s;\n" % (self.staticmessage, attrobj.attrname)
##            self.result +=  "    public %s int %s;\n" % (self.staticmessage, attrname)
            self.result +=  "    public %s variant %s;\n" % (self.staticmessage, attrname)

        """
        import java.util.Vector;

        private java.util.Vector lnkClass4;

        private Vector lnkClass4;
        """

    def _DumpCompositeExtraFooter(self):
        pass

    def _DumpClassNameAndGeneralisations(self):
        if self.verbose:
            print '  Generating Java class', self.aclass
        self._OpenNextFile()

        self.result += "// Generated by PyNSource http://www.atug.com/andypatterns/pynsource.htm \n\n"

##        self.result +=  "import javax.swing.Icon;     // Not needed, just testing pyNSource's ability to generate import statements.\n\n"    # NEW package support!

        self.result +=  'public class %s ' % self.aclass
        if self.classentry.classesinheritsfrom:
            self.result +=  'extends %s ' % self._NiceNameToPreventCompilerErrors(self.classentry.classesinheritsfrom[0])
        self.result +=  '{\n'

    def _DumpMethods(self):
        for adef in self.classentry.defs:
            self.result +=  "    public void %s() {\n    }\n" % adef

    def _Line(self):
        pass

def unique(s):
    """ Return a list of the elements in list s in arbitrary order, but without duplicates """
    # FIXME, is this list(set(x)) ?
    n = len(s)
    if n == 0:
         return []
    u = {}
    try:
         for x in s:
            u[x] = 1
    except TypeError:
         del u   # move onto the next record
    else:
          return u.keys()

    raise "uniqueness algorithm failed .. type more of it in please - see http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52560"

class PySourceAsDelphi(PySourceAsText):
    """
    Example Delphi source file:

      unit test000123;

      interface

      uses
        SysUtils, Windows, Messages, Classes, Graphics, Controls,
        Forms, Dialogs;

      type
        TDefault1 = class (TObject)
        private
          field0012: Variant;
        public
          class var field0123434: Variant;
          procedure Member1;
          class procedure Member2;
        end;


      procedure Register;

      implementation

      procedure Register;
      begin
      end;

      {
      ********************************** TDefault1 ***********************************
      }
      procedure TDefault1.Member1;
      begin
      end;

      class procedure TDefault1.Member2;
      begin
      end;


      end.

    """
    def __init__(self, outdir=None):
        PySourceAsText.__init__(self)
        self.outdir = outdir
        self.fp = None

    def _DumpClassFooter(self):
        self.result +=  "\n\n"

        self.result +=  "implementation\n\n"

        self.DumpImplementationMethods()

        self.result +=  "\nend.\n\n"

        if self.fp:
            self.fp.write(self.result)
            self.fp.close()
            self.fp = None
            self.result = ''

    def _DumpModuleMethods(self):
        self.result += '(*\n'
        PySourceAsText._DumpModuleMethods(self)
        self.result += '*)\n\n'

    def _OpenNextFile(self):
        filepath = "%s\\unit_%s.pas" % (self.outdir, self.aclass)
        self.fp = open(filepath, 'w')


    def _NiceNameToPreventCompilerErrors(self, attrname):
        """
        Prevent compiler errors on the java side by checking and modifying attribute name
        """
        # only emit the rhs of a multi part name e.g. undo.UndoItem will appear only as UndoItem
        if attrname.find('.') <> -1:
            attrname = attrname.split('.')[-1] # take the last

        # Prevent compiler errors on the Delphi side by avoiding the generating of delphi keywords as attribute names
        if attrname.lower() in delphikeywords:   # delphi is case insensitive, so convert everything to lowercase for comparisons
            attrname = '_' + attrname

        return attrname

    def _DumpAttribute(self, attrobj):
        """
        Figure out what type the attribute is only in those cases where
        we are later going to assign to these variables using .Create() in the constructor.
        The rest we make Variants.
        """
        compositescreated = self._GetCompositeCreatedClassesFor(attrobj.attrname)
        if compositescreated:
            compositecreated = compositescreated[0]
        else:
            compositecreated = None

        # Extra processing on the attribute name, to avoid delphi compiler errors
        attrname = self._NiceNameToPreventCompilerErrors(attrobj.attrname)

        self.result +=  "    "
        if self.staticmessage:
            self.result +=  "class var"

        if compositecreated:
            vartype = compositecreated
        else:
            vartype = 'Variant'
        self.result +=  "%s : %s;\n"%(attrname, vartype)

        # generate more complex stuff in the implementation section...
##        if compositecreated and self.embedcompositeswithattributelist:
##            self.result +=  "    public %s %s %s = new %s();\n" % (self.staticmessage, compositecreated, attrname, compositecreated)
##        else:
##            self.result +=  "%s : Variant;\n"%attrname

    def _DumpCompositeExtraFooter(self):
        pass

    def _DumpClassNameAndGeneralisations(self):
        if self.verbose:
            print '  Generating Delphi class', self.aclass
        self._OpenNextFile()

        self.result += "// Generated by PyNSource http://www.atug.com/andypatterns/pynsource.htm \n\n"

        self.result += "unit unit_%s;\n\n" % self.aclass
        self.result += "interface\n\n"

        uses = unique(self.GetUses())
        if uses:
            self.result += "uses\n    "
            self.result += ", ".join(uses)
            self.result += ";\n\n"

        self.result +=  'type\n\n'
        self.result +=  '%s = class' % self.aclass
        if self.classentry.classesinheritsfrom:
            self.result +=  '(%s)' % self._NiceNameToPreventCompilerErrors(self.classentry.classesinheritsfrom[0])
        self.result +=  '\n'
        self.result +=  'public\n'

    def _DumpMethods(self):
        if self.classentry.attrs:   # if there were any atributes...
            self.result +=  "\n"  # a little bit of a separator between attributes and methods.

        for adef in self.classentry.defs:
            if adef == '__init__':
                self.result +=  "    constructor Create;\n"
            else:
##                self.result +=  "    function %s(): void; virtual;\n" % adef
                self.result +=  "    procedure %s(); virtual;\n" % adef

        self.result +=  "end;\n"   # end of class

    def DumpImplementationMethods(self):
        for adef in self.classentry.defs:
            if adef == '__init__':
                self.result +=  "constructor %s.Create;\n" % self.aclass  # replace __init__ with the word 'Create'
            else:
##                self.result +=  "function %s.%s(): void;\n" % (self.aclass, adef)
                self.result +=  "procedure %s.%s();\n" % (self.aclass, adef)
            self.result +=  "begin\n"
            if adef == '__init__':
                self.CreateCompositeAttributeClassCreationAndAssignmentInImplementation()
            self.result +=  "end;\n\n"


    def CreateCompositeAttributeClassCreationAndAssignmentInImplementation(self):
        # Only do those attributes that are composite and need to create an instance of something
        for attrobj in self.classentry.attrs:
            compositescreated = self._GetCompositeCreatedClassesFor(attrobj.attrname)
            if compositescreated and self.embedcompositeswithattributelist: # latter variable always seems to be true! Never reset!?
                compositecreated = compositescreated[0]
                self.result +=  "    %s := %s.Create();\n" % (attrobj.attrname, compositecreated)

    def GetUses(self):
        result = []
        for attrobj in self.classentry.attrs:
            compositescreated = self._GetCompositeCreatedClassesFor(attrobj.attrname)
            if compositescreated and self.embedcompositeswithattributelist: # latter variable always seems to be true! Never reset!?
                compositecreated = compositescreated[0]
                result.append(compositecreated)

        # Also use any inherited calss modules.
        if self.classentry.classesinheritsfrom:
            result.append(self._NiceNameToPreventCompilerErrors(self.classentry.classesinheritsfrom[0]))

        return [ 'unit_'+u for u in result ]

    def _Line(self):
        pass


class PythonToJava:
    def __init__(self, directories, treatmoduleasclass=0, verbose=0):
        self.directories = directories
        self.optionModuleAsClass = treatmoduleasclass
        self.verbose = verbose

    def _GenerateAuxilliaryClasses(self):
        classestocreate = ('variant', 'unittest', 'list', 'object', 'dict')  # should add more classes and add them to a jar file to avoid namespace pollution.
        for aclass in classestocreate:
            fp = open(os.path.join(self.outpath, aclass+'.java'), 'w')
            fp.write(self.GenerateSourceFileForAuxClass(aclass))
            fp.close()

    def GenerateSourceFileForAuxClass(self, aclass):
       return '\npublic class %s {\n}\n'%aclass

    def ExportTo(self, outpath):
        self.outpath = outpath

        self._GenerateAuxilliaryClasses()

        for directory in self.directories:
            if '*' in directory or '.' in directory:
                filepath = directory
            else:
                filepath = os.path.join(directory, "*.py")
            if self.verbose:
                print 'Processing directory', filepath
            globbed = glob.glob(filepath)
            #print 'Java globbed is', globbed
            for f in globbed:
                self._Process(f)

    def _Process(self, filepath):
        if self.verbose:
            padding = ' '
        else:
            padding = ''
        thefile = os.path.basename(filepath)
        if thefile[0] == '_':
            print '  ', 'Skipped', thefile, 'cos begins with underscore.'
            return
        print '%sProcessing %s...'%(padding, thefile)
        p = self._CreateParser()
        p.Parse(filepath)
        str(p)  # triggers the output.

    def _CreateParser(self):
        p = PySourceAsJava(self.outpath)
        p.optionModuleAsClass = self.optionModuleAsClass
        p.verbose = self.verbose
        return p

class PythonToDelphi(PythonToJava):
    def _GenerateAuxilliaryJavaClasses(self):
        pass

    def _CreateParser(self):
        p = PySourceAsDelphi(self.outpath)
        p.optionModuleAsClass = self.optionModuleAsClass
        p.verbose = self.verbose
        return p

    def _GenerateAuxilliaryClasses(self):
        # Delphi version omits the class 'object' and 'variant' since these already are pre-defined in Delphi.
        classestocreate = ('unittest', 'list', 'dict')  # should add more classes
        for aclass in classestocreate:
            fp = open(os.path.join(self.outpath, 'unit_'+aclass+'.pas'), 'w')
            fp.write(self.GenerateSourceFileForAuxClass(aclass))
            fp.close()

    def GenerateSourceFileForAuxClass(self, aclass):
       template = """
unit unit_%s;

interface

type

    %s = class
    public
    end;

implementation

end.
       """
       return template%(aclass,aclass)



if __name__ == '__main__':
    pass

