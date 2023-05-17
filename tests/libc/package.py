from slick.packge import *

class Libc(BundlePackage):
    """Dummy package to provide interfaces available in libc."""

    homepage = "https://en.wikipedia.org/wiki/C_standard_library"

    version("1.0")  # Dummy

    variant("iconv", default=False, description="Provides interfaces for Localization Functions")
    variant("rpc", default=False, description="Provides interfaces for RPC")

    provides("iconv", when="+iconv")
    provides("rpc", when="+rpc")

    @property
    def libs(self):
        return LibraryList([])
