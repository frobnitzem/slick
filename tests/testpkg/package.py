from slick.package import PackageBase
from slick.directives import *

class Test(PackageBase):
    variant('foo')
    depends_on('xyz')
