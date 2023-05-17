from slick.package import *

class TestPkg(Package):
    variant('foo', True)

    depends_on('github.com/intel/llvm@1.0')
    depends_on('ftp.gnu.org/gnu/bison@3.0:')
