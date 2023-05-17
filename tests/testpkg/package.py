from slick.package import PackageBase
from slick.directives import *

class Test(PackageBase):
    variant('foo', True)
    depends_on('xyz')
