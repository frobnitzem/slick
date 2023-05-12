from typing import Dict, Optional, List

from pydantic import BaseModel
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor
from parsimonious.exceptions import IncompleteParseError

"""
More formally, a spec consists of the following pieces:

Package name identifier (mpileaks above)

@ Optional version specifier (@1.2:1.4)

% Optional compiler specifier, with an optional compiler version (gcc or gcc@4.7.3)

+ or - or ~ Optional variant specifiers (+debug, -qt, or ~qt) for boolean variants. Use ++ or -- or ~~ to propagate variants through the dependencies (++debug, --qt, or ~~qt).

name=<value> Optional variant specifiers that are not restricted to boolean variants. Use name==<value> to propagate variant through the dependencies.

name=<value> Optional compiler flag specifiers.
-- not implemented --
Valid flag names are cflags, cxxflags, fflags, cppflags, ldflags, and ldlibs. Use name==<value> to propagate compiler flags through the dependencies.

# reserved keywords for arch specifiers:
target=<value> os=<value> Optional architecture specifier (target=haswell os=CNL10)
platform=linux
os=ubuntu18.04
target=broadwell
gpu_arch=nil
# combination
arch=cray-CNL10-haswell-nil
arch=cray-CNL10-haswell

^ Dependency specs (^callpath@1.1)
"""

class Version(BaseModel):
    major:   int = 0
    minor:   int = 0
    patch:   int = 0
    ext:     str = ""

class VariantValue(BaseModel):
    enable:  Optional[bool]      = None
    value:   Optional[str]       = None
    values:  Optional[List[str]] = None

class Compiler(BaseModel):
    name:    str
    version: Version
    variant: Dict[str,VariantValue] = {}

class ArchSpec(BaseModel):
    platform: str = "nil"
    os:       str = "nil"
    cpu:      str = "nil"
    gpu:      str = "nil"

class Spec(BaseModel):
    name:          str
    version:       Version
    compiler:      Compiler
    compilerflags: List[str] = []
    variant:       Dict[str,VariantValue] = {}
    deps:          Dict[str,"Spec"] = {}
    archspec:      ArchSpec

grammar = Grammar(
    r"""
    spec        = word ws specifier*
    specifier   = (reserved ws) / (variant ws)

    variant     = variantone / variantbool
    variantone  = word equal word
    variantbool = ~r"[+-~]" ws word

    osarch      = word "-" word "-" arch
    arch        = (word "-" word) / word
    word       = ~r"\w+"
    equal       = ws? "=" ws?

    reserved    = ("arch" equal osarch)
                / ("platform"  equal word)
                / ("os"        equal word)
                / ("target"    equal word)
                / ("gpu_arch"  equal word)
    ws          = ~"\s*"
    """
)

def update_variant(a : Spec, name : str, val : VariantValue): 
    if name in a.variant:
        raise KeyError("Repeated variant: {}".format(name))
    a.variant[name] = val

def update_arch(a : Spec, arch : ArchSpec):
    for key in ["platform", "os", "cpu", "gpu"]:
        if getattr(arch,key) == "nil": continue
        if getattr(a.archspec,key) != "nil":
            raise KeyError("Repeated archspec: {}".format(key))
        setattr(a.archspec,key, getattr(arch,key))

# TODO:
#   version:       Version
#   compiler:      Compiler
#   compilerflags: List[str]
#   deps:          Dict[str,"Spec"]

""" Mutating parser that builds up the result in self.spec.
"""
class SpecVisitor(NodeVisitor):
    def __init__(self):
        self.spec = Spec(name = "",
                 version = Version(),
                 compiler = Compiler(name="gcc",
                                     version=Version(major=7, minor=0)),
                 archspec = ArchSpec())
        super(NodeVisitor).__init__()

    def visit_spec(self, node, visited_children):
        self.spec.name = node.children[0].text
        return self.spec

    def visit_arch(self, node, visited_children):
        visited_children = visited_children[0]
        if len(visited_children) == 1:
            gpu = "nil"
        else:
            gpu = visited_children[2].text
        return {'cpu': visited_children[0].text,
                'gpu': gpu
               }

    def visit_osarch(self, node, visited_children):
        arch = ArchSpec(platform = visited_children[0].text,
                        os       = visited_children[2].text,
                        cpu      = visited_children[4]["cpu"],
                        gpu      = visited_children[4]["gpu"])
        update_arch(self.spec, arch)
        return arch

    def visit_variantone(self, node, visited_children):
        """ Gets each key/value pair, returns a tuple. """
        key, _, value = node.children
        update_variant(self.spec, key.text, VariantValue(value = value.text))

    def visit_variantbool(self, node, visited_children):
        flag, _, key  = node.children
        val = (flag.text == "+")
        update_variant(self.spec, key.text, VariantValue(enable=val))

    def visit_reserved(self, node, visited_children):
        visited_children = visited_children[0]
        key = visited_children[0].text
        val = visited_children[2]
        if key == "arch":
            pass # val is the ArchSpec we got
        elif key == "platform":
            update_arch(self.spec, ArchSpec(
                        platform = val.text,
                        os = "nil", cpu = "nil", gpu = "nil"))
        elif key == "os":
            update_arch(self.spec, ArchSpec(
                        os = val.text,
                        platform = "nil", cpu = "nil", gpu = "nil"))
        elif key == "target":
            update_arch(self.spec, ArchSpec(
                        cpu = val.text,
                        os = "nil", platform = "nil", gpu = "nil"))
        elif key == "gpu_arch":
            update_arch(self.spec, ArchSpec(
                        gpu = val.text,
                        os = "nil", cpu = "nil", platform = "nil"))
        else:
            raise ValueError("Invalid reserved word: {}".format(key))

    def generic_visit(self, node, visited_children):
        """ The generic visit method. """
        return visited_children or node

def test_spec():
    try:
        parse = grammar.parse('llvm +cheese ~sausage false=true os=CNL10 arch=cray-nil-haswell-nil')
    except IncompleteParseError as err:
        print(err)
        return

    sv = SpecVisitor()
    spec = sv.visit(parse)
    print(spec)

if __name__=="__main__":
    test_spec()
