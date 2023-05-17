from typing import Dict, Optional, List, Tuple, Set
from enum import Enum

from pydantic import BaseModel
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor
from parsimonious.exceptions import IncompleteParseError

"""
A Spec is a set of constraints, each of which lists a requirement
for a package.

version range: (@1.2:1.4)

compiler specifier: (%gcc, %gcc@4.7.3, etc.)

variant specifier:
  +debug, -qt, ~qt
  name=<value>

propagating variant specifier:
  ++debug, ~~debug
  name==<value> 

reserved variant keys for compiler flags:
  cflags, cxxflags, fflags, cppflags, ldflags, and ldlibs

reserved variant keys for arch specifiers:
  platform, os, target, gpu_arch, arch

  examples:
      target=<value> os=<value> Optional architecture specifier (target=haswell os=CNL10)
      platform=linux
      os=ubuntu18.04
      target=broadwell
      # combination
      arch=cray-CNL10-haswell-sm_70
      arch=cray-CNL10-haswell

Dependency specs: (^callpath@1.1)
"""

identifier_re = r"\w[-/.\w]*"

# these variants must have string values
variant_kws = set("arch platform os target gpu_arch cflags cxxflags fflags cppflags ldflags ldlibs".split())

# these variants must have bool values
#variant_bools = "debug test".split()
variant_bools = set()

# The defaults for each of these types below
# define a non-constraining, "any", value.
class VersionRange(BaseModel):
    lo:      Optional[Tuple[int,int,int]] = None
    hi:      Optional[Tuple[int,int,int]] = None
    ext:     str = "" # must match ext2 up to smaller of 2 string lengths.

class VersionInstance(BaseModel):
    semver:  Tuple[int,int,int]
    ext:     str = ""

class VariantType(str, Enum):
    bool    = 'bool'
    single  = 'single'
    multi   = 'multi'

# enable applies to bool-valued specs
# anyof  applies to single and multi-valued specs
#        - values not in the list are not allowed
#        - If anyof is empty, this constraint is not active
#          (since we don't ever form internally contradictory specs).
# allof  applies only to multi-valued specs and is an "and"-list
#        - values not in the list are also allowed
class VariantValue(BaseModel):
    type:      VariantType
    enable:    Optional[bool] = None
    anyof:     Set[str]       = set()
    allof:     Set[str]       = set()
    propagate: bool           = False

class VariantInstance(BaseModel):
    type:      VariantType
    enable:    Optional[bool] = None
    value:     Set[str]       = set()

class Compiler(BaseModel):
    name:    str = ""
    version: Set[VersionRange] = set()
    variant: Dict[str,VariantValue] = {}

class CompilerConfig(BaseModel):
    name:    str
    version: VersionInstance
    variant: Dict[str,VariantInstance] = {}

class Spec(BaseModel):
    name:          str
    version:       Set[VersionRange]      = set()
    variant:       Dict[str,VariantValue] = {}
    deps:          Dict[str,"Spec"]       = {}
    compiler:      Compiler               = Compiler()

class PackageConfig(BaseModel):
    name:     str
    version:  VersionInstance
    variant:  Dict[str,VariantInstance] = {}
    deps:     Dict[str,"PackageConfig"] = {}
    compiler: CompilerConfig

grammar = Grammar(
    r"""
    spec        = word specifier* ws
    specifier   = (ws1 variantone)
                / (ws variantbool)
                / (ws version)
                / (ws compiler)

    variantone  = word equal word
    variantbool = ~r"\+\+|--|~~|\+|-|~" ws word

    version     = ("@:" ws semver) / ("@" semver (ws ":" (ws semver)?)?)

    compiler    = "%%" ws word ws version?

    semver      = ~r"[0-9]+(\.[0-9]+){0,2}"

    word        = ~r"%s"
    equal       = ws ~r"={1,2}" ws

    ws          = ~r"\s*"
    ws1         = ~r"\s+"
    """ % identifier_re
)

# Return the logical "and" of two variant values,
# or else None if there is no mutual solution.
def unify_variants(x : VariantValue, y : VariantValue) -> Optional[VariantValue]:
    if x.type   != y.type:
        return None

    if x.enable != y.enable:
        return None

    if len(x.anyof) > 0 and len(y.anyof) > 0:
        anyof = x.anyof & y.anyof
        if len(anyof) == 0:
            return None
    else:
        anyof = x.anyof | y.anyof

    allof = x.allof | y.allof

    return VariantValue(
              type   = x.type
            , enable = x.enable
            , anyof  = anyof
            , allof  = allof
            , propagate = x.propagate or y.propagate)

def update_variant(s : Spec, name : str, val : VariantValue):
    if name in s.variant:
        ans = unify_variants(s.variant[name], val)
        if ans == None:
            raise KeyError("Incompatible requirements for variant {}: {} and {}".format(name, s.variant[name], val))
        val = ans

    s.variant[name] = val

def update_arch(s : Spec, vals : str, prop : bool) -> None:
    kws = "platform-os-target-gpu_arch"
    for key, val in zip(kws.split("-"), vals.split("-")):
        update_variant(s, key, VariantValue(
            type=VariantType.single, anyof=set([val]), propagate=prop))

# TODO:
#   compiler:      Compiler
#   compilerflags: List[str]
#   deps:          Dict[str,"Spec"]

""" Mutating parser that builds up the result in self.spec.
"""
class SpecVisitor(NodeVisitor):
    def __init__(self):
        self.spec = Spec(name = "")
        super(NodeVisitor).__init__()

    def visit_spec(self, node, visited_children):
        self.spec.name = node.children[0].text
        return self.spec

    def visit_variantone(self, node, visited_children):
        """ Gets each key/value pair, returns a tuple. """
        key, eq, value = visited_children
        if key in variant_bools:
            raise KeyError("Reserved variant {} must be a bool, not a string.".format(key))
        prop = len(eq) > 0
        if key == "arch":
            update_arch(self.spec, value, prop)
        else:
            update_variant(self.spec, key,
                           VariantValue(type=VariantType.single,
                                        anyof=set([value]),
                                        propagate=prop))

    def visit_variantbool(self, node, visited_children):
        flag, _, key  = visited_children
        if flag in variant_kws:
            raise KeyError("Reserved variant {} must be a string, not a bool.".format(flag))
        val  = (flag[0] == "+")
        prop = len(flag) > 1
        update_variant(self.spec, key,
                       VariantValue(type=VariantType.bool,
                                    enable=val,
                                    propagate=prop))

    def visit_equal(self, node, visited_children):
        return visited_children[1]

    def generic_visit(self, node, visited_children):
        """ The generic visit method. """
        return visited_children or node.text

def parse_spec(info : str) -> Spec:
    parse = grammar.parse(info)
    return SpecVisitor().visit(parse)

def test_spec():
    try:
        parse = grammar.parse('llvm +cheese ~sausage false=true os=CNL10 arch=cray-CNL10-haswell')
    except IncompleteParseError as err:
        print(err)
        return

    sv = SpecVisitor()
    spec = sv.visit(parse)
    print(spec)

if __name__=="__main__":
    test_spec()
